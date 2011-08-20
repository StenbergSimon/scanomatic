#!/usr/bin/env python

#Importin what is needed
import sys, os, gtk
from numpy import *

class Bioscreen_Run():
	def __init__(self, file_path = None):

		self.wells = []
		self.source = file_path
		self.times = None
		self.good_measurements = None

		if file_path != None:
			load_from_file(file_path)

	def load_from_file(self, location=None):
		if location == None:
			loader = gtk.FileChooserDialog(title="Select Bioscreen C - file", action=gtk.FILE_CHOOSER_ACTION_OPEN, \
				buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))

			loader.set_default_response(gtk.RESPONSE_OK)

			response = loader.run()

			if response == gtk.RESPONSE_OK:
				location = loader.get_filename()
			loader.destroy()

		try:
			fs = open(location,'r')
		except:
			print "Error: Failed to load the file: " + location
			

		type_of_file = fs.readline().split(" ")[0]

		if type_of_file == "READER:":
			no_data = True
			head_row = True
			well_names = []
			values = []

			for line in fs:
				line_tuple = line.split("\t")
				if no_data == True:
					if line_tuple[0][:9] == "TenthSec." or line_tuple[0][:4] == "0000":
						no_data = False

				if no_data == False:
					if head_row == True:
						if line_tuple[0].strip() == "TenthSec.":
							for item in line_tuple:
								if item.strip() != "":
									well_names.append(item.strip())
						else:
							if well_names == []:
								well_names = range(len(line_tuple))
							head_row = False

					if head_row == False:
						row = []
						for item in line_tuple:
							row.append(item.strip())

						values.append(row)
					head_row = True

			measures_count = len(values)
			for well in well_names:
				self.wells.append(Bioscreen_Well(matrix_size=measures_count, name=well))

			well_count = len(values[0])
			for well in range(well_count) :
				for measure in range(measures_count):
					try:
						self.wells[well].values[measure] = float(values[measure][well])
					except:
						measures_count = measure			
	def useful_range(self):
		measurements = range(len(self.wells[0].values))
		for well in self.wells:
			if well.name != "TenthSec.":
				for value_pos in measurements:
					if value_pos != -1:
						if well.values[value_pos] != 0:
							measurements[value_pos] = -1
		self.good_measurements =  array(measurements) == -1
					
	def smoothen(self):
		for well in self.wells:
			well.smoothen()

	def log2(self, force_from_raw=None):
		for well in self.wells:
			well.log2(force_from_raw=force_from_raw)

class Bioscreen_Well():
	def __init__(self, matrix_size=None, values=None, name=None, media=None):
		'''
			The Bioscreen Well contains all the measurments from one well.
			It has the functions generally applied to the wells

			A well is initiated with
			@values		A tuple of values
			@@name		A name for the well
			@@media		A media description
		'''

		self.name = name
		self.media = media
		if values != None:
			self.values = array(values, dtype=float64)
		elif matrix_size != None:
			self.values = zeros((matrix_size,), dtype=float64)
		else:
			self.values = None

		self.log2 = None
		self.smoothened = None
		
	def smoothen(self):

		no_collapse = empty(self.values.shape, dtype=float64)
		no_collapse[0] = self.values[0]

		for pos in range(no_collapse.shape[0]-1):
			if self.values[pos+1] > no_collapse[pos]:
				no_collapse[pos+1] = self.values[pos+1]
			else:
				no_collapse[pos+1] = no_collapse[pos]

		self.smoothened = empty(self.values.shape, dtype=float64)
		self.smoothened[0] = self.values[0]

		for pos in range(no_collapse.shape[0]-2):
			self.smoothened[pos+1] = mean(no_collapse[pos:pos+3])

		self.smoothened[-1] = self.values[-1]

	def log(self, force_from_raw = False):
		if self.smoothened == None or force_from_raw == True:
			self.log2 = log2(self.values)
		else:
			self.log2 = log2(self.smoothened)

class Prophecy_Run():
	def __init__(self, bioscreen_run):
		pass

class Prophecy_Well():
	def __init__(self, well):
		if well.smoothened == None:
			well.smoothen
		if well.log2 == None:
			well.log()


class Prophecy_Phenotype():
	def __init__(self):
		pass

class BBT_Phenotype():
	def __init__(self):
		pas
 

#well = Bioscreen_Well(values=[1, 2, 1, 4, 5, 6, 7, 8, 8, 9])
#well.smoothen()
#print well.smoothened
#well.log()
#print well.log2

bioscreen = Bioscreen_Run()
bioscreen.load_from_file()
bioscreen.useful_range()
print len(bioscreen.wells), bioscreen.wells[1].name
print bioscreen.wells[1].values
