#!/usr/bin/env python
"""The Calibration Controller"""
__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson"]
__license__ = "GPL v3.0"
__version__ = "0.997"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"

#
# DEPENDENCIES
#

#
# INTERNAL DEPENDENCIES
#

import src.model_calibration as model_calibration
import src.view_calibration as view_calibration
import src.controller_generic as controller_generic

#
# EXCEPTIONS
#

class Bad_Stage_Call(Exception): pass
class No_View_Loaded(Exception): pass
class Not_Yet_Implemented(Exception): pass
class Impossible_Fixture(Exception): pass
class UnDocumented_Error(Exception): pass

#
# CLASSES
#

class Calibration_Controller(controller_generic.Controller):

    def __init__(self, window, main_controller):

        super(Calibration_Controller, self).__init__(window, main_controller)

        self._specific_controller = None

    def _get_default_view(self):

        return view_calibration.Calibration_View(self, self._model)

    def _get_default_model(self):

        return model_calibration.model

    def set_mode(self, widget, calibration_mode):

        view = self._view
        model = self._model

        if calibration_mode == 'fixture':

            self._specific_controller = Fixture_Controller(self._window,
                self, model=model, view=view)

        elif calibration_mode == "poly":

            err = Not_Yet_Implemented("Mode 'Cell Count Calibration'")

            raise err

        else:

            raise Bad_Stage_Call(calibration_mode)

class Fixture_Controller(controller_generic.Controller):

    def __init__(self, window, parent, view=None, model=None,
        specific_model=None):

        super(Fixture_Controller, self).__init__(window, parent,
            view=view, model=model)

        #MODEL
        if specific_model is not None:
            self._specific_model = specific_model
        else:
            self.build_new_specific_model()

        #VIEW
        view.set_controller(self)
        self.set_view_stage(None, 'fixture-select')

    def set_view_stage(self, widget, stage_call, *args, **kwargs):

        if len(args) > 0:
            sm = args[0]
        else:
            sm = self._specific_model

        m = self._model
        view = self._view

        if stage_call == 'fixture-select':

            top = view_calibration.Fixture_Select_Top(self,
                m, sm)
            stage = view_calibration.Fixture_Select_Stage(self,
                m, sm)

        elif stage_call == 'marker-calibration':

            self.set_unsaved()
            if sm['new_fixture']:
                self.get_top_controller.fixtures.fill_model(sm)

            top = view_calibration.Fixture_Marker_Calibration_Top(self,
                m, sm)

            if len(sm['marker-positions']) > 3:
                top.set_allow_next(True)

            stage = view_calibration.Fixture_Marker_Calibration_Stage(self,
                m, sm)

        else:

            err = Bad_Stage_Call("{0} recieved call '{1}' from {2}".format(
                self, stage_call, widget))

            raise err

        view.set_top(top)
        view.set_stage(stage)

    def build_new_specific_model(self):

        sm = model_calibration.copy_model(
            model_calibration.specific_fixture_model)
        self._specific_model = sm
        return sm

    def check_fixture_select(self, widget, is_new):

        stage = self._view.get_stage()
        top = self._view.get_top()
        model = self._model

        if is_new:

            new_name = stage.new_name.get_text()
            if new_name == "" or new_name in \
                    self.get_top_controller().fixtures.names():

                warn = True
                allow_next = False

            else:

                warn = False
                allow_next = True

            model['fixture'] = new_name
            model['new_fixture'] = True

        else:

            treemodel, rows = stage.selection.get_selected_rows()
            allow_next = len(rows) > 0
            warn = None
            if allow_next:
                model['fixture'] = treemodel[rows[0]][0]
            model['new_fixture'] = False


        stage.set_bad_name_warning(warn)
        top.set_allow_next(allow_next)

    def set_image_path(self, widget):

        image_list = view_calibration.select_file(
            self._model['fixture-image-dialog'],
            multiple_files=False,
            file_filter=self._model['fixture-image-file-filter'])

        if len(image_list) > 0:

            self._specific_model['im-path'] = image_list[0]
            self._specific_model['marker-positions'] = list()
            self._view.get_stage().set_new_image()

            self._view.get_stage().check_allow_marker_detection()


    def set_number_of_markers(self, widget):

        s = widget.get_text()

        if s != "":

            try:

                n = int(widget.get_text())

            except:

                n = 0
                widget.set_text(str(n))

        else:

            n = 0

        self._specific_model['markers'] = n
        self._view.get_stage().check_allow_marker_detection()

    def run_marker_detect(self, widget):

        sm = self._specific_model

        if sm['markers'] >= 3 and sm['im'] is not None:

            pass

        else:

            err = Impossible_Fixture(
                "Markers must be at least 3 (you have '{0}')".format(
                sm['markers']) + " and you need an image too")

            raise err

        if len(sm['marker-positions']) > 3:
            top.set_allow_next(True)

    def mouse_press(self, widget, *args, **kwargs):

        print "press", widget, args, kwargs

    def mouse_release(self, widget, *args, **kwargs):

        print "release", widget, args, kwargs

    def mouse_move(self, widget, *args, **kwargs):

        print "notify", widget, args, kwargs
