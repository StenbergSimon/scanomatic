#!/usr/bin/env python

import os, os.path, sys
import time

class Power_Manager():
    def __init__(self, installed=False, path=None, on_string="", off_string="", DMS = None):
        self._installed = installed
        self._path = path
        self._on_string = on_string
        self._off_string = off_string
        self._on = None
        self._DMS = DMS

    def on(self):
        if self._installed and self._on != True:
            #print "*** Calling", self._path, self._on_string
            os.system(str(self._path)+' '+str(self._on_string))
            self._on = True
            if self._DMS:
                self._DMS("Power","Switching on",1)     

    def off(self):
        if self._installed and self._on != False:
            #print "*** Calling", self._path, self._off_string
            os.system('"'+str(self._path)+'" '+str(self._off_string))
            self._on = False
            if self._DMS:
                self._DMS("Power","Switching off",1)     

    def toggle(self):
        if self.on != None:
            if self.on == True:
                self.off()
            else:
                self.on()
        else:
            self.on()
