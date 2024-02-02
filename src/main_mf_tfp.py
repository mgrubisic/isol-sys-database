############################################################################
#               Create database

# Created by:   Huy Pham
#               University of California, Berkeley

# Date created: January 2024

# Description:  Main workfile for TFP-MF database, reworked in new framework

# Open issues:  

############################################################################

from db import Database

main_obj = Database(400, n_buffer=8, seed=130, 
                    struct_sys_list=['MF'], isol_wts=[1, 0])

main_obj.design_bearings(filter_designs=True)
main_obj.design_structure(filter_designs=True)

main_obj.scale_gms()

#%% troubleshoot fatal case

# # run 364/400
# # troubleshoot building
# run = main_obj.retained_designs.iloc[1]
# from building import Building

# bldg = Building(run)
# bldg.model_frame()
# bldg.apply_grav_load()

# T_1 = bldg.run_eigen()

# bldg.provide_damping(80, method='SP',
#                                   zeta=[0.05], modes=[1])

# dt = 0.005
# ok = bldg.run_ground_motion(run.gm_selected, 
#                         run.scale_factor*1.0, 
#                         dt, T_end=60.0)

# from plot_structure import plot_dynamic
# plot_dynamic(run)

#%% analyze database

main_obj.analyze_db('tfp_mf_db.csv', save_interval=5)

# Pickle the main object
import pickle
with open('../data/tfp_mf_db.pickle', 'wb') as f:
    pickle.dump(main_obj, f)