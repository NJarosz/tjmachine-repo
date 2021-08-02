import pickle

def read_pckl_counts(pcklfile):
    pickle_in = open(pcklfile, "rb")
    pkl_dict = pickle.load(pickle_in)
    return pkl_dict

def save_vars(dict, pkl_file):
    with open(pkl_file, "wb") as pckl:
        pickle.dump(dict, pckl)

Prod_vars_dict = {"part": 0,
                  "mach": 0,
                  "countset": 0}

counts_dict = {"totalcount": 0,
               "runcount": 0}

vars_file = "/home/pi/Documents/vars.pickle"
count_file = "/home/pi/Documents/counts.pickle"

save_vars(Prod_vars_dict, vars_file)
save_vars(counts_dict, count_file)
