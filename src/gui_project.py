#!/usr/bin/env python
"""GTK-GUI for running analysis on a project"""

__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson"]
__license__ = "GPL v3.0"
__version__ = "0.992"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"

#
# DEPENDENCIES
#

import pygtk
pygtk.require('2.0')

import gtk, pango
import gobject
import os, os.path, sys#, shutil
import re
import time
import types
from subprocess import call, Popen

#
# SCANNOMATIC LIBRARIES
#

import src.resource_log_maker as log_maker
import src.resource_log_reader as log_reader
import src.resource_power_manager as power_manager
import src.resource_image as img_base
import src.resource_fixture as fixture_settings
import src.resource_os as os_tools


#
# SCANNING EXPERIMENT GUI
#


class Project_Analysis_Running(gtk.Frame):
    def __init__(self, owner, gtk_target, log_file, matrices, 
        watch_colony = None, supress_other = False, watch_time = 1, 
        analysis_output='analysis'):

        self.USE_CALLBACK = owner.USE_CALLBACK

        self.owner = owner
        self.DMS = self.owner.DMS

        self._gtk_target = gtk_target


        self._analyis_script_path = self.owner._program_config_root + os.sep + "analysis.py"

        self._analysis_running = False

        self._matrices = matrices
        self._watch_colony = watch_colony
        self._supress_other = supress_other
        self._watch_time = watch_time

        self._analysis_log_dir = os.sep.join(log_file.split(os.sep)[:-1]) + os.sep 

        self._analysis_output = analysis_output
        self._analysis_log_file_path = log_file

        self._start_time = time.time()

        #Make GTK-stuff
        gtk.Frame.__init__(self, "Running Analysis On: %s" % log_file)

        vbox = gtk.VBox()
        self.add(vbox)


        #Time status
        hbox = gtk.HBox()
        self._gui_analysis_start = gtk.Label("Start time: %s" % str(\
            time.strftime("%Y-%m-%d %H:%M",
            time.localtime(time.time()))))
        self._gui_timer = gtk.Label("Run-time: %d" % int((time.time() - float(self._start_time)) / 60))
        hbox.pack_start(self._gui_analysis_start, False, False, 2)
        hbox.pack_start(self._gui_timer, False, False, 20)
        vbox.pack_start(hbox, False, False, 2)

        #Run status
        self._gui_status_text = gtk.Label("")
        vbox.pack_start(self._gui_status_text, False, False, 2)

            
        self._gtk_target.pack_start(self, False, False, 20)
        self.show_all()

        gobject.timeout_add(1000*5, self._run)

    def _run(self):

        if self._analysis_running:

            if self._analysis_sub_proc.poll() != None:
                self._analysis_log.close()
                self._gui_status_text.set_text("Analysis complete")
                gobject.timeout_add(1000*60*3, self.destroy)          
            else:
                
                self._gui_timer = gtk.Label("Run-time: %d" % int((time.time() \
                    - float(self._start_time)) / 60))
                gobject.timeout_add(1000*60*2, self._run)
        else:
            self._gui_status_text.set_text("Analysis is running! (This may take several hours)")
            self._analysis_running = True
            self._analysis_log = open(self._analysis_log_dir +  ".analysis.log", 'w')
            analysis_query = [self.owner._program_code_root + os.sep + \
                "analysis.py","-i", self._analysis_log_file_path, 
                "-o", self._analysis_output, "-t", 
                self._watch_time, '--xml-short', 'True', 
                '--xml-omit-compartments', 'background,cell',
                '--xml-omit-measures','mean,median,IQR,IQR_mean,centroid,perimeter,area']

            if self._matrices is not None:
                analysis_query += ["-m", self._matrices]
            if self._watch_colony is not None:
                analysis_query += ["-w", self._watch_colony]
            if self._supress_other is True: 
                analysis_query += ["-s", "True"]

            self.DMS("Executing", str(analysis_query), level=110)

            self._analysis_sub_proc = Popen(map(str, analysis_query), 
                stdout=self._analysis_log, shell=False)
            gobject.timeout_add(1000*60*10, self._run)

          
class Project_Analysis_Setup(gtk.Frame):
    def __init__(self, owner):

        self._gui_updating = False
        self._owner = owner
        self.DMS = owner.DMS
        
        self._matrices = None
        self._watch_colony = None
        self._supress_other = False
        self._watch_time = '-1'

        self._analysis_output = 'analysis'
        self._analysis_log_file_path = None

        self.pinning_matrices = {'A: 8 x 12 (96)':(8,12), 
            'B: 16 x 24 (384)': (16,24), 
            'C: 32 x 48 (1536)': (32,48),
            'D: 64 x 96 (6144)': (64,96),
            '--Empty--': None}

        self.pinning_string = ""
 
        #GTK - stuff

        gtk.Frame.__init__(self, "(RE)-START ANALYSIS OF A PROJECT")
        vbox = gtk.VBox()
        self.add(vbox)

        #Log-file selection
        hbox = gtk.HBox()
        self._gui_analysis_log_file = gtk.Label("Log file: %s" % \
            str(self._analysis_log_file_path))
        #label.set_max_width_chars(110)
        #label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)

        button = gtk.Button(label = 'Select Log File')
        button.connect("clicked", self._select_log_file)
        hbox.pack_start(self._gui_analysis_log_file, False, False, 2)
        hbox.pack_end(button, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)

        #Output directory name
        hbox = gtk.HBox()
        label = gtk.Label("Analysis output relative directory:")
        entry = gtk.Entry()
        entry.set_text(str(self._analysis_output))
        entry.connect("focus-out-event", self._eval_input, "analysis_output")
        hbox.pack_start(label, False, False, 2)
        hbox.pack_end(entry, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)

        #Output directory overwrite warning
        self._gui_warning = gtk.Label("")
        vbox.pack_start(self._gui_warning, False, False, 2)

        #Matrices-override
        hbox = gtk.HBox()
        self.plates_label = gtk.Label("Plates")
        checkbox = gtk.CheckButton(label="Override pinning settings", use_underline=False)
        checkbox.connect("clicked", self._set_override_toggle)
        self.plate_pinnings = gtk.HBox()
        self.plates_entry = gtk.Entry(max=1)
        self.plates_entry.set_size_request(20,-1)
        self.plates_entry.connect("focus-out-event", self._set_plates)
        self.plates_entry.set_text(str(len(self._matrices or 4*[None])))
        hbox.pack_start(checkbox, False, False, 2)
        hbox.pack_end(self.plate_pinnings, False, False, 2)
        hbox.pack_end(self.plates_entry, False, False, 2)
        hbox.pack_end(self.plates_label, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)
        self._set_plates(self.plates_entry)

        #Watch-colony
        hbox = gtk.HBox()
        label = gtk.Label("Watch colony:")
        entry = gtk.Entry()
        entry.set_text(str(self._watch_colony))
        entry.connect("focus-out-event",self._eval_input, "watch_colony")
        hbox.pack_start(label, False, False, 2)
        hbox.pack_end(entry, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)
       
        #Watch-time 
        hbox = gtk.HBox()
        label = gtk.Label("Watch time:")
        entry = gtk.Entry()
        entry.set_text(str(self._watch_time))
        entry.connect("focus-out-event",self._eval_input, "watch_time")
        hbox.pack_start(label, False, False, 2)
        hbox.pack_end(entry, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)

        #Supress other
        hbox = gtk.HBox()
        label = gtk.Label("Supress analysis of the non-watched colonies:")
        entry = gtk.Entry()
        entry.set_text(str(self._supress_other))
        entry.connect("focus-out-event",self._eval_input, "supress_other")
        hbox.pack_start(label, False, False, 2)
        hbox.pack_end(entry, False, False, 2)
        vbox.pack_start(hbox, False, False, 20)
        
        #Start button
        hbox = gtk.HBox()
        self._gui_start_button = gtk.Button("Start")
        self._gui_start_button.connect("clicked", self._start)
        self._gui_start_button.set_sensitive(False)
        hbox.pack_start(self._gui_start_button, False, False, 2)
        vbox.pack_start(hbox, False, False, 2)
        
        vbox.show_all() 
        self._set_override_toggle(widget=checkbox)

    def _set_override_toggle(self, widget=None, event=None, data=None):

        if widget.get_active():
            self.plates_entry.show()
            self.plate_pinnings.show()
            self._set_plates(widget=self.plates_entry)
            self.plates_label.set_text("Plates:")
        else:
            self.plates_entry.hide()
            self.plate_pinnings.hide()
            self.plates_label.set_text("(Using the pinning matrices specified in the log-file)")
            self.pinning_string = None

    def _set_plates(self, widget=None, event=None, data=None):

        try:
            slots = int(widget.get_text())
        except:
            slots = 0
            widget.set_text(str(slots))
        if slots < 0:
            slots = 0
            widget.set_text(str(slots))
 
        cur_len = len(self.plate_pinnings.get_children()) / 2

        if cur_len < slots:
            for pos in xrange(cur_len, slots):

                label = gtk.Label('#%d' % pos)
                self.plate_pinnings.pack_start(label, False, False, 2)

                dropbox = gtk.combo_box_new_text()                   
                def_key_text = '1536'
                def_key = 0
                for i, m in enumerate(sorted(self.pinning_matrices.keys())):
                    dropbox.append_text(m)
                    if def_key_text in m:
                        def_key = i
                dropbox.connect("changed", self._build_pinning_string)
                self.plate_pinnings.pack_start(dropbox, False, False, 2)
                dropbox.set_active(def_key)
                
            self.plate_pinnings.show_all()
        elif cur_len > slots:
            children = self.plate_pinnings.get_children()
            for i, c in enumerate(children):
                if i >= slots*2:
                    c.destroy()

    def _build_pinning_string(self, widget=None):

        children = self.plate_pinnings.get_children()
        self.pinning_string = ""
        sep = ":"
        for i in xrange(1, len(children), 2):
            c_active = children[i].get_active()
            c_text = children[i].get_model()[c_active][0]
            self.pinning_string += str(self.pinning_matrices[c_text])
            if i < len(children)-1:
                self.pinning_string += sep

    def _eval_input(self, widget=None, event=None, widget_name=None):

        if not self._gui_updating:

            self._gui_updating = True

            data = widget.get_text()

            if widget_name == "supress_other":
                try:
                    data = bool(eval(data))
                except:
                    data = False

                self._supress_other = data

            elif widget_name == "watch_time":
                try:
                    data = data.split(",")
                    data = map(int, data)
                    data = str(data)[1:-1].replace(" ","")
                except:
                    data = "-1"
                
                self._watch_time = data

            elif widget_name == "watch_colony":
                if data == "None":
                    data = None
                else:
                    try:
                        data = data.split(":")
                        data = map(int, data)
                        data = str(data)[1:-1].replace(" ","").replace(",",":")
                    except: 
                        data = None

                self._watch_colony = data


            elif widget_name == "analysis_output":

                
                if data == "":
                    data = "analysis"

                self._path_warning(output=data)

                self._analysis_output = data

            widget.set_text(str(data))
            self._gui_updating = False




    def _path_warning(self, output=None):

        if output is None:
            output = self._analysis_output

        abs_path = os.sep.join(str(self._analysis_log_file_path).split(os.sep)[:-1]) + \
            os.sep + output 

        if os.path.exists(abs_path):
            self._gui_warning.set_text("Warning: There is already a"\
                +" directory with that name.")
        else:
            self._gui_warning.set_text("") 

    def _select_log_file(self, widget=None, event=None, data=None):
        newlog = gtk.FileChooserDialog(title="Select log file", 
            action=gtk.FILE_CHOOSER_ACTION_OPEN, 
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, 
            gtk.STOCK_APPLY, gtk.RESPONSE_APPLY))

        f = gtk.FileFilter()
        f.set_name("Valid log files")
        f.add_mime_type("text")
        f.add_pattern("*.log")
        newlog.add_filter(f)


        result = newlog.run()
        
        if result == gtk.RESPONSE_APPLY:

            self._analysis_log_file_path = newlog.get_filename()
            self._gui_analysis_log_file.set_text("Log file: %s" % \
                str(self._analysis_log_file_path))

            self._path_warning()

            self._gui_start_button.set_sensitive(True)
            
        newlog.destroy()

    def _start(self, widget=None, event=None, data=None):

        self.hide()
        self._owner.analysis_Start_New(widget=self)
