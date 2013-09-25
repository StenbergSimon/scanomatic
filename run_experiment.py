#!/usr/bin/env python
"""Script that runs the image aquisition"""

__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson"]
__license__ = "GPL v3.0"
__version__ = "0.9991"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"

#
# DEPENDENCIES
#

import threading
from multiprocessing import Process
import os
import sys
import time
import uuid
import shutil
from argparse import ArgumentParser
import logging

"""
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
    level=logging.INFO)
"""

#
# SCANNOMATIC LIBRARIES
#

import src.resource_scanner as resource_scanner
import src.resource_first_pass_analysis as resource_first_pass_analysis
import src.resource_fixture as resource_fixture
import src.resource_path as resource_path
import src.resource_app_config as resource_app_config
import src.resource_project_log as resource_project_log
import src.subprocs.communicator as communicator

#
# EXCEPTIONS
#


class Not_Initialized(Exception):
    pass

#
# FUNCTIONS
#


def get_pinnings_list(pinning_string):

    try:

        pinning_str_list = pinning_string.split(",")

    except:

        return None

    pinning_list = list()
    for p in pinning_str_list:

        try:

            p_list = tuple(map(int, p.split("x")))

        except:

            p_list = None

        pinning_list.append(p_list)

    return pinning_list


def free_scanner(scanner, uuid):

    paths = resource_path.Paths()
    config = resource_app_config.Config(paths)
    scanners = resource_scanner.Scanners(paths, config)
    s = scanners[scanner]
    s.set_uuid(uuid)
    s.free()

#
# CLASSES
#


class Experiment(object):

    SCAN_MODE = 'TPU'

    def __init__(self, run_args=None, **kwargs):

        self.paths = resource_path.Paths()
        self._logger = logging.getLogger("Expermient")
        self.fixtures = resource_fixture.Fixtures(self.paths)
        self.config = resource_app_config.Config(self.paths)
        self.scanners = resource_scanner.Scanners(self.paths, self.config)

        self._running = True
        self._paused = False

        if run_args is None or run_args.init_time is None:
            self._init_time = time.time()
        else:
            self._init_time = run_args.init_time

        self._first_image_time

        sys.excepthook = self.__excepthook

        self._scan_threads = list()

        if run_args is None or run_args.scanned is None:
            self._scanned = 0
        else:
            self._scanned = run_args.scanned

        self._initialized = False

        if run_args is None or run_args is not None:
            self._set_settings_from_run_args(run_args)
        elif kwargs is not None:
            self._set_settings_from_kwargs(kwargs)

        self._comm = communicator.Communicator(
            self,
            self.paths.experiment_stdin.format(
                self.paths.get_scanner_path_name(self._scanner_name)),
            self.paths.log_scanner_out.format(self._scanner_name[-1]),
            self.paths.log_scanner_err.format(self._scanner_name[-1])
        )

        self._stdin_pipe_deamon = threading.Thread(target=self._comm.run)
        self._stdin_pipe_deamon.start()

    def __excepthook(self, excType, excValue, traceback):

        self._logger.critical(
            "Uncaught exception:",
            exc_info=(excType, excValue, traceback))

        self._logger.info("Killing deamon")
        #os.kill(self._stdin_pipe_deamon.pid, signal.SIGTERM)
        self._comm.set_terminate()

        self._logger.info("Making sure scanner is freed")
        self._scanner.free()

        self._running = False

    def get_info(self):

        output = (
            '__ALIVE__ {0}\n'.format(self._running),
            '__PREFIX__ {0}\n'.format(self._prefix),
            '__FIXTURE__ {0}\n'.format(self._fixture_name),
            '__SCANNER__ {0}\n'.format(self._scanner_name),
            '__ROOT__ {0}\n'.format(self._root),
            #'__ID__ {0}\n'.format(self._id)
            '__PINNING__ {0}\n'.format(self._pinning),
            '__INTERVAL__ {0}\n'.format(self._interval),
            '__SCANS__ {0}\n'.format(self._max_scans),
            '__INIT-TIME__ {0}\n'.format(self._init_time),
            '__CUR-IM__ {0}\n'.format(self._scanned),
            '__1-PASS FILE__ {0}\n'.format(self._first_pass_analysis_file)
        )
        return output

    def set_terminate(self):

        self._running = False
        return True

    def set_pause(self):
        self._paused = True
        return True

    def set_unpause(self):
        self._paused = False
        return True

    def get_paused(self):
        return self._paused

    def get_current_step(self):
        return self._scanned

    def get_total_iterations(self):
        return self._max_scans

    def get_progress(self):
        return float(self.get_current_step()) / self.get_total_iterations()

    def _generate_uuid(self):

        self._uuid = uuid.uuid1().get_urn().split(":")[-1]

    def _set_settings_from_kwargs(self):

        raise Not_Initialized("Setting from kwarg not done yet")

    def _set_settings_from_run_args(self, run_args):

        self._interval = run_args.interval
        self._max_scans = run_args.number_of_scans
        self._last_scan = run_args.last_scan

        self._pinning = run_args.pinning
        if (64, 96) in self._pinning:
            self._logger.info("Changing resolution to 900 due to 6144 format")
            self.scanners.update_sane_setting('--resolution', "900", modes=['TPU'])

        self._scanner = self.scanners[run_args.scanner]
        self._scanner_name = run_args.scanner
        self._fixture_name = run_args.fixture
        self._root = run_args.root
        self._prefix = run_args.prefix
        self._out_data_path = run_args.outdata_path

        self._set_fixture(self.paths.fixtures, self._fixture_name)

        self._first_pass_analysis_file = os.path.join(
            self._out_data_path,
            self.paths.experiment_first_pass_analysis_relative.format(
                self._prefix))

        self._im_filename_pattern = os.path.join(
            self._root, self._prefix,
            self.paths.experiment_scan_image_pattern)

        self._description = run_args.description
        self._project_id = run_args.project_id
        self._layout_id = run_args.layout_id

        self._uuid = run_args.uuid
        if self._uuid is None or self._uuid == "":
            self._generate_uuid()

        self._scanner.set_uuid(self._uuid)

        self._initialized = True

    def _set_fixture(self, dir_path, fixture_name):

        self._logger.info("Making local copy of fixture settings.")

        shutil.copyfile(
            self.paths.get_fixture_path(fixture_name, own_path=dir_path),
            os.path.join(
                self._out_data_path,
                self.paths.experiment_local_fixturename))

        self._fixture = resource_fixture.Fixture_Settings(
            self._out_data_path,
            self.paths.experiment_local_fixturename,
            self.paths)

    def run(self):

        if not self._initialized:
            raise Not_Initialized()

        self._logger.info("Experiment is initialized...starting!")

        if self._scanned == 0:
            self._write_header_row()

        if self._last_scan is None:
            timer = time.time()
        else:
            timer = self._last_scan

        while self._running:

            #If time for next of first image: Get IT!
            if ((((time.time() - timer) > self._interval * 60) or
                    (self._scanned == 0)) and
                    (self._paused is False)):

                timer = time.time()
                self._get_image()

            time.sleep(0.1)

        self._join_threads()

    def _get_image(self):

        if self._running:

            #self._gated_print("__Is__ {0}".format(self._scanned))
            self._logger.info("Acquiring image {0}".format(
                self._scanned))

            #THREAD IMAGE AQ AND ANALYSIS
            thread = Process(target=self._scan_and_analyse, args=(self._scanned,))

            thread.start()

            #SAFETY MARGIN SO THAT
            time.sleep(0.1)

            #CHECK IF ALL IS DONE
            self._scanned += 1

            if (self._scanned > self._max_scans or
                    self._init_time + self._interval * 60 *
                    (self._max_scans + 1) < time.time()):

                self._logger.info("That was the last image")
                self._running = False

                return False

        else:

            self._logger.info("Aborting, no image aquired")
            return False

    def _scan_and_analyse(self, im_index):

        if self._first_image_time is None:
            self._first_image_time = time.time()
            curTime = 0.0
        else:
            curTime = time.time() - self._first_image_time

        self._logger.info("Image {0} started!".format(im_index))
        im_path = self._im_filename_pattern.format(
            self._prefix,
            str(im_index).zfill(4),
            curTime)

        #SCAN
        self._logger.info("Requesting scan to file '{0}'".format(im_path))
        scan_success = self._scanner.scan(
            mode=self.SCAN_MODE, filename=im_path)

        #FREE SCANNER IF LAST
        if not self._running or im_index >= self._max_scans:
            self._scanner.free()

        #ANALYSE
        if scan_success:

            self._logger.info("Requesting first pass analysis of file '{0}'".format(im_path))
            im_dict = resource_first_pass_analysis.analyse(
                file_name=im_path,
                im_acq_time=curTime,
                experiment_directory=self._out_data_path,
                paths=self.paths)

            self._logger.info("{0}".format(im_dict))

            im_dict = resource_project_log.get_image_dict(
                im_path,
                curTime,
                im_dict['mark_X'],
                im_dict['mark_Y'],
                im_dict['grayscale_indices'],
                im_dict['grayscale_values'],
                im_dict['scale'],
                img_dict=im_dict,
                image_shape=im_dict['im_shape'])

            self._logger.info("Writing first pass analysis results to file")

            resource_project_log.append_image_dicts(
                self._first_pass_analysis_file,
                images=[im_dict])

        #self._gated_print("__Id__ {0}".format(self._scanned))
        self._logger.info("Image {0} done!".format(im_index))

    def _write_header_row(self):

        self._logger.info("Writing header row")

        meta_data = resource_project_log.get_meta_data_dict(
            **{
                'Start Time': time.time(),
                'Prefix': self._prefix,
                'Description': self._description,
                'Measures': self._max_scans,
                'Interval': self._interval,
                'UUID': self._uuid,
                'Fixture': self._fixture_name,
                'Scanner': self._scanner_name,
                'Pinning Matrices': self._pinning,
                'Manual Gridding': None,
                'Project ID': self._project_id,
                'Scanner Layout ID': self._layout_id
            }
        )

        resource_project_log.write_log_file(
            self._first_pass_analysis_file,
            meta_data=meta_data)

    def _join_threads(self):

        #End communications thread
        self._comm.set_terminate()

        self._logger.info("Waiting for all scans and analysis...")

        while threading.active_count() > 1:
            time.sleep(0.5)

        self._scanner.free()

        self._logger.info("All threads are done, experiment run is done")

#
# COMMAND LINE BEHAVIOUR
#

if __name__ == "__main__":

    print "Experiment called with:\n{0}\n".format(" ".join(sys.argv))

    parser = ArgumentParser(description="""Runs a session of image gathering
given certain parameters and creates a first pass analysis file which is the
input file for the analysis script.""")

    parser.add_argument(
        '-f', '--fixture', type=str, dest="fixture",
        help='Path to fixture config file')

    parser.add_argument(
        '-s', '--scanner', type=str, dest='scanner',
        help='Scanner to be used')

    parser.add_argument(
        '-i', '--interval', type=float, default=20.0,
        dest='interval',
        help='Minutes between scans')

    parser.add_argument(
        '-n', '--number-of-scans', type=int, default=217,
        dest='number_of_scans',
        help='Number of scans requested')

    parser.add_argument(
        '-m', '--matrices', type=str, dest='pinning',
        help='List of pinning matrices')

    parser.add_argument(
        '-r', '--root', type=str, dest='root',
        help='Projects root')

    parser.add_argument(
        '-p', '--prefix', type=str, dest='prefix',
        help='Project prefix')

    parser.add_argument(
        '-d', '--description', type=str, dest='description',
        help='Project description')

    parser.add_argument(
        '-c', '--code', type=str, dest='project_id',
        help='Identification code for the project from the planner')

    parser.add_argument(
        '-l', '--scan-layout-tag', dest='layout_id',
        help="Identification code for the scanner layout being run")

    parser.add_argument(
        '-u', '--uuid', type=str, dest='uuid',
        help='UUID to indentify self with scanner reservation')

    parser.add_argument(
        '-e', '--experiment-file', type=str, dest='file',
        help='Path to experiment file to continue on')

    parser.add_argument(
        "--debug", dest="debug", default="warning",
        type=str, help="Sets debugging level")

    args = parser.parse_args()

    #DEBUGGING
    LOGGING_LEVELS = {'critical': logging.CRITICAL,
                      'error': logging.ERROR,
                      'warning': logging.WARNING,
                      'info': logging.INFO,
                      'debug': logging.DEBUG}

    #PATHS
    paths = resource_path.Paths()

    #HIDDEN ARGS DEALING WITH CONTIUNUING PROJECTS
    args.last_scan = None
    args.init_time = None
    args.scanned = None

    #EXPERIMENT FILE TAKES OVER OTHER THINGS
    if args.file is not None:
        try:
            fh = open(args.file, 'r')
            file_settings = eval(fh.readline().strip())
        except:
            parser.error("Could not load experiemtfile")

        args.scanner = file_settings['Scanner']
        args.fixture = file_settings['Fixture']
        args.interval = file_settings['Interval']
        args.number_of_scans = file_settings['Measures']
        args.pinning = file_settings['Pinning Matrices']
        args.prefix = file_settings['Prefix']
        args.uuid = file_settings['UUID']
        args.init_time = file_settings['Start Time']
        args.project_id = file_settings['Project ID']
        args.layout_id = file_settings['Scanner Layout ID']

        args.root = os.path.abspath(os.path.join(
            args.file, os.path.pardir,
            os.path.pardir))

        args.scanned = 0
        for line in fh:
            try:
                args.last_scan = eval(line.strip())['Time']
                args.scanned += 1
            except:
                pass
        fh.close()

    #SCANNER
    if args.scanner is None:
        parser.error("Without specifying a scanner, this makes little sense")
    #elif get_scanner_resource(args.scanner) is None

    #TESTING FIXTURE FILE
    if args.fixture is None or args.fixture == "":
        free_scanner(args.scanner, args.uuid)
        parser.error("Must have fixture file")

    fixture = paths.get_fixture_path(args.fixture)

    try:
        fs = open(fixture, 'r')
        fs.close()
    except:
        free_scanner(args.scanner, args.uuid)
        parser.error("Can't find any file at '{0}'".format(fixture))

    #INTERVAl
    if 7 > args.interval > 4 * 60:
        free_scanner(args.scanner, args.uuid)
        parser.error("Interval is out of allowed bounds!")

    #NUMBER OF SCANS
    if 2 > args.number_of_scans > 1000:
        free_scanner(args.scanner, args.uuid)
        parser.error("Number of scans is out of bounds")

    #EXPERIMENTS ROOT
    if args.root is None or os.path.isdir(args.root) is False:
        free_scanner(args.scanner, args.uuid)
        parser.error("Experiments root is not a directory")

    #PINNING MATRICSE
    if type(args.pinning) == str:
        args.pinning = get_pinnings_list(args.pinning)

    if args.pinning is None:
        free_scanner(args.scanner, args.uuid)
        parser.error("Bad pinnings supplied")

    #PREFIX
    if (args.prefix is None or args.file is None and
            os.path.isdir(os.path.join(args.root, args.prefix))):

        free_scanner(args.scanner, args.uuid)
        parser.error("Prefix is a duplicate or invalid")

    args.outdata_path = os.sep.join((args.root, args.prefix))

    #CODE
    if args.project_id is None:
        args.project_id = ""

    #LAYOUT TAG
    if args.layout_id is None:
        args.layout_id = ""

    #LOGGING
    if args.debug in LOGGING_LEVELS.keys():

        logging_level = LOGGING_LEVELS[args.debug]

    else:

        logging_level = LOGGING_LEVELS['warning']

    #CREATE DIRECTORY
    if args.file is None:
        os.mkdir(args.outdata_path)

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S\n',
        filename=os.path.join(args.outdata_path, "experiment.run"),
        filemode='w',
        level=logging_level)

    logging.info("TEST")
    e = Experiment(run_args=args)
    e.run()
