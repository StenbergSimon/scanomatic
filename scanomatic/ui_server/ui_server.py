__author__ = 'martin'

import time
from flask import Flask, request, send_from_directory, redirect, jsonify, abort, render_template
import webbrowser
from threading import Thread
from socket import error
from subprocess import Popen
import os
import numpy as np
from enum import Enum
import shutil
import re
from itertools import chain
import glob

from scanomatic.io.app_config import Config
from scanomatic.io.paths import Paths
from scanomatic.io.logger import Logger
from scanomatic.io.rpc_client import get_client
from scanomatic.imageAnalysis.first_pass_image import FixtureImage
from scanomatic.imageAnalysis.support import save_image_as_png
from scanomatic.models.fixture_models import GrayScaleAreaModel, FixturePlateModel
from scanomatic.imageAnalysis.grayscale import getGrayscales, getGrayscale
from scanomatic.imageAnalysis.imageGrayscale import get_grayscale
from scanomatic.models.factories.fixture_factories import FixtureFactory
from scanomatic.models.factories.compile_project_factory import CompileProjectFactory
from scanomatic.models.compile_project_model import COMPILE_ACTION
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.factories.scanning_factory import ScanningModelFactory
from scanomatic.models.factories.features_factory import FeaturesFactory
from scanomatic.models.factories.settings_factories import ApplicationSettingsFactory

_url = None
_logger = Logger("UI-server")
_ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.tiff'}
_TOO_LARGE_GRAYSCALE_AREA = 300000


class SaveActions(Enum):
    Create = 0
    Update = 1


def _allowed_image(ext):
    """Validates that the image extension is allowed

    :param ext: The image file's extension
    :type ext: str
    :returns bool
    """
    return ext.lower() in _ALLOWED_EXTENSIONS


def get_fixture_image_by_name(name, ext="tiff"):

    fixture_file = Paths().get_fixture_path(name)
    image_path = os.path.extsep.join((fixture_file, ext))
    return get_fixture_image(name, image_path)


def get_fixture_image(name, image_path):

    fixture = FixtureImage()
    fixture.name = name
    fixture.set_image(image_path=image_path)
    return fixture


def get_area_too_large_for_grayscale(grayscale_area_model):
    global _TOO_LARGE_GRAYSCALE_AREA
    area_size = (grayscale_area_model.x2 - grayscale_area_model.x1) * \
                (grayscale_area_model.y2 - grayscale_area_model.y1)

    return area_size > _TOO_LARGE_GRAYSCALE_AREA

    
def get_grayscale_is_valid(values, grayscale):
    if values is None:
        return False

    try:
        fit = np.polyfit(grayscale['targets'], values, 3)
        return np.unique(np.sign(fit)).size == 1
    except:
        return False


def usable_markers(markers, image):

    def marker_inside_image(marker):

        return (marker > 0).all() and marker[0] < image.shape[0] and marker[1] < image.shape[1]

    try:
        markers_array = np.array(markers, dtype=float)
    except ValueError:
        return False

    if markers_array.ndim != 2 or markers_array.shape[0] < 3 or markers_array.shape[1] != 2:
        return False

    if len(set(map(tuple, markers_array))) != len(markers):
        return False

    return all(marker_inside_image(marker) for marker in markers_array)


def safe_directory_name(name):
    return re.match("^[A-Za-z_0-9]*$", name) is not None


def usable_plates(plates):
    
    def usable_plate(plate):
        """

        :type plate: scanomatic.models.fixture_models.FixturePlateModel
        """
        return plate.x2 > plate.x1 and plate.y2 > plate.y1

    def unique_valid_indices():

        return tuple(sorted(plate.index - 1 for plate in plates)) == tuple(range(len(plates)))

    if not all(usable_plate(plate) for plate in plates):
        _logger.warning("Some plate coordinates are wrong")
        return False
    elif not unique_valid_indices():
        _logger.warning("Plate indices are bad")
        return False
    elif len(plates) == 0:
        _logger.warning("No plates")
        return False
    return True
        
    
def split_areas_into_grayscale_and_plates(areas):

    gs = None
    plates = []

    for area in areas:

        try:
            if area['grayscale']:
                gs = GrayScaleAreaModel(x1=area['x1'], x2=area['x2'], y1=area['y1'], y2=area['y2'])
            else:
                plates.append(FixturePlateModel(x1=area['x1'], x2=area['x2'], y1=area['y1'], y2=area['y2'],
                                                index=area['plate']))

        except (AttributeError, KeyError, TypeError):

            _logger.warning("Bad data: '{0}' does not have the expected area attributes".format(area))

    return gs, plates


def launch_server(is_local=None, port=None, host=None, debug=False):

    global _url

    app = Flask("Scan-o-Matic UI", template_folder=Paths().ui_templates)
    rpc_client = get_client(admin=True)

    if rpc_client.local and rpc_client.online is False:
        rpc_client.launch_local()

    if port is None:
        port = Config().ui_port

    if is_local is True or (Config().ui_local and is_local is None):
        host = "localhost"
        is_local = True
    elif host is None:
        host = "0.0.0.0"
        is_local = False

    _url = "http://{host}:{port}".format(host=host, port=port)

    @app.route("/")
    def _root():
        return send_from_directory(Paths().ui_root, Paths().ui_root_file)

    @app.route("/help")
    def _help():
        return send_from_directory(Paths().ui_root, Paths().ui_help_file)

    @app.route("/wiki")
    def _wiki():
        return redirect("https://github.com/local-minimum/scanomatic/wiki")

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

    @app.route("/job/<job_id>/<job_command>")
    def _communicate_with_job(job_id="", job_command=""):

        if rpc_client.online:
            val = rpc_client.communicate(job_id, job_command)
            return jsonify(success=val, reason=None if val else "Refused by server")

        return jsonify(success=False, reason="Server offline")

    @app.route("/status")
    @app.route("/status/<status_type>")
    def _status(status_type=""):

        if status_type != "" and not rpc_client.online:
            return jsonify(sucess= False, reason= "Server offline")

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

    @app.route("/config", methods=['get', 'post'])
    def _config():

        action = request.args.get("action")
        if action:
            return jsonify(success=False, reason="Not implemented")

        try:
            settings_model = ApplicationSettingsFactory.serializer.load(Paths().config_main_app)[0]
        except IndexError:
            settings_model = ApplicationSettingsFactory.create()

        return render_template(Paths().ui_settings_template, **settings_model)

    @app.route("/analysis", methods=['get', 'post'])
    def _analysis():

        action = request.args.get("action")

        if action:
            if action == 'analysis':

                model = AnalysisModelFactory.create(
                    compilation=request.values.get("compilation"),
                    compile_instructions=request.values.get("compile_instructions"),
                    output_directory=request.values.get("output_directory"),
                    chain=request.values.get("chain"))

                success = AnalysisModelFactory.validate(model) and rpc_client.create_analysis_job(
                    AnalysisModelFactory.to_dict(model))

                if success:
                    return jsonify(success=True)
                else:
                    return jsonify(success=False, reason="The following has bad data: {0}".format(
                        ", ".join(AnalysisModelFactory.get_invalid_names(model))))

            elif action == 'extract':

                model = FeaturesFactory.create(analysis_directory=request.values.get("analysis_directory"))

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
            project_name = os.path.basename(os.path.abspath(request.json.get("project_path")))
            project_root = os.path.dirname(request.json.get("project_path")).replace(
                'root', Paths().experiment_root)

            plate_descriptions = request.json.get("plate_descriptions")
            if all(isinstance(p, str) or isinstance(p, unicode) or p is None for p in plate_descriptions):
                plate_descriptions = tuple({"index": i, "description": p} for i, p in enumerate(plate_descriptions))

            m = ScanningModelFactory.create(
                 number_of_scans=request.json.get("number_of_scans"),
                 time_between_scans=request.json.get("time_between_scans"),
                 project_name=project_name,
                 directory_containing_project=project_root,
                 project_tag=request.json.get("project_tag"),
                 scanner_tag=request.json.get("scanner_tag"),
                 description=request.json.get("description"),
                 email=request.json.get("email"),
                 pinning_formats=request.json.get("pinning_formats"),
                 fixture=request.json.get("fixture"),
                 scanner=request.json.get("scanner"),
                 scanner_hardware=request.json.get("scanner_hardware") if "scanner_hardware" in request.json else "EPSON V700",
                 mode=request.json.get("mode") if "mode" in request.json else "TPU",
                 plate_descriptions=plate_descriptions,
                 auxillary_info=request.json.get("auxillary_info"),
            )

            validates = ScanningModelFactory.validate(m)

            job_id = rpc_client.create_scanning_job(ScanningModelFactory.to_dict(m))

            if validates and job_id:
                return jsonify(success=True, name=project_name)
            else:
                return jsonify(success=False, reason="The following has bad data: {0}".format(
                    ", ".join(ScanningModelFactory.get_invalid_names(m))) if not validates else
                    "Job refused, probably scanner can't be reached, check connection.")

        return send_from_directory(Paths().ui_root, Paths().ui_experiment_file)

    @app.route("/experiment/")
    @app.route("/experiment/<command>", methods=['get', 'post'])
    @app.route("/experiment/<command>/", methods=['get', 'post'])
    @app.route("/experiment/<command>/<path:sub_path>", methods=['get', 'post'])
    def _experiment_commands(command=None, sub_path=""):

        if command is None:
            command = 'root'

        sub_path = sub_path.split("/")

        if not all(safe_directory_name(name) for name in sub_path):

            return jsonify(path=Paths().experiment_root, valid_experiment=False,
                           reason="Only letter, numbers and underscore allowed")

        if command == 'root':

            root = Paths().experiment_root
            path = os.path.join(*chain([root], sub_path))
            valid_root = os.path.isdir(os.path.dirname(path))
            duplicate_experiment = os.path.isdir(path) or os.path.isfile(path)
            reason = "Root directory does not exist" if not valid_root else "Duplicate experiment" if duplicate_experiment else ""
            if valid_root:
                suggestions = tuple("/".join(chain([command], os.path.relpath(p, root).split(os.sep)))
                                    for p in glob.glob(path + "*")
                                    if os.path.isdir(p) and safe_directory_name(os.path.basename(p)))
            else:
                suggestions = tuple()

            return jsonify(path="/".join(chain([command], sub_path)), valid_experiment=valid_root and not duplicate_experiment,
                           reason=reason, suggestions=suggestions, prefix=sub_path[-1] if sub_path else "")

        return jsonify()

    @app.route("/compile", methods=['get', 'post'])
    def _compile():

        if request.args.get("run"):

            if not rpc_client.online:
                return jsonify(success=False, reason="Scan-o-Matic server offline")

            path = request.values.get('path')
            is_local = bool(int(request.values.get('local')))
            fixture=request.values.get("fixture")
            _logger.info("Attempting to compile on path {0}, as {1} fixture{2}".format(
                path, ['global', 'local'][is_local], is_local and "." or " (Fixture {0}).".format(fixture)))

            job_id = rpc_client.create_compile_project_job(
                CompileProjectFactory.dict_from_path_and_fixture(
                    path, fixture=fixture, is_local=is_local,
                    compile_action=COMPILE_ACTION.InitiateAndSpawnAnalysis if request.values.get('chain') else COMPILE_ACTION.Initiate))

            return jsonify(success=True if job_id else False, reason="" if job_id else "Invalid parameters")

        return send_from_directory(Paths().ui_root, Paths().ui_compile_file)

    @app.route("/scanners/<scanner_query>")
    def _scanners(scanner_query=None):
        if scanner_query is None or scanner_query.lower() == 'all':
            return jsonify(scanners=rpc_client.get_scanner_status(), success=True)
        elif scanner_query.lower() == 'free':
            return jsonify(scanners={s['socket']: s['scanner_name'] for s in rpc_client.get_scanner_status()},
                           success=True)
        else:
            try:
                return jsonify(scanner=(s for s in rpc_client.get_scanner_status() if scanner_query
                                        in s['scanner_name']).next(), success=True)
            except StopIteration:
                return jsonify(scanner=None, success=False, reason="Unknown scanner or query '{0}'".format(
                    scanner_query))

    @app.route("/grayscales", methods=['post', 'get'])
    def _grayscales():

        if request.args.get("names"):

            return jsonify(grayscales=getGrayscales())

        return ""

    @app.route("/fixtures/<name>")
    def _fixture_data(name=None):
        if not rpc_client.online:
            return jsonify(success=False, reason="Scan-o-Matic server offline")
        elif name in rpc_client.get_fixtures():
            path = Paths().get_fixture_path(name)
            try:
                fixture = tuple(FixtureFactory.serializer.load(path))[0]
                return jsonify(success=True, grayscale=dict(**fixture.grayscale),
                        plates=[dict(**plate) for plate in fixture.plates],
                        markers=zip(fixture.orientation_marks_x, fixture.orientation_marks_y))
            except IndexError:
                return jsonify(success=False, reason="Fixture without data")
        else:
            return jsonify(success=False, reason="Unknown fixture")

    @app.route("/fixtures", methods=['post', 'get'])
    def _fixtures():
        global _TOO_LARGE_GRAYSCALE_AREA
        if request.args.get("names"):

            if rpc_client.online:
                return jsonify(fixtures=rpc_client.get_fixtures(), success=True)
            else:
                return jsonify(fixtures=[], success=False, reason="Scan-o-Matic server offline")
        elif request.args.get("remove"):

            name = Paths().get_fixture_name(request.values.get("name"))
            known_fixtures = tuple(Paths().get_fixture_name(f) for f in rpc_client.get_fixtures())
            if (name not in known_fixtures):
                return jsonify(success=False, reason="Unknown fixture")
            source = Paths().get_fixture_path(name)
            path, ext = os.path.splitext(source)
            i = 0
            pattern = "{0}.deleted{1}"
            while os.path.isfile(pattern.format(path, i)):
                i += 1
            try:
                shutil.move(source, pattern.format(path, i))
            except IOError:
                return jsonify(success=False, reason="Error while removing")
            return jsonify(success=True,reason="Happy")

        elif request.args.get("update") or request.args.get("create"):

            if not rpc_client.online:
                return jsonify(success=False, reason="Scan-o-Matic server offline")

            save_action = SaveActions(int(bool(request.args.get("update", 0, type=int))))

            name = Paths().get_fixture_name(request.json.get("name", ''))
            areas = request.json.get("areas")
            markers = request.json.get("markers")
            grayscale_name = request.json.get("grayscale_name")
            known_fixtures = tuple(Paths().get_fixture_name(f) for f in rpc_client.get_fixtures())
            _logger.info("Attempting to save {0} with areas {1} and markers {2}".format(name, areas, markers))

            if not name:
                return jsonify(success=False, reason="Fixtures need a name")
            elif save_action is SaveActions.Create and name in known_fixtures:
                return jsonify(success=False, reason="Fixture name taken")
            elif save_action is SaveActions.Update and name not in known_fixtures:
                return jsonify(success=False, reason="Unknown fixture")

            try:
                fixture = get_fixture_image_by_name(name)
            except IOError:
                return jsonify(success=False, reason="Fixture image not on server")

            if not usable_markers(markers, fixture.im):
                return jsonify(success=False, reason="Bad markers")

            grayscale_area_model, plates = split_areas_into_grayscale_and_plates(areas)
            _logger.info("Grayscale {0}".format(grayscale_area_model))
            _logger.info("Plates".format(plates))

            if grayscale_area_model:
                
                if grayscale_name not in getGrayscales():
                    return jsonify(success=False, reason="Unknown grayscale type")
                if get_area_too_large_for_grayscale(grayscale_area_model):
                    return jsonify(success=False, reason="Area too large for grayscale")
                
                grayscale_area_model.name = grayscale_name
                _, values = get_grayscale(fixture, grayscale_area_model)
                grayscale_object = getGrayscale(grayscale_area_model.name)
                valid = get_grayscale_is_valid(values, grayscale_object)
                
                if not valid:
                    return jsonify(success=False, reason="Could not detect grayscale")
                
                grayscale_area_model.values = values

            if not usable_plates(plates):
                return jsonify(success=False, reason="Bad plate selections")

            fixture_model = FixtureFactory.create(
                path=Paths().get_fixture_path(name),
                grayscale=grayscale_area_model,
                orientation_marks_x = tuple(mark[0] for mark in markers),
                orientation_marks_y = tuple(mark[1] for mark in markers),
                shape=fixture.im.shape,
                coordinates_scale=1.0,
                plates = plates,
                name=name,
                scale=1.0)

            if not FixtureFactory.validate(fixture_model):
                return jsonify(success=False, reason="Final compilation doesn't validate")

            FixtureFactory.serializer.dump(fixture_model, fixture_model.path)
            return jsonify(success=True)

        elif request.args.get("grayscale"):

            name = request.args.get("fixture", "", type=str)

            if name:

                grayscale_area_model = GrayScaleAreaModel(
                    name=request.args.get("grayscale_name", "", type=str),
                    x1=request.values.get("x1", type=float),
                    x2=request.values.get("x2", type=float),
                    y1=request.values.get("y1", type=float),
                    y2=request.values.get("y2", type=float))

                if get_area_too_large_for_grayscale(grayscale_area_model):

                    return jsonify(source_values=None, target_values=None, grayscale=False,
                                   reason="Area too large")

                _logger.info("Grayscale area to be tested {0}".format(dict(**grayscale_area_model)))

                fixture = get_fixture_image_by_name(name)
                _, values = get_grayscale(fixture, grayscale_area_model)
                grayscale_object = getGrayscale(grayscale_area_model.name)
                valid = get_grayscale_is_valid(values, grayscale_object)
                return jsonify(source_values=values, target_values=grayscale_object['targets'],
                               grayscale=valid, reason=not valid and "No Grayscale" or None)
            else:
                return abort(500)

        elif request.args.get("detect"):

            markers = request.values.get('markers', default=3, type=int)
            image = request.files.get('image')
            name = os.path.basename(request.values.get("name", '', type=str))
            image_name, ext = os.path.splitext(image.filename)
            _logger.info("Working on detecting marker for fixture {0} using image {1} ({2})".format(
                name, image.filename, _allowed_image(ext)))

            if name and _allowed_image(ext):

                fixture_file = Paths().get_fixture_path(name)

                path = os.path.extsep.join((fixture_file, ext.lstrip(os.path.extsep)))
                image.save(path)

                fixture = get_fixture_image(name, path)
                fixture.run_marker_analysis(markings=markers)

                save_image_as_png(path)

                return jsonify(markers=fixture['current'].get_marker_positions(),
                               image=os.path.basename(fixture_file))

            _logger.warning("Refused detection (keys files: {0} values: {1})".format(
                request.files.keys(), request.values.keys()))

            return jsonify(markers=[], image="")

        elif request.args.get("image"):

            image = os.path.extsep.join((os.path.basename(request.args.get("image")), "png"))
            _logger.info("Sending fixture image {0}".format(image))
            return send_from_directory(Paths().fixtures, image)

        return send_from_directory(Paths().ui_root, Paths().ui_fixture_file)

    try:
        if is_local:
            if debug:
                _logger.info("Running in debug mode.")
            app.run(port=port, debug=debug)
        else:
            if debug:
                _logger.warning("Debugging is only allowed on local servers")
            app.run(port=port, host=host)

    except error:
        _logger.warning("Could not bind socket, probably server is already running and this is nothing to worry about."
                        + "\n\tIf old server is not responding, try killing its process."
                        + "\n\tIf something else is blocking the port, try setting another port using --help.")
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
        Thread(target=launch_webbrowser, kwargs={"delay": 2}).start()
    launch_server(**kwargs)