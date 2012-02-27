#!/usr/bin/env python
"""Part of analysis work-flow that holds a grid arrays"""

__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson", "Mats Kvarnstroem", "Andreas Skyman"]
__license__ = "GPL v3.0"
__version__ = "0.992"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"


#
# DEPENDENCIES
#

import numpy as np
from scipy.optimize import fsolve
import os, types

#
# SCANNOMATIC LIBRARIES
#

import analysis_grid_array_dissection as array_dissection
import analysis_grid_cell as grid_cell

#
# CLASS: Grid_Array
#

class Grid_Array():
    def __init__(self, parent, identifier, pinning_matrix):

        self._parent = parent

        if type(identifier) == types.IntType:
            identifier = ("unknown", identifier)
        elif len(identifier) == 1:
            identifier = ["unknown", identifier[0]]
        else:
            identifier = [identifier[0], identifier[1]]

        self._identifier = identifier
        self._analysis = array_dissection.Grid_Analysis()
        self._pinning_matrix = None

        self._grid_cell_size = None
        self._grid_cells = None

        self._features = []

        self.R = None
        self._best_fit_rows = None
        self._best_fit_coulmns = None

        if pinning_matrix != None:
            self.set_pinning_matrix(pinning_matrix)

        self._polynomial_coeffs = None
        if parent is not None:
            
            self._config_calibration_polynomial = parent._program_config_root +\
                os.sep + "calibration.polynomials"

            get_poly = True
            try:

                fs = open(self._config_calibration_polynomial, 'r')
            except:
                print "ERROR: Cannot open polynomial info file"
                get_poly = False

            if get_poly:

                self._polynomial_coeffs = []
                for l in fs:
                    l_data = eval(l.strip("\n"))
                    if type(l_data) == types.ListType:
                        self._polynomial_coeffs = l_data[-1]
                        break

                fs.close()

                if self._polynomial_coeffs == []:
                    self._polynomial_coeffs = None
    #
    # SET functions
    #

    def set_pinning_matrix(self, pinning_matrix):
        """
            set_pinning_matrix sets the pinning_matrix.

            The function takes the following argument:

            @pinning_matrix  A list/tuple/array where first position is
                            the number of rows to be detected and second
                            is the number of columns to be detected.

        """

        self._pinning_matrix = pinning_matrix

        self._grid_cells = []
        self._features = []

        for row in xrange(pinning_matrix[0]):

            self._grid_cells.append([])
            self._features.append([])

            for column in xrange(pinning_matrix[1]):
                self._grid_cells[row].append(grid_cell.Grid_Cell(\
                    [self._identifier,  [row, column]]))
                self._features[row].append(None)

    #
    # Get functions
    # 


    def get_p3(self, x):
        """
            returns the solution to:

                self.gs_a * x^3 + self.gs_b * x^2 + self.gs_c * x + self.gs_d

        """

        return self.gs_a * (x**3) + self.gs_b * (x**2) + self.gs_c * x + self.gs_d


    def get_transformation_matrix(self, gs_values=None, gs_fit=None, gs_indices=None, y_range = (0,255), fix_axis=False):
        """
            get_transformation_matrix takes an coefficient array of a
            polynomial fit of the 3rd degree and calculates a matrix
            of all solutions for all the integer steps of the y-range
            specified.

            The function takes two arguments:

            @gs_values  A numpy array or a list of gray-scale values

            @gs_fit     A numpy array of the coefficients as returned
                        by numpy.polyfit, assuming 3rd degree 
                        solution

            @gs_indices An optional list of gs indices if not a simple
                        enumerated range

            @y_range    A tuple having the including range limits 
                        for the solution.

            @fix_axis   An optional possibility to fix the gs-axis,
                        else it will be made increasing (transformed with
                        -1 if not). Lowest value will also be set to 0,
                        assuming a continious series.

            The function returns a list of transformation values

        """

        if gs_values != None:

            if gs_indices == None:
                gs_indices  = range(len(gs_values))

            if gs_indices[0] > gs_indices[-1]:
                gs_indices = map(lambda x: x * -1, gs_indices)

            if gs_indices[0] != 0:
                gs_indices = map(lambda x: x - gs_indices[0], gs_indices)

            tf_matrix = np.zeros((y_range[1]+1))

            p = np.poly1d(np.polyfit(gs_indices,\
                gs_values, 3))

            self.gs_a = p.c[0]
            self.gs_b = p.c[1]
            self.gs_c = p.c[2]
            self.gs_d = p.c[3]

            for i in xrange(256):

                #moving the line along y-axis
                self.gs_d = p.c[3] - i
                x = fsolve(self.get_p3, gs_values[0])

                #setting it back to get the values
                self.gs_d = p.c[3]
                tf_matrix[int(round(self.get_p3(x)))] = x


        else:    

            tf_matrix = []

            for y in range(y_range[0],y_range[1]+1):

                #Do something real here
                #The caluclated value shoud be a float
                x = float(y)
                
                tf_matrix.append(x)

        ###DEBUG TF-matrix
        #print "Transformation matrix:\n", list(tf_matrix)
        ###END DEBUG

        return tf_matrix

    def get_analysis(self, im, gs_fit=None, gs_values=None, use_fallback=False,\
        use_otsu=True, median_coeff=None, verboise=False, visual=False, \
        watch_colony=None, supress_other=False, save_grid_image=False, \
        save_grid_name=None, grid_lock=False, identifier_time=None):

        """
            @param im: An array / the image

            @param gs_fit : An array of the fitted coefficients for the grayscale

            @param gs_values : An array of the grayscale pixelvalues, if 
            submittet gs_fit is disregarded

            @param use_otsu : Causes thresholding to be done by Otsu
            algorithm (Default)

            @param median_coeff : Coefficient to threshold from the
            median when not using Otsu.

            @param verboise : If a lot of things should be printed out

            @param visual : If visual information should be presented.

            @param save_grid_image : Causes the script to save the plates' 
            grid placement as images. Conflicts with visual, so don't use 
            visual if you want to save

            @param save_grid_name : A custom name for the saved image, if none
            is submitted, it will be grid.png in current directory.

            @param grid_lock : Default False, if true, the grid will only be
            gotten once and then reused all way through.

            @param identifier_time : A time index to update the identifier with

            The function returns two arrays, one per dimension, of the
            positions of the spikes and a quality index

        """

        if identifier_time is not None:
            self._identifier[0] = identifier_time

        debug_per_plate = False

        #DEBUGHACK
        #grid_lock = False
        #visual = True
        #verboise = True
        #save_grid_image = True
        #debug_per_plate = True
        #DEBUGHACK - END

        self.watch_source = None
        self.watch_scaled = None
        self.watch_blob = None
        self.watch_results = None

        if debug_per_plate:
            raw_input("Waiting to start next plate (press Enter)")    

        has_previous_rect = True

        if not grid_lock or self._best_fit_rows is None:
            #if rows is None so is columns 

            best_fit_rows, best_fit_columns, R = self._analysis.get_analysis(\
                im, self._pinning_matrix, use_otsu, median_coeff, verboise, 
                visual)


            if verboise:
                print "*** Grid (rows x columns):"
                print best_fit_rows
                print best_fit_columns
                print

            if best_fit_rows == None or best_fit_columns == None:
                self._best_fit_rows = None
                self._best_fit_coulmns = None
                return None
            elif self.R is None or R < 20:
                self._best_fit_rows = best_fit_rows
                self._best_fit_columns = best_fit_columns

            self.R = R


            if self._grid_cell_size == None:
                self._grid_cell_size = map(round, self._analysis.best_fit_frequency[:])
                #print self._grid_cell_size
                has_previous_rect = False

        #else:
            ###DEBUG SIZE OF CELL
            #print  "I,",self._identifier, ", give shape ", self._grid_cell_size, " and keep position"
            ###DEBUG END

        #total_steps = float(self._pinning_matrix[0] * self._pinning_matrix[1])


        #Normalising towards grayscale before anything is done on the colonies
        transformation_matrix = None
        #KODAK neutral scale
        gs_indices = np.asarray([82,78,74,70,66,62,58,54,50,46,42,38,34,30,26,
            22,18,14,10,6,4,2,0])

        #TEMPORARY SOLUTION TO MAKE AGAR APPEAR AS 0 AND BIOMASS BE POSITIVE
        gs_indices -= 75
        gs_indices *= -1
        #TEMPORARY SOLUTION END

        if gs_values == None:
            transformation_matrix = self.get_transformation_matrix(\
                gs_fit=gs_fit, gs_indices=gs_indices)
        else:
            transformation_matrix = self.get_transformation_matrix(\
                gs_values = gs_values, gs_indices=gs_indices)

        #print "\n***Transformation matrix"
        #print transformation_matrix

        #if watch_colony != None:
        #    ul = self._grid_cells[watch_colony[1]][watch_colony[2]].get_top_left()
        #    lr = self._grid_cells[watch_colony[1]][watch_colony[2]].get_bottom_right()
        #    self.watch_source = im[ul[1]:lr[1],ul[0]:lr[0]]


        #if transformation_matrix != None:
            #There's probably some faster way
            #for x in xrange(im.shape[0]):
                #for y in xrange(im.shape[1]):
                    #im[x,y] = transformation_matrix[im[x,y]]
        #print "*** Analysing grid:"
        if visual or save_grid_image:
            import matplotlib.pyplot as plt
            grid_image = plt.figure()
            grid_plot = grid_image.add_subplot(111)
            grid_plot.imshow(im)
            if save_grid_name is None:
                save_grid_name = "plate.png"

        for row in xrange(self._pinning_matrix[0]):
            if visual or save_grid_image:
                grid_plot.plot(\
                    np.ones(len(self._best_fit_columns))*\
                    self._best_fit_rows[row],
                    np.array(self._best_fit_columns),
                    'r-')
            for column in xrange(self._pinning_matrix[1]):
                if visual or save_grid_image:
                    grid_plot.plot(\
                        np.array(self._best_fit_rows),
                        np.ones(len(self._best_fit_rows))*\
                            self._best_fit_columns[column], 'r-')
                if supress_other == False or (watch_colony != None and \
                        watch_colony[1] == row and watch_colony[2] == column):

                    self._grid_cells[row][column].set_center( \
                        (self._best_fit_rows[row], 
                            self._best_fit_columns[column]) , self._grid_cell_size)

                    coord_2nd = self._grid_cells[row][column].get_first_dim_as_tuple()
                    coord_1st = self._grid_cells[row][column].get_second_dim_as_tuple()

                    if transformation_matrix != None:
                        #There's probably some faster way
                        #print coord_1st, coord_2nd, im.shape
                        for x in xrange(int(coord_1st[0]),int(np.ceil(coord_1st[1]))):
                            for y in xrange(int(coord_2nd[0]),int(np.ceil(coord_2nd[1]))):
                                im[x,y] = transformation_matrix[im[x,y]]

                    self._grid_cells[row][column].set_data_source( \
                        im[coord_1st[0]:coord_1st[1],\
                        coord_2nd[0]:coord_2nd[1]].copy() )


                    if watch_colony != None:
                        if row == watch_colony[1] and column == watch_colony[2]:
                            self.watch_scaled = im[coord_1st[0]:coord_1st[1],\
                                coord_2nd[0]:coord_2nd[1]]
                            
                    #if visual:
                        #pass
                        #plt.plot(self._grid_cells[row][column].center[0],
                        #    self._grid_cells[row][column].center[1] , 'k.')

                        #plt.plot(np.asarray(coord_1st),np.asarray(coord_2nd),'k')              

                    #This happens only the first time
                    if has_previous_rect == False:
                        self._grid_cells[row][column].attach_analysis(
                            blob=True, background=True, cell=True, 
                            use_fallback_detection=use_fallback, run_detect=False)

                    #This step only detects the objects
                    self._grid_cells[row][column].get_analysis(no_analysis=True, 
                        remember_filter=True)

                    ###DEBUG RE-DETECT PART1
                    #from matplotlib import pyplot as plt
                    #debug_plt = plt.figure()
                    #debug_plt.add_subplot(221)
                    #plt.imshow(self._grid_cells[row][column].get_item('blob').filter_array)
                    #debug_plt.add_subplot(223)
                    #plt.imshow(self._grid_cells[row][column].get_item('blob').grid_array)
                    ###DEBUG END PART1

                    #Transfer data to 'Cell Estimate Space'
                    self._grid_cells[row][column].set_new_data_source_space(\
                        space='cell estimate', bg_sub_source = \
                        self._grid_cells[row][column].get_item('background').filter_array\
                        , polynomial_coeffs = self._polynomial_coeffs)

                    #This step re-detects in Cell Estimate Space
                    #self._grid_cells[row][column].get_analysis(no_analysis=True,\
                    #    remember_filter=True, use_fallback=True)

                    ###DEBUG RE-DETECT PART2
                    #debug_plt.add_subplot(222)
                    #plt.imshow(self._grid_cells[row][column].get_item('blob').filter_array)
                    #debug_plt.add_subplot(224)
                    #plt.imshow(self._grid_cells[row][column].get_item('blob').grid_array)
                    #debug_plt.show()
                    #plot = raw_input('waiting: ')
                    ###DEBUG END


                    ###DEBUG CODE
                    #from matplotlib import pyplot as plt
                    #plt.clf()
                    #fig = plt.figure()
                    #ax = fig.add_subplot(221, title="Blob")
                    #fig.gca().imshow(self._grid_cells[row][column].\
                        #get_item('blob').filter_array)
                    #ax = fig.add_subplot(222, title ="Background")
                    #fig.gca().imshow(self._grid_cells[row][column].\
                        #get_item('background').filter_array)
                    #ax = fig.add_subplot(223, title = "Image")
                    #ax_im = fig.gca().imshow(self._grid_cells[row][column].\
                        #get_item('background').grid_array, vmin=0, vmax=3500,
                        #)
                    #fig.colorbar(ax_im)
                    #fig.savefig("debug_cell_t" + ("%03d" % self._identifier[0]))
                    ###END DEBUG CODE

                    #This step does analysis on the previously detected objects
                    self._features[row][column] = \
                        self._grid_cells[row][column].get_analysis(no_detect=True)

                    if watch_colony != None:
                        if row == watch_colony[1] and column == watch_colony[2]:
                            self.watch_blob = \
                                self._grid_cells[row][column].\
                                get_item('blob').filter_array

                            self.watch_results = self._features[row][column]
        if visual:
            grid_image.show() 
            plt.close(grid_image)
            del grid_image
        elif save_grid_image:
            grid_image.savefig(save_grid_name)
            plt.close(grid_image)
            del grid_image
                #print str(((row+1)*self._pinning_matrix[1] + column+1)/total_steps) + "%"
        return self._features 