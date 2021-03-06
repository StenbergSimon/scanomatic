#!/usr/bin/env python
#IMPORTS
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.pylab as plt_lab
import logging
import scipy.interpolate as scint
import scipy.stats as stats
import sys

def make_linear_interpolation(data):
    y, x = np.where(data != 0)
    Y, X = np.arange(data.shape[0]), np.arange(data.shape[1])
    logging.warning("ready for linear")
    f = scint.interp2d(x, y, data[y, x], 'linear')
    logging.warning("done linear interpol")
    return f(X,Y)

def make_linear_interpolation2(data):
    empty_poses = np.where(data == 0)
    f = data.copy()
    for i in xrange(len(empty_poses[0])):
        pos = [p[i] for p in empty_poses]
        a_pos = map(lambda x: x-1, pos)    
        a_pos = np.array(a_pos)
        a_pos[np.where(a_pos < 0)] = 0    
        b_pos = map(lambda x: x+1, pos)
        b_pos = np.array(b_pos)
        #logging.warning("Pos {0}, a_pos {1}, b_pos {2}, data.shape {3}"\
        #    .format(pos, a_pos, b_pos, data.shape))
        b_pos[np.where(b_pos > np.array(data.shape))] -= 1
        cell = data[a_pos[0]:b_pos[0], a_pos[1]:b_pos[1]]
        f[tuple(pos)] = cell[np.where(cell != 0)].mean()
        #logging.warning("Corrected position {0} to {1}".format(\
        #    pos, f[tuple(pos)]))
    return f

def make_cubic_interpolation(data):
    y, x = np.where(data !=0)
    Y, X = np.mgrid[0: data.shape[0], 0:data.shape[1]]
    f = scint.griddata((x,y), data[y,x], (X, Y), 'cubic')
    #logging.warning('Done some shit')
    nans = np.where(np.isnan(f))
    #logging.warning('Got {0} nans after cubic'.format(len(nans[0])))
    f[nans] = 0
    f2 = make_linear_interpolation2(f)
    #logging.warning('Linear done')
    f[nans] = f2[nans]
    return f

#NEWEST PRECOG RATES
def get_empty_data_structure(plate, max_row, max_column, depth=None, default_value=48):
    d = []
    for p in range(plate+1):
        if depth is None:
            if max_row[p] > 0 and max_column[p] > 0:
                d.append(np.ones((max_row[p]+1, max_column[p]+1))*default_value)
            else:
                d.append(np.array([]))
        else:
            if max_row[p] > 0 and max_column[p] > 0:
                d.append(np.ones((max_row[p]+1, max_column[p]+1, depth))*default_value)
            else:
                d.append(np.array([]))
    data = np.array(d)
    return data


#USING 1/4th AS NORMALISING GRID
def get_norm_surface(data, sigma=3, only_linear=False, surface_matrix=None):
    if surface_matrix is None:
        surface_matrix = {}
        for p in xrange(data.shape[0]):
            surface_matrix[p] = [[1,0],[0,0]]

    norm_surfaces = []
    norm_means = []
    for p in xrange(data.shape[0]):

        if len(data[p].shape) == 2:
            #exp_pp = map(lambda x: x/2, data[p].shape)
            #X, Y = np.mgrid[0:exp_pp[0],0:exp_pp[1]]*2
            norm_surface = np.zeros(data[p].shape)
            original_norm_surface = norm_surface.copy()
            #norm_surface[X, Y] = data[p][X, Y]
            #m = norm_surface[X, Y].mean()#.mean(1)
            #sd = norm_surface[X, Y].std()#.std(1)
            for x in xrange(data[p].shape[0]):
                for y in xrange(data[p].shape[1]):
                    if surface_matrix[p][x % 2][y % 2] == 1:
                        if np.isnan(data[p][x,y]) or data[p][x,y] == 48:
                            logging.warning("Discarded grid point ({0},{1})".format(\
                                x,y) + " on plate {0} because it {1}.".format(\
                                p, ["had no data", "had no growth"][data[p][x,y] == 48]))
                        else:
                            norm_surface[x, y] = data[p][x, y]

                        original_norm_surface[x,y] = np.nan
                        #print x, y
            original_norms = norm_surface[np.where(norm_surface != 0)]
            m = original_norms.mean()
            sd = original_norms.std()

            logging.info('Plate {0} has size {1} and {2} grid positions.'.format(\
                p, data[p].shape[0] * data[p].shape[1] , 
                len(np.where(norm_surface != 0)[0])))
            logging.info('High-bound outliers ({0}) on plate {1}'.format(\
                len(np.where(m + sigma*sd < original_norms)[0]), p))
            norm_surface[np.where(m + sigma*sd <\
                norm_surface)] = 0
            logging.info('Low-bound outliers ({0}) on plate {1}'.format(\
                len(np.where(m - sigma*sd > original_norms)[0]), p))
            norm_surface[np.where(m - sigma*sd >
                norm_surface)] = 0

            if only_linear:
                norm_surface = \
                    make_linear_interpolation(norm_surface)
            else:
                norm_surface = \
                    make_cubic_interpolation(norm_surface)
            norm_surfaces.append(norm_surface - original_norm_surface)
            norm_means.append(m)
            logging.info('Going for next plate')
        else:
            norm_surfaces.append(np.array([]))
            norm_means.append(None)
    return np.array(norm_surfaces), np.array(norm_means)


#NEW Luciano-format (And newest)
def get_data_from_file(file_path):
    try:
        fs = open(file_path, 'r')
    except:
        logging.error("Could not open file, no data was loaded")
        return None

    old_row = -1
    max_row = [-1,-1,-1,-1]
    max_column = [-1,-1,-1,-1]
    plate = 0
    data_store = {}
    meta_data_store = {}

    for line in fs:
        try:
            position, value, data = line.split("\t",2)
            try:
                plate, row_column = map(lambda x: x.strip(":"), 
                    position.split(" "))
                row, column = row_column.split("-")
            except:
                plate, row_column = position.split(":",1)
                row, column = row_column.split("-",1)

            plate, row, column = map(int, (plate, row, column))
            if max_row[plate] < row:
                max_row[plate] = row
            if max_column[plate] < column:
                max_column[plate] = column
            value = float(value.strip())
            data_store[(plate, row, column)] = value
            data = data.strip()[1:-1]
            data = data.split(",")
            try:
                data = map(lambda x: x.split("-"), data)
                data_rates = map(float, [d[0] for d in data])
                data_times = map(float, [d[1] for d in data])
                meta_data_store[(plate, row, column)] = (data_rates, data_times)
            except:
                pass
                #logging.warning("Position {0} has unrecognized meta-data format: {1}".\
                #    format((plate,row,column), data))
        except:
            try:
                position, data = line.split(" ", 1)
                row, column = map(int, position.split("-"))
                if row < old_row:
                    plate += 1
                data = eval(data)
                if len(data) == 5:
                    data_store[(plate, row, column)] = data
                    if row > max_row:
                        max_row = row
                    if column > max_column:
                        max_column = column
                old_row = row
            except:
                logging.warning("BAD data row: '%s'" % line)
            

    fs.close()    
    data = get_empty_data_structure(plate, max_row, max_column, default_value=48)
    for k,v in data_store.items():
        try:
            data[k[0]][k[1], k[2]] = v 
        except:
            logging.error("Got unexpected index {0} when data-shape is {1}".format(\
                k, data.shape))
            return None

    return {'data': data, 'meta-data': meta_data_store}

def get_dubious_phenotypes(meta_data_store, plate, max_row, max_column):

    if meta_data_store == {}:
        logging.info("No meta-data to analyse")
        return None
    
    data = get_empty_data_structure(plate, max_row, max_column)
    dubious = 0
    dubious2 = 0
    st_pt = 0
    ln_pts = 7
    side_buff = 1
    for loc, measures in meta_data_store.items():

        times = np.array(measures[0])
        OD = np.array(measures[1])
        f_OD = OD[st_pt:ln_pts][times[st_pt:ln_pts].argsort()[-1 - side_buff]] / \
            OD[st_pt:ln_pts][times[st_pt:ln_pts].argsort()[side_buff]]
        d_t = times[times[st_pt:ln_pts].argsort()[-1 - side_buff]] -\
            times[times[st_pt:ln_pts].argsort()[side_buff]]
        data[loc[0]][loc[1:]] = d_t * np.log(2) / np.log2(f_OD)
        if times[st_pt:ln_pts].min() in times[st_pt:ln_pts][-2:] and\
            times[st_pt:ln_pts].max() in times[st_pt:ln_pts][-2:]:

            logging.warning("Encountered dubious thing".format(d_t, f_OD))
            dubious += 1
        if times[st_pt:ln_pts].min() in times[st_pt:ln_pts][:2] or\
            times[st_pt:ln_pts].max() in times[st_pt:ln_pts][:2]:

            dubious2 += 1

    logging.info("Found {0} dubious type 1 and {1} type 2 dubious".\
        format(dubious, dubious2))

    return dubious, dubious2

def show_heatmap(data, plate_texts, plate_text_pattern, vlim=(0,5)):
    #PLOT A SIMPLE HEAT MAP
    fig = plt.figure()
    rows = np.ceil(data.shape[0] / 2.0)
    columns = np.ceil(data.shape[0] / 2.0)
    for p in xrange(data.shape[0]):
        if len(data[p].shape) == 2:
            ax = fig.add_subplot(rows, columns ,p+1, title=plate_text_pattern.format( plate_texts[p]))
            plt.imshow(data[p], vmin=vlim[0], vmax=vlim[1], interpolation="nearest")
            #plt.colorbar(ax = ax, orientation='horizontal')
        else:
            logging.warning("Plate {0} has no values (shape {1})".format(p, data[p].shape))
    fig.show()
    #PLOT DONE

def get_interactive_header(header,width=60):

    print "\n"
    print header.center(width)
    print ("-"*len(header)).center(width)
    print "\n"

def get_interactive_info(info_list, margin=6):

    for info in info_list:
        print " "*margin + info

    print "\n"

def get_interactive_labels(header, labels):

    get_interactive_header(header)
   
    plate_labels = {}

    for i in xrange(labels):
        plate_labels[i] = raw_input("Label for Plate {0}: ".format(i))

    return plate_labels


def get_interactive_norm_surface_matrix(data):

    get_interactive_header("This sets up the normalisation grid per plate")

    get_interactive_info([\
        "Each 2x2 square of colonies is expected to have both",
        "norm-grid positions and experiment posistions",
        "1 means it's a norm-grid position",
        "0 means it's an experiment position",
        "",
        "Default is:",
        "1 0 (first row)",
        "0 0 (second row)"])

    norm_surface_matrices = {}
    default_matrix = [[1,0],[0,0]]
    for p in xrange(data.shape[0]):
        norm_matrix = [None, None]
        print "-- For Plate {0} --".format(p)
        for row in xrange(2):
            r = raw_input("Row {0} ('enter for deafault') :".format(["one","two"][row>0]))
            try:
                norm_matrix[row] = map(int, r.split(" ",1))
            except:
                logging.info("Default is used for row {0}".format(row + 1))
                norm_matrix[row] = default_matrix[row]
        
        norm_surface_matrices[p] = norm_matrix

    return norm_surface_matrices


"""
#CREATING NORM TARGET ARRAY
data2 = np.zeros(data.shape, dtype=np.float64)

for p in range( data.shape[0] ):
    for x in range( exp_pp[0] ):
        for y in range( exp_pp[1] ):

            data2[p, x*2, y*2] = data[p, x*2, y*2]

data3 = data2.copy()
#PASS 1
for p in range( data.shape[0]):
    for x in range( exp_pp[0]):
        for y in range(exp_pp[1]):
            try:
                cell = data2[p, x*2: x*2+3, y*2: y*2+3]            
            except:
                try:
                    cell = data2[p, x*2: x*2+2, y*2: y*2+3] 
                except:
                    cell = data2[p, x*2: x*2+2, y*2: y*2+2]                       
            data3[p, x*2+1, y*2+1] = cell[np.where(cell != 0)].mean()
#PASS 2
"""
#DO NORM
def get_normalised_values(data, surface_matrices):

    norm_surface, norm_means = get_norm_surface(data, surface_matrix=surface_matrices)
    print norm_means
    normed_data = (data - norm_surface) + norm_means

    return normed_data

def get_experiment_results(data, surface_matrices):
    exp_pp = map(lambda x: map(lambda y: y/2, x.shape), data)
    e_mean = []
    e_sd = []
    """
    e_max = 0
    e_min = 0
    e_sd_max = 0
    e_sd_min = 0
    """
    if surface_matrices is None:
        surface_matrices = {}
        for p in xrange(data.shape[0]):
            surface_matrices[p] = [[1,0],[0,0]]

    #CALC EXPERIMENTS
    for p in range( data.shape[0] ):
     
        if len(data[p].shape) == 2: 
            exp_filter = np.array(surface_matrices[p]) == 0
            exp_mean = np.zeros(exp_pp[p], dtype=np.float64)
            exp_sd = np.zeros(exp_pp[p], dtype=np.float64)
            for x in range( exp_pp[p][0]):
                for y in range( exp_pp[p][1]):
                    cell = data[p][x*2:x*2+2, y*2:y*2+2]
                    exp_mean[x,y] = cell[np.where(exp_filter)].mean()
                    exp_sd[x,y] = cell[np.where(exp_filter)].std()

                #logging.warning("Plate {0}, row {1}".format(p, x))
            """
            if e_max < exp_mean.max():
                e_max = exp_mean.max()
            if e_min > exp_mean.min():
                e_min = exp_mean.min()
            if e_sd_max < exp_sd.max():
                e_sd_max = exp_sd.max()
            if e_sd_min > exp_sd.min():
                e_sd_min = exp_sd.min()
            """
            e_mean.append(exp_mean)
            e_sd.append(exp_sd)
        else:
            e_mean.append(np.array([]))
            e_sd.append(np.array([]))


    return np.array(e_mean), np.array(e_sd) #, (e_min, e_max), (e_sd_min, e_sd_max)
        
"""
#PLOT A SIMPLE HEAT MAP
fig = plt.figure()
for p in xrange(data.shape[0]):
    ax = fig.add_subplot(2,2, p+1, title="Rate {0}".format( plate_texts[p]))
    plt.imshow(e_mean[p], vmin=e_min, 
        vmax=e_max)
    plt.colorbar(ax = ax, orientation='horizontal')

fig.savefig("./exp_norm.png")
"""

"""
fig = plt.figure()
for p in xrange(data.shape[0]):
    ax = fig.add_subplot(4,2,2*p+1, title="Rate {0}".format( plate_texts[p]))
    plt.imshow(e_mean[p], vmin=e_min, 
        vmax=e_max)
    plt.colorbar(ax = ax, orientation='horizontal')
    ax = fig.add_subplot(4,2,2*p+2, title="Standard dev {0}".format( plate_texts[p]))
    plt.imshow(e_sd[p], vmin=e_sd_min, vmax=e_sd_max)
    plt.colorbar(ax = ax, orientation='horizontal')

fig.savefig("./exp_norm_mean_sd.png")
#PLOT DONE
"""

"""
e_mean2 = []
for p in xrange(data.shape[0]):

    print "{0} has mean {1} ({2}) and std {3} ({4})".format(\
        plate_texts[p], e_mean[p].mean(), 
            e_mean[p].mean() + norm_surface[p].mean(),
            e_mean[p].std(),
            (e_mean[p] + norm_surface[p].mean()).std())

    e_mean2.append(e_mean[p][np.where(e_mean[p] < e_mean[p].mean() + 6 * \
        e_mean[p].std())])
    print "Omitting outlier experiments {0}: mean {1} std {2}\n".format(\
        e_mean[p].shape[0] * e_mean[p].shape[1] - e_mean2[-1].shape[0],
        e_mean2[-1].mean(),
        e_mean2[-1].std())

"""
"""
#TTESTS
alpha = 0.05
n_sign = 0
n_controls = 15
ctrls = np.random.random_integers(0,len(t_exp),n_controls)
texp = np.array(t_exp)
tref = texp[ctrls,:].ravel()
not_ctrls = np.array([x for x in range(texp.shape[0]) if x not in ctrls])
texp2 = texp[not_ctrls,:]
for e in texp2:
    if stats.ttest_ind(tref, e)[1] < alpha:
        n_sign += 1
    
print "Found {0} Experimental False Positives, expected {1} using {2}\
 control positions(ratio {3})".format(
    n_sign,
    alpha*texp2.shape[0],
    n_controls,
    n_sign / (alpha*texp2.shape[0]))

"""

class Interactive_Menu():

    def __init__(self):

        self._menu = {'1': 'Load data',
            '2': 'Set normalisation grids',
            '3': 'Normalise data',
            '4': 'Calculate experiments',
            'P1': 'Set plot plate names',
            'P2': 'Show heatmap(s) of original data',
            'P3': 'Show heatmap(s) of normalised data',
            'P4': 'Show heatmap(s) of per experment data',
            'S1': 'Save the normalised data',
            'S2': 'Save the normalised data per experiment',
            'S3': 'Save the normalised data as np-array',
            'S4': 'Save the normalised data per experiment as np-array',
            'T': 'Terminate! (Quit)'}

        self._enabled_menus = {}
        self.set_start_menu_state()

        self._experiments = None
        self._experiments_sd = None
        self._file_path = None
        self._grid_surface_matrices = None
        self._plate_labels = None
        self._original_phenotypes = None 
        self._normalised_phenotypes = None
        self._original_meta_data = None 
        self._data_shapes = None 

    def set_start_menu_state(self):
        for k in self._menu.keys():
            if k in ['1', 'T']:
                self._enabled_menus[k] = True
            else:
                self._enabled_menus[k] = False

    def set_new_file_menu_state(self):
        self.set_start_menu_state()
        self.set_enable_menu_items(['2','3','P1'])

    def set_enable_menu_items(self, itemlist):

        for i in itemlist:
            self._enabled_menus[i] = True

    def set_disable_menu_items(self, itemlist):

        for i in itemlist:
            self._enabled_menus[i] = False

    def set_enable_menu_plots(self):

        if self._plate_labels is not None:

            if self._original_phenotypes is not None:

                self.set_enable_menu_items(["P2"])

            if self._normalised_phenotypes is not None:

                self.set_enable_menu_items(["P3"])

            if self._experiments is not None:

                self.set_enable_menu_items(["P4"])

    def print_menu(self):

        get_interactive_header("Menu{0}".format([" ({0})".format(self._file_path),""][\
            self._file_path is None]))
        
        for k in sorted(self._menu.keys()):

            if self._enabled_menus[k]:

                print " "*2 + k + " "*(6 -len(k)) + self._menu[k]

        print "\n"

    def get_answer(self):

        answer = str(raw_input("Run option: ")).upper()

        if answer in self._menu.keys() and self._enabled_menus[answer]:
            return answer
        else:
            logging.info("{0} is not a valid option".format(answer))

            return None

    def set_plate_labels(self):

        self._plate_labels =  get_interactive_labels("Setting plate names", 
            self._original_phenotypes.shape[0])
        logging.info("New labels set")
        self.set_enable_menu_plots()

    def load_file(self, file_path):


        file_contents = get_data_from_file(file_path)

        if file_contents is not None:
            

            self._file_path = file_path
            self._original_phenotypes = file_contents['data']
            self._original_meta_data = file_contents['meta-data']

            mins = []
            maxs = []

            for p in xrange(self._original_phenotypes.shape[0]):
                if len(self._original_phenotypes[p].shape) == 2:
                    mins.append(self._original_phenotypes[p].min())
                    maxs.append(self._original_phenotypes[p].max())
                else:
                    mins.append("N/A")
                    maxs.append("N/A")

            logging.info("File had {0} plates,".format(self._original_phenotypes.shape[0])+\
                "and phenotypes ranged from {0} to {1} per plate.".format(\
                mins, maxs))

            self.set_new_file_menu_state()
            return True

        else:
            return False

    def do_task(self, task):

        if task == "1":

            file_path = str(raw_input("The path to the file: "))
            if self.load_file(file_path) == False:

                logging.warning("Nothing changed...")

        elif task == "2":

            self._grid_surface_matrices = get_interactive_norm_surface_matrix(self._original_phenotypes)
            logging.info("New normalisation grid set!")

        elif task == "3":

            self._normalised_phenotypes = get_normalised_values(self._original_phenotypes, 
                self._grid_surface_matrices)

            self._experiments, self._experiments_sd = get_experiment_results(\
                self._normalised_phenotypes, self._grid_surface_matrices)

            self.set_enable_menu_items(["4","S1","S3", "S2", "S4"])
            self.set_enable_menu_plots()

        elif task == "P1":

            self.set_plate_labels()

        elif task == "P2":
        
            show_heatmap(self._original_phenotypes, 
                self._plate_labels, 
                "Phenotypes with position effect (Plate {0})" , vlim=(0,5))

        elif task == "P3":
        
            show_heatmap(self._normalised_phenotypes, 
                self._plate_labels, 
                "Phenotypes (Plate {0})" , vlim=(0,5))

        elif task == "P4":

            show_heatmap(self._experiments, 
                self._plate_labels, 
                "Mean experiment phenotype (Plate {0})" , vlim=(0,5))

            show_heatmap(self._experiments_sd, 
                self._plate_labels, 
                "Experiment phenotype std (Plate {0})" , vlim=(0,5))

        elif task in ["S1", "S3"] :

            header = "Saving normalised phenotypes as {0}".format(["csv","numpy-array"][task == "S3"])
            if self._save(self._normalised_phenotypes, header,
                save_as_np_array = (task == "S3")):

                logging.info("Data saved!")

            else:

                logging.warning("Could not save data, probably path is not valid")

        elif task in ["S2", "S4"]:

            header = "Saving experiment phenotypes as {0}".format(["csv","numpy-array"][task == "S3"])
            if self._save(self._experiment, header,
                save_as_np_array = (task == "S3"), data2=self._experiment_sd):

                logging.info("Data saved!")

            else:

                logging.warning("Could not save data, probably path is not valid")

            
    def _save(self, data, header, save_as_np_array=False, data2=None):

        get_interactive_header(header)
        get_interactive_info(['Note that the directory must exist.',
            'Also note that this will overwrite existing files (if they exist)'])

        if self._plate_labels == None:
            self.set_plate_labels()

        file_path = str(raw_input("Save-path (with file name): "))

        if save_as_np_array:
            try:
                np.save(file_path, data)
            except:
                return False

            if data2 is not None:

                file_path = file_path.split(".")
                file_path = ".".join(file_path[:-1]) + "2" + file_path[-1]
              
                try:
                    np.save(file_path, data2)
                except:
                    return False

                logging.info("Also saved secondary data as '{0}'".format(file_path))
        else:
            try:
                fs = open(file_path, 'w')
            except:
                return False


            for p in xrange(data.shape[0]):
                fs.write("START PLATE {0}\n".format(self._plate_labels[p]))

                if len(data[p].shape) == 2:
                    for x in xrange(data[p].shape[0]):
                        for y in xrange(data[p].shape[1]):
                            if data2 is None:
                                fs.write("{0}\t{1}\t{2}\t{3}\n".format(\
                                    p,x,y, data[p][x,y]))
                            else:
                                fs.write("{0}\t{1}\t{2}\t{3}\t{4}\n".format(\
                                    p,x,y, data[p][x,y]), data2[p][x,y])


                fs.write("STOP PLATE {0}\n".format(self._plate_labels[p]))
            fs.close()

        return True

    def run(self):

        get_interactive_header("This script will take care of positional effects")
        get_interactive_info(["It is in alpha-state,",
            "so let Martin know what doesn't work.",
            "And don't expect everything to work."])

        answer = None

        while answer != 'T':

            self.print_menu()

            answer = self.get_answer()

            if answer is not None:
                self.do_task(answer)

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    interactive_menu = Interactive_Menu()
    if len(sys.argv) == 2:
        interactive_menu.load_file(sys.argv[1])    

    interactive_menu.run()

"""


#############################################################################
#OLD STUFF
#
#############################################################################

#LOADING DATA
X = plt_lab.csv2rec("analysis_GT.csv", skiprows=1, delimiter="\t")

X_list = []

for x in X:
    X_list.append([x[1],x[3],x[5],x[7]])


Y = np.asarray(X_list)
Y2 = np.reshape(Y, (16, 24,4))
#DATA LOADED

#CLEAR OUT OUT-LIERS
Y2[np.where(Y2[:,:,:]>10)] = np.nan

#ALTERNATIVE DATA
#X = plt_lab.csv2rec("analysis_locked_baseline.csv", skiprows=1, delimiter="\t")
#X_list = []
#for x in X:
#    X_list.append([x[2],x[5],x[8],x[11]])

#Z = np.asarray(X_list)
#Z2 = np.reshape(Y, (16, 24,4))
#ALTERNATIVE DATA LOADED

#PLOT A SIMPLE HEAT MAP
fig = plt.figure()
for p in xrange(Y2.shape[2]):
    fig.add_subplot(2,2,p+1, title="Plate %d" % p)
    plt.imshow(Y2[:,:,p])

fig.show()
#PLOT DONE

#PLOT HISTOGRAM
fig = plt.figure()
plt.clf()
plt.hist(Y2[np.where(Y2[:,:,0]>0)].ravel(), bins=25)
plt.show()
#PLOT DONE

#PLOTTING DATA VS ALTERNATIVE DATA...
plt.clf()
for i in xrange(Y2.shape[2]):
    plt.plot(Y2[:,:,i].ravel(), Z2[:,:,i].ravel(), '.', label="Plate %d" % i)


plt.xlabel('Rate')
plt.ylabel('Lowest value')
plt.legend()
plt.show()
#PLOT DONE

#NEIGHBOUR COUNT ARRAY
N = Y2.copy()
N[:,:,:] = 4 + 4*(1/np.sqrt(2))
N[0,:,:] = 3 + 2*(1/np.sqrt(2))
N[-1,:,:] = 3 + 2*(1/np.sqrt(2))
N[:,0,:] = 3 + 2*(1/np.sqrt(2))
N[:,-1,:] = 3 + 2*(1/np.sqrt(2))
N[0,0,:] = 2 + (1/np.sqrt(2))
N[-1,0,:] = 2 + (1/np.sqrt(2))
N[-1,-1,:] = 2 + (1/np.sqrt(2))
N[0,-1,:] = 2 + (1/np.sqrt(2))

#THE NUMBER OF NEIGHBOURS PER TYPE
neighbours = [2 + (1/np.sqrt(2)), 3 + 2*(1/np.sqrt(2)), 4 + 4*(1/np.sqrt(2))]

#MAKE NEIGHBOURDEPENDENT PLOT
plt.clf()
fig = plt.figure()

for i in xrange(N.shape[2]):
    fig.add_subplot(2,2,i+1, title="Plate %d" % i)
    plt.boxplot([Y2[np.where(N[:,:,i] == neighbours[0])].ravel(), 
        Y2[np.where(N[:,:,i] == neighbours[1])].ravel(),
        Y2[np.where(N[:,:,i] == neighbours[2])].ravel()],
        positions=neighbours)
    plt.ylabel('Rate')
    plt.xlabel('Neighbours')


fig.show()
#PLOT END

#POSITIONAL EFFECT

Y2[np.where(np.isnan(Y2[:,:,:]))] = 0

#STENCIL A
#n = 4 + 4 / np.sqrt(2)
#kernel = np.asarray([[-1/np.sqrt(2), -1.0,-1/np.sqrt(2)],[-1, n,-1],[-1/np.sqrt(2), -1, -1/np.sqrt(2)]])
#STENCIL B
n=6
kernel = np.asarray([[-1/2, -1.0,-1/2],[-1, n,-1],[-1/2, -1, -1/2]])
N2 = []
for i in xrange(Y2.shape[2]):
    N2.append(fftconvolve(kernel, Y2[:,:,i], mode='full'))


#PLOT POSITIONAL EFFECT
fig = plt.figure()
for p in xrange(Y2.shape[2]):
    fig.add_subplot(2,2,p+1, title="Plate %d" % p)
    plt.imshow(N2[p])
    plt.colorbar()

fig.show()


Y3 = 1 / Y2

#STENCILS
kernel = np.asarray([[0.5, 1.0, 0.5],
                    [1.0, 0, 1.0],
                    [0.5, 1.0, 0.5]])

kernel = np.asarray([[1/np.sqrt(2), 1.0,1/np.sqrt(2)],
                    [1.0, 0, 1.0],
                    [1/np.sqrt(2), 1.0, 1/np.sqrt(2)]])
"""

def vector_orth_dist(x, y, p1):
    """
    @param x: is a vector of X-measures
    @param y: is a vector of corresponding Y-measures
    @param p1: is a polynomial returned from numpy.poly1d
    """
    #
    #get the point where ax + b = 0
    x_off = -p1[0]/p1[1]
    #
    #p's unit vector creation
    p_unit = np.asarray((1-x_off,p1(1)))
    p_unit = p_unit / np.sqrt(np.sum(p_unit**2))
    #
    #its orthogonal vector
    p_u_orth = np.asarray((-p_unit[1], p_unit[0]))
    #
    #distances:
    dists = np.zeros(x.shape)
    for d in xrange(dists.size):
        dists[d] = np.sum(np.asarray((x[d]-x_off,y[d]))* p_u_orth)
    #
    return dists
"""
#PLOT THE POSITIONAL EFFECT
plt.clf()
fig = plt.figure()
Ps = []
Ns = []

for p in xrange(Y2.shape[2]):
    C = c2(Y2[:,:,p], kernel, mode='nearest').ravel() / np.sum(kernel)
    z1  = np.polyfit(C, Y2[:,:,p].ravel(),1)
    Ps.append(z1)
    p1 = np.poly1d(z1)
    l = np.linspace(C.min(), C.max(), num=100)
    Ns.append( vector_orth_dist(C, Y2[:,:,p].ravel(),p1) + np.mean(Y2[:,:,p]))
    fig.add_subplot(2,2,p+1, title="Plate %d" % p)
    plt.plot(C, Y2[:,:,p].ravel(), 'b.')
    plt.plot(l, p1(l), 'r-')
    plt.gca().annotate(s=str("%.3f" % z1[0]) + "x + " + str("%.3f" % z1[1]), 
        xy=(l[5]+0.6,p1(l[5])+0.3))
    plt.xlim(1.4, 4)
    plt.ylim(1, 4.5)
    plt.ylabel('Colony Generation Time')
    plt.xlabel('How cool your neighbours are (Very <-> Not)')

fig.show()

#PLOT SECONDARY POSITIONAL EFFECTS
fig = plt.figure()
Ns2 = []

for p in xrange(Y2.shape[2]):
    C = c2(np.reshape(Ns[p], (16,24)), kernel, mode='nearest').ravel() / np.sum(kernel)
    z1  = np.polyfit(C, Ns[p],1)
    p1 = np.poly1d(z1)
    l = np.linspace(C.min(), C.max(), num=100)
    Ns2.append( vector_orth_dist(C, Ns[p], p1) + np.mean(Ns[p]))
    fig.add_subplot(2,2,p+1, title="Plate %d" % p)
    plt.plot(C, Ns[p], 'b.')
    plt.plot(l, p1(l), 'r-')
    plt.gca().annotate(s=str("%.3f" % z1[0]) + "x + " + str("%.3f" % z1[1]),
        xy=(l[5],p1(l[5])+0.6))
    plt.xlim(2.0, 3.5)
    plt.ylim(1.5, 4.0)
    plt.ylabel('Colony Generation Time')
    plt.xlabel('How cool your neighbours are (Very <-> Not)')

plt.show()

#PLOT THE PROCESSED VS RAW HEAT MAPS
plt.clf()
fig = plt.figure()

for i in xrange(N.shape[2]):
    fig.add_subplot(2,2,i+1, title="Plate %d" % i)
    plt.boxplot([Y2[:,:,i].ravel(),
        Ns[i]])
    plt.annotate(s="std: %.3f" % np.std(Y2[:,:,i].ravel()), xy=(1,4) )
    plt.annotate(s="std: %.3f" % np.std(Ns[i]), xy=(2,4) )
    plt.ylabel('Generation Time')
    plt.xlabel('Untreated vs Normalized')
    plt.ylim(1.0,4.5)

fig.show()

#UNUSED
fig = plt.figure()

for p in xrange(Y2.shape[2]):
    fig.add_subplot(2,2,p+1, title="Plate %d" % p)
    plt.plot(c2(Y3[:,:,p], kernel, mode='constant', cval=np.mean(Y3[:,:,p]))\
        .ravel(), Y2[:,:,p].ravel(), 'b.')
    plt.ylabel('Colony rate')
    plt.xlabel('How cool your neighbours are (Not <-> Very)')

fig.show()

#PLOT START EFFECT
fig = plt.figure()

for p in xrange(Y2.shape[2]):
    fig.add_subplot(2,2,p+1, title="Plate %d" % p)
    plt.plot(Z2[:,:,p].ravel(), Ns[p], 'b.')
    plt.ylabel('Colony rate')
    plt.xlabel('Start-value')
    plt.xlim(0,200000)
    plt.ylim(0,4)

plt.show()

#
#
#
fs = open('slow_fast_test.csv', 'w')
y_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
yeasts = ['wt','Hog1']
fig = plt.figure()
for p in xrange(4):
    fs.write("\nPlate " + str(p+1) + "\n")
    fs.write("Row\tCol\tType\n")
    p_layout = np.random.random((8,12))>0.8
    for x in xrange(p_layout.shape[0]):
        for y in xrange(p_layout.shape[1]):
            fs.write(y_labels[x] + "\t" + str(y+1) + "\t" + yeasts[p_layout[x,y]] + "\n")
    fig.add_subplot(2,2,p+1)
    plt.imshow(p_layout, aspect='equal', interpolation='nearest')
    plt.xticks(np.arange(12), np.arange(12)+1)
    plt.yticks(np.arange(8), y_labels)
    plt.ylabel('Columns')
    plt.xlabel('Rows')

fs.close()
plt.show()
"""
