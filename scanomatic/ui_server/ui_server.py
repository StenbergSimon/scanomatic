import os
import requests

import time
import webbrowser
from flask import Flask, request, send_from_directory, redirect, jsonify, render_template

from socket import error
from threading import Thread
from types import StringTypes

from scanomatic.io.app_config import Config
from scanomatic.io.logger import Logger
from scanomatic.io.paths import Paths
from scanomatic.io.power_manager import POWER_MANAGER_TYPE
from scanomatic.io.rpc_client import get_client
from scanomatic.models.compile_project_model import COMPILE_ACTION
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.compile_project_factory import CompileProjectFactory
from scanomatic.models.factories.features_factory import FeaturesFactory
from scanomatic.models.factories.scanning_factory import ScanningModelFactory

from . import qc_api
from . import analysis_api
from . import compilation_api
from . import calibration_api
from . import scan_api
from . import management_api
from . import tools_api
from . import data_api
from .general import get_2d_list

_url = None
_logger = Logger("UI-server")


def launch_server(is_local=None, port=None, host=None, debug=False):

    global _url

    app = Flask("Scan-o-Matic UI", template_folder=Paths().ui_templates)

    rpc_client = get_client(admin=True)

    if rpc_client.local and rpc_client.online is False:
        rpc_client.launch_local()

    if port is None:
        port = Config().ui_server.port

    if is_local is True or (Config().ui_server.local and is_local is None):
        host = "localhost"
        is_local = True
    elif host is None:
        host = "0.0.0.0"
        is_local = False

    _url = "http://{host}:{port}".format(host=host, port=port)

    _logger.info("Requested to launch UI-server at {0} being local={1} and debug={2}".format(
        _url, is_local, debug))

    @app.route("/")
    def _root():
        return send_from_directory(Paths().ui_root, Paths().ui_root_file)

    @app.route("/help")
    def _help():
        return send_from_directory(Paths().ui_root, Paths().ui_help_file)

    @app.route("/qc_norm")
    def _qc_norm():
        return send_from_directory(Paths().ui_root, Paths().ui_qc_norm_file)

    @app.route("/wiki")
    def _wiki():
        return redirect("https://github.com/local-minimum/scanomatic/wiki")

    @app.route("/maintain")
    def _maintain():
        return send_from_directory(Paths().ui_root, Paths().ui_maintain_file)

    @app.route("/images/<image_name>")
    def _help_logo(image_name=None):
        if image_name:
            return send_from_directory(Paths().images, image_name)

    @app.route("/style/<style>")
    def _css_base(style=None):
        if style:
            return send_from_directory(Paths().ui_css, style)

    @app.route("/js/<js>")
    def _js_base(js=None):
        if js:
            return send_from_directory(Paths().ui_js, js)

    @app.route("/fonts/<font>")
    def _font_base(font=None):
        if font:
            return send_from_directory(Paths().ui_font, font)

    @app.route("/status")
    @app.route("/status/<status_type>")
    def _status(status_type=""):

        if status_type != "" and not rpc_client.online:
            return jsonify(sucess=False, reason="Server offline")

        if status_type == 'queue':
            return jsonify(success=True, data=rpc_client.get_queue_status())
        elif 'scanner' in status_type:
            return jsonify(success=True, data=rpc_client.get_scanner_status())
        elif 'job' in status_type:
            return jsonify(success=True, data=rpc_client.get_job_status())
        elif status_type == 'server':
            return jsonify(success=True, data=rpc_client.get_status())
        elif status_type == "":

            return send_from_directory(Paths().ui_root, Paths().ui_status_file)
        else:
            return jsonify(succes=False, reason='Unknown status request')

    @app.route("/settings", methods=['get', 'post'])
    def _config():

        app_conf = Config()

        action = request.args.get("action")
        if action == "update":

            data_object = request.get_json(silent=True, force=True)
            if not data_object:
                data_object = request.values

            app_conf.number_of_scanners = data_object["number_of_scanners"]
            app_conf.power_manager.number_of_sockets = data_object["power_manager"]["sockets"]
            app_conf.power_manager.host = data_object["power_manager"]["host"]
            app_conf.power_manager.mac = data_object["power_manager"]["mac"]
            app_conf.power_manager.name = data_object["power_manager"]["name"]
            app_conf.power_manager.password = data_object["power_manager"]["password"]
            app_conf.power_manager.host = data_object["power_manager"]["host"]
            app_conf.power_manager.type = POWER_MANAGER_TYPE[data_object["power_manager"]["type"]]
            app_conf.paths.projects_root = data_object["paths"]["projects_root"]
            app_conf.computer_human_name = data_object["computer_human_name"]
            app_conf.mail.warn_scanning_done_minutes_before = data_object["mail"]["warn_scanning_done_minutes_before"]

            bad_data = []
            success = app_conf.validate(bad_data)
            app_conf.save_current_settings()
            return jsonify(success=success, reason=None if success else "Bad data for {0}".format(bad_data))
        elif action:
            return jsonify(success=False, reason="Not implemented")

        return render_template(Paths().ui_settings_template, **app_conf.model_copy())

    @app.route("/analysis", methods=['get', 'post'])
    def _analysis():

        action = request.args.get("action")

        if action:
            if action == 'analysis':

                path_compilation = request.values.get("compilation")
                path_compilation = os.path.abspath(path_compilation.replace('root', Config().paths.projects_root))

                path_compile_instructions = request.values.get("compile_instructions")
                if path_compile_instructions == "root" or path_compile_instructions == "root/":
                    path_compile_instructions = None
                elif path_compile_instructions:
                    path_compile_instructions = os.path.abspath(path_compile_instructions.replace(
                        'root', Config().paths.projects_root))

                _logger.info("Attempting to analyse '{0}' (instructions {1})".format(
                    path_compilation, path_compile_instructions))

                model = AnalysisModelFactory.create(
                    compilation=path_compilation,
                    compile_instructions=path_compile_instructions,
                    output_directory=request.values.get("output_directory"),
                    one_time_positioning=bool(request.values.get('one_time_positioning', default=1, type=int)),
                    chain=bool(request.values.get('chain', default=1, type=int)))

                regridding_folder = request.values.get("reference_grid_folder", default=None)
                if regridding_folder:
                    grid_list = get_2d_list(request.values, "gridding_offsets")
                    grid_list = tuple(tuple(map(int, l)) if l else None for l in grid_list)

                    model.grid_model.reference_grid_folder = regridding_folder
                    model.grid_model.gridding_offsets = grid_list

                success = AnalysisModelFactory.validate(model) and rpc_client.create_analysis_job(
                    AnalysisModelFactory.to_dict(model))

                if success:
                    return jsonify(success=True)
                else:
                    return jsonify(success=False, reason="The following has bad data: {0}".format(
                        ", ".join(AnalysisModelFactory.get_invalid_names(model))))

            elif action == 'extract':
                path = request.values.get("analysis_directory")
                path = os.path.abspath(path.replace('root', Config().paths.projects_root))
                _logger.info("Attempting to extract features in '{0}'".format(path))
                model = FeaturesFactory.create(analysis_directory=path)

                success = FeaturesFactory.validate(model) and rpc_client.create_feature_extract_job(
                    FeaturesFactory.to_dict(model))

                if success:
                    return jsonify(success=success)
                else:
                    return jsonify(success=success, reason="The follwoing has bad data: {0}".format(", ".join(
                        FeaturesFactory.get_invalid_names(model))) if not FeaturesFactory.validate(model) else
                        "Refused by the server, check logs.")

            else:
                return jsonify(success=False, reason='Action "{0}" not reconginzed'.format(action))
        return send_from_directory(Paths().ui_root, Paths().ui_analysis_file)

    @app.route("/experiment", methods=['get', 'post'])
    def _experiment():

        if request.args.get("enqueue"):

            data_object = request.get_json(silent=True, force=True)
            if not data_object:
                data_object = request.values

            project_name = os.path.basename(os.path.abspath(data_object.get("project_path")))
            project_root = os.path.dirname(data_object.get("project_path")).replace(
                'root', Config().paths.projects_root)

            plate_descriptions = data_object.get("plate_descriptions")
            if all(isinstance(p, StringTypes) or p is None for p in plate_descriptions):
                plate_descriptions = tuple({"index": i, "description": p} for i, p in enumerate(plate_descriptions))

            m = ScanningModelFactory.create(
                 number_of_scans=data_object.get("number_of_scans"),
                 time_between_scans=data_object.get("time_between_scans"),
                 project_name=project_name,
                 directory_containing_project=project_root,
                 project_tag=data_object.get("project_tag"),
                 scanner_tag=data_object.get("scanner_tag"),
                 description=data_object.get("description"),
                 email=data_object.get("email"),
                 pinning_formats=data_object.get("pinning_formats"),
                 fixture=data_object.get("fixture"),
                 scanner=data_object.get("scanner"),
                 scanner_hardware=data_object.get("scanner_hardware") if "scanner_hardware" in request.json
                 else "EPSON V700",
                 mode=data_object.get("mode", "TPU"),
                 plate_descriptions=plate_descriptions,
                 auxillary_info=data_object.get("auxillary_info"),
            )

            validates = ScanningModelFactory.validate(m)

            job_id = rpc_client.create_scanning_job(ScanningModelFactory.to_dict(m))

            if validates and job_id:
                return jsonify(success=True, name=project_name)
            else:

                return jsonify(success=False, reason="The following has bad data: {0}".format(
                    ScanningModelFactory.get_invalid_as_text(m))
                    if not validates else
                    "Job refused, probably scanner can't be reached, check connection.")

        return send_from_directory(Paths().ui_root, Paths().ui_experiment_file)

    @app.route("/compile", methods=['get', 'post'])
    def _compile():

        if request.args.get("run"):

            if not rpc_client.online:
                return jsonify(success=False, reason="Scan-o-Matic server offline")

            path = request.values.get('path')
            path = os.path.abspath(path.replace('root', Config().paths.projects_root))
            fixture_is_local = bool(int(request.values.get('local')))
            fixture = request.values.get("fixture")
            chain_steps = bool(request.values.get('chain', default=1, type=int))
            images = request.values.getlist('images[]')

            _logger.info("Attempting to compile on path {0}, as {1} fixture{2} (Chaining: {3}), images {4}".format(
                path,
                'local' if fixture_is_local else 'global',
                fixture_is_local and "." or " (Fixture {0}).".format(fixture),
                chain_steps, images))

            dict_model = CompileProjectFactory.dict_from_path_and_fixture(
                path, fixture=fixture, is_local=fixture_is_local,
                compile_action=COMPILE_ACTION.InitiateAndSpawnAnalysis if chain_steps else
                COMPILE_ACTION.Initiate)

            if images:
                dict_model['images'] = [p for p in dict_model['images'] if os.path.basename(p['path']) in images]
                if len(dict_model['images']) != len(images):
                    return jsonify(
                        success=False,
                        reason="The manually set list of images could not be satisfied"
                        "with the images in the specified folder")

            job_id = rpc_client.create_compile_project_job(dict_model)

            return jsonify(success=True if job_id else False, reason="" if job_id else "Invalid parameters")

        return send_from_directory(Paths().ui_root, Paths().ui_compile_file)

    @app.route("/scanners/<scanner_query>")
    def _scanners(scanner_query=None):
        if scanner_query is None or scanner_query.lower() == 'all':
            return jsonify(scanners=rpc_client.get_scanner_status(), success=True)
        elif scanner_query.lower() == 'free':
            return jsonify(scanners={s['socket']: s['scanner_name'] for s in rpc_client.get_scanner_status()
                                     if 'owner' not in s or not s['owner']},
                           success=True)
        else:
            try:
                return jsonify(scanner=(s for s in rpc_client.get_scanner_status() if scanner_query
                                        in s['scanner_name']).next(), success=True)
            except StopIteration:
                return jsonify(scanner=None, success=False, reason="Unknown scanner or query '{0}'".format(
                    scanner_query))

    @app.route("/fixtures", methods=['post', 'get'])
    def _fixtures():

        return send_from_directory(Paths().ui_root, Paths().ui_fixture_file)

    management_api.add_routes(app, rpc_client)
    tools_api.add_routes(app)
    qc_api.add_routes(app)
    analysis_api.add_routes(app)
    compilation_api.add_routes(app)
    scan_api.add_routes(app)
    data_api.add_routes(app, rpc_client, debug)
    calibration_api.add_routes(app)

    try:
        if is_local:
            if debug:
                _logger.info("Running in debug mode.")
            app.run(port=port, debug=debug)
        else:
            if debug:
                _logger.warning("Debugging is only allowed on local servers")
            else:
                app.run(port=port, host=host)

    except error:
        _logger.warning("Could not bind socket, probably server is already running and this is nothing to worry about."
                        "\n\tIf old server is not responding, try killing its process."
                        "\n\tIf something else is blocking the port, try setting another port using --help.")
        return False
    return True


def launch_webbrowser(delay=0.0):

    if delay:
        _logger.info("Will open webbrowser in {0} s".format(delay))
        time.sleep(delay)

    if _url:
        webbrowser.open(_url)
    else:
        _logger.error("No server launched")


def launch(open_browser_url=True, **kwargs):
    if open_browser_url:
        _logger.info("Getting ready to open browser")
        Thread(target=launch_webbrowser, kwargs={"delay": 2}).start()
    else:
        _logger.info("Will not open browser")

    launch_server(**kwargs)


def ui_server_responsive():

    port = Config().ui_server.port
    if not port:
        port = 5000
    host = Config().ui_server.host
    if not host:
        host = 'localhost'
    try:
        return requests.get("http://{0}:{1}".format(host, port)).ok
    except requests.ConnectionError:
        return False