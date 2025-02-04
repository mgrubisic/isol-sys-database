############################################################################
#               Troubleshooting plots

# Created by:   Huy Pham
#               University of California, Berkeley

# Date created: Aug 2023

# Description:  Various plots for structure

# Open issues:  

############################################################################

def plot_dynamic(run, data_dir='./outputs/'):
    import pandas as pd
    import matplotlib.pyplot as plt
    plt.close('all')
    structure_type = run.superstructure_system
    
    # L_bay = run.L_bay
    h_story = run.h_story
    num_bays = run.num_bays
    
    # TODO: collect Sa values, collect validation indicator (IDA level)
    num_stories = run.num_stories
    
    # gather EDPs from opensees output
    # also collecting story 0, which is isol layer
    story_names = ['story_'+str(story)
                   for story in range(0,num_stories+1)]
    story_names.insert(0, 'time')
    
    isol_columns = ['time', 'x', 'z', 'rot']
    isol_disp = pd.read_csv(data_dir+'isolator_displacement.csv', sep=' ', 
                                 header=None, names=isol_columns)
    
    force_columns = ['time', 'iFx', 'iFy', 'iFz', 'iMx', 'iMy', 'iMz', 
                    'jFx', 'jFy', 'jFz', 'jMx', 'jMy', 'jMz']
    isol_force = pd.read_csv(data_dir+'isolator_forces.csv', sep=' ', 
                                 header=None, names=force_columns)
    
    
    story_disp = pd.read_csv(data_dir+'inner_col_disp.csv', sep=' ', 
                                 header=None, names=story_names)
    isol_disp = pd.read_csv(data_dir+'isolator_displacement.csv', sep=' ', 
                                 header=None, names=isol_columns)
    
    basic_columns = ['time', 'iFx', 'iFy', 'iFz', 'iMx', 'iMy', 'iMz']
    
    if structure_type == 'CBF':
        res_columns = ['stress1', 'strain1', 'stress2', 'strain2', 
                       'stress3', 'strain3', 'stress4', 'strain4']
        left_brace_res = pd.read_csv(data_dir+'brace_left_str.csv', sep=' ', 
                                     header=None, names=res_columns)
        
        right_brace_res = pd.read_csv(data_dir+'brace_right_str.csv', sep=' ', 
                                      header=None, names=res_columns)
        
        ghost_columns = ['time', 'axial_strain']
        left_brace_def = pd.read_csv(data_dir+'left_ghost_deformation.csv', sep=' ', 
                                      header=None, names=ghost_columns)
        right_brace_def = pd.read_csv(data_dir+'right_ghost_deformation.csv', sep=' ', 
                                      header=None, names=ghost_columns)
        
        from building import get_shape 
        selected_brace = get_shape(run.brace[0],'brace')
        d_brace = selected_brace.iloc[0]['b']
        t_brace = selected_brace.iloc[0]['tdes']
        
        A_flange = d_brace*t_brace
        A_web = (d_brace-2*t_brace)*t_brace
        
        total_axial_force_left = (left_brace_res['stress1']*A_flange +
                              left_brace_res['stress2']*A_web +
                              left_brace_res['stress3']*A_web +
                              left_brace_res['stress4']*A_flange)
        
        total_axial_force_right = (right_brace_res['stress1']*A_flange +
                              right_brace_res['stress2']*A_web +
                              right_brace_res['stress3']*A_web +
                              right_brace_res['stress4']*A_flange)
        
        # stress strain
        plt.figure()
        plt.plot(left_brace_res['strain1'], left_brace_res['stress1'])
        plt.title('Axial stress-strain brace (midpoint, top fiber)')
        plt.ylabel('Stress (ksi)')
        plt.xlabel('Strain (in/in)')
        plt.grid(True)
        
        left_brace_force = pd.read_csv(data_dir+'brace_left_force.csv', sep=' ', 
                                     header=None, names=basic_columns)
        
        right_brace_force = pd.read_csv(data_dir+'brace_right_force.csv', sep=' ', 
                                     header=None, names=basic_columns)
        
        # force displacement
        plt.figure()
        plt.plot(left_brace_def['axial_strain'], left_brace_force['iFx'])
        plt.title('Total left brace force (axial basic in top leg)')
        plt.ylabel('Force (kip)')
        plt.xlabel('Axial deformation (in)')
        plt.grid(True)
        
        # force displacement
        plt.figure()
        plt.plot(right_brace_def['axial_strain'], right_brace_force['iFx'])
        plt.title('Total right brace force (axial basic in top leg)')
        plt.ylabel('Force (kip)')
        plt.xlabel('Axial deformation (in)')
        plt.grid(True)
    
    
    # All hystereses
    from bearing import Bearing
    isolator = Bearing(run)
    u_bearing, fs_bearing = isolator.get_backbone()
    
    isol_type = run.isolator_system
    
    col_line = ['column_'+str(col)
                   for col in range(0,num_bays+1)]
    just_cols = col_line.copy()
    col_line.insert(0, 'time')
    
    base_rxn = pd.read_csv(data_dir+'base_rxn.csv', sep=' ', 
                                 header=None, names=col_line)
    
    
    
    if isol_type == 'LRB':
        
        # plt.figure()
        # plt.plot(isol_disp['x'], isol_force['jFy'])
        # plt.plot(u_bearing, fs_bearing, linestyle='--')
        # plt.axvline(run.moat_ampli*run.D_m, linestyle=':', color='red')
        # plt.axvline(-run.moat_ampli*run.D_m, linestyle=':', color='red')
        # plt.title('Single isolator hystereses (LRB)')
        # plt.xlabel('Displ (in)')
        # plt.ylabel('Lateral force (kip)')
        # plt.grid(True)
        
        col_line = ['column_'+str(col)
                       for col in range(0,num_bays+1)]
        just_cols = col_line.copy()
        col_line.insert(0, 'time')
        lrb_disp = pd.read_csv(data_dir+'lrb_disp.csv', sep=' ', 
                                     header=None, names=col_line)
        
        lrb_shear = base_rxn[just_cols].sum(axis=1)
        u_bearing, fs_bearing = isolator.get_backbone(mode='building')
        
        plt.figure()
        plt.plot(lrb_disp['column_0'], -lrb_shear)
        plt.plot(u_bearing, fs_bearing, linestyle='--')
        plt.axvline(run.moat_ampli*run.D_m, linestyle=':', color='red')
        plt.axvline(-run.moat_ampli*run.D_m, linestyle=':', color='red')
        plt.title('Isolator hystereses (whole building) (LRB)')
        plt.xlabel('Displ (in)')
        plt.ylabel('Lateral force (kip)')
        plt.grid(True)
        
    else:
        plt.figure()
        plt.plot(isol_disp['x'], isol_force['jFy']/isol_force['iFx'])
        plt.plot(u_bearing, fs_bearing, linestyle='--')
        plt.axvline(run.moat_ampli*run.D_m, linestyle=':', color='red')
        plt.axvline(-run.moat_ampli*run.D_m, linestyle=':', color='red')
        plt.title('Single isolator hystereses (TFP)')
        plt.xlabel('Displ (in)')
        plt.ylabel('Lateral friction (V/N)')
        plt.grid(True)
        
        col_line = ['column_'+str(col)
                       for col in range(0,num_bays+1)]
        just_cols = col_line.copy()
        col_line.insert(0, 'time')
        tfp_disp = pd.read_csv(data_dir+'tfp_disp.csv', sep=' ', 
                                     header=None, names=col_line)
        
        tfp_base_vert = pd.read_csv(data_dir+'tfp_base_vert.csv', sep=' ', 
                                     header=None, names=col_line)
        
        tfp_shear = base_rxn[just_cols].sum(axis=1)
        tfp_axial = tfp_base_vert[just_cols].sum(axis=1)
        
        u_bearing, fs_bearing = isolator.get_backbone(mode='building')
        
        plt.figure()
        plt.plot(tfp_disp['column_0'], -tfp_shear/tfp_axial)
        plt.plot(u_bearing, fs_bearing, linestyle='--')
        plt.axvline(run.moat_ampli*run.D_m, linestyle=':', color='red')
        plt.axvline(-run.moat_ampli*run.D_m, linestyle=':', color='red')
        plt.title('Isolator hystereses (whole_building) (TFP)')
        plt.xlabel('Displ (in)')
        plt.ylabel('Lateral friction (V/N)')
        plt.grid(True)
        
    # # story level force-displacement
    # diaph_rxn = pd.read_csv(data_dir+'diaph_rxn.csv', sep=' ', 
    #                               header=None, names=col_line)
    
    # story_rxn = pd.read_csv(data_dir+'story_1_rxn.csv', sep=' ', 
    #                              header=None, names=col_line)
    
    # story_1_force = story_rxn[just_cols].sum(axis=1)
    # diaph_force = diaph_rxn[just_cols].sum(axis=1)
    # story_1_shear = story_1_force - diaph_force
    # bldg_disp = (story_disp['story_1'] - story_disp['story_0'])
    # plt.figure()
    # plt.plot(bldg_disp, story_1_shear)
    # plt.title('Story 1 force-displacement')
    # plt.xlabel('Displ (in)')
    # plt.ylabel('Force (kip)')
    # plt.grid(True)
    
        
    wall_columns = ['time', 'left_x', 'left_z', 'right_x', 'right_z']
    impact_forces = pd.read_csv(data_dir+'impact_forces.csv', sep=' ', 
                                 header=None, names=wall_columns)
    
    # wall
    wall_columns = ['time', 'left_x', 'right_x']
    impact_forces = pd.read_csv(data_dir+'impact_forces.csv', sep=' ', 
                                 header=None, names=wall_columns)
    impact_disp = pd.read_csv(data_dir+'impact_disp.csv', sep=' ', 
                                 header=None, names=wall_columns)

    plt.figure()
    plt.plot(impact_disp['left_x'], -impact_forces['left_x'])
    plt.plot(-impact_disp['right_x'], -impact_forces['right_x'])
    plt.title('Impact hysteresis')
    plt.xlabel('Displ (in)')
    plt.ylabel('Force (kip)')
    plt.grid(True)
    
    diaph_columns = ['time', 'iFx', 'iFy', 'iFz', 'iMx', 'iMy', 'iMz']
    diaph_forces = pd.read_csv(data_dir+'diaphragm_forces.csv', sep=' ', 
                                 header=None, names=diaph_columns)
    
    plt.figure()
    plt.plot(diaph_forces['time'], diaph_forces['iFx'])
    plt.title('Diaphragm forces')
    plt.xlabel('Time (s)')
    plt.ylabel('Force (kip)')
    plt.grid(True)
    
    # drift
    # drift ratios recorded. diff takes difference with adjacent column
    ft = 12
    h_story = run.h_story
    story_drift = story_disp.diff(axis=1).drop(
        columns=['time', 'story_0'])/(h_story*ft)
    
    global_drift = (story_disp[story_names[-1]] - story_disp['story_0'])/(run.h_bldg*ft)
    
    # plt.figure()
    # plt.plot(story_disp['time'], story_drift['story_1'])
    # plt.title('Story 1 drift history')
    # plt.xlabel('Time (s)')
    # plt.ylabel('Drift ratio')
    # plt.grid(True)
    
    plt.figure()
    plt.plot(story_disp['time'], global_drift)
    plt.title('Global drift history')
    plt.xlabel('Time (s)')
    plt.ylabel('Drift ratio')
    plt.grid(True)
    
    PID = story_drift.abs().max().tolist()
    PID.insert(0, 0)
    h_up = [fl/num_stories for fl in range(1, num_stories+1)]
    h_up.insert(0, 0)
    
    # # TODO: fix drift profile
    # plt.figure()
    # plt.plot(PID, h_up)
    # plt.title('Drift profile')
    # plt.xlabel('Peak story drift ratio')
    # plt.ylabel('Building height ratio')
    # plt.xlim([0, 5e-2])
    # plt.ylim([0, 1])
    # plt.grid(True)
    
def plot_pushover(run, data_dir='./outputs/pushover/'):
    import pandas as pd
    import matplotlib.pyplot as plt
    
    plt.close('all')
    
    # gather EDPs from opensees output
    # also collecting story 0, which is isol layer
    num_stories = run.num_stories
    num_bays = run.num_bays
    story_names = ['story_'+str(story)
                   for story in range(0,num_stories+1)]
    story_names.insert(0, 'time')
    
    rxn_cols = ['bay_'+str(bay)
                 for bay in range(0, num_bays+1)]
    rxn_cols.insert(len(rxn_cols), 'left_wall')
    rxn_cols.insert(len(rxn_cols), 'right_wall')
    
    bay_names = rxn_cols.copy()
    rxn_cols.insert(0, 'time')
    
    ground_reactions = pd.read_csv(data_dir+'ground_rxn.csv', sep=' ', 
                           header=None, names=rxn_cols)
    
    # drift
    story_disp = pd.read_csv(data_dir+'outer_col_disp.csv', sep=' ', 
                                 header=None, names=story_names)
    
    # drift ratios recorded. diff takes difference with adjacent column
    ft = 12
    h_story = run.h_story
    h_bldg = h_story*num_stories
    story_drift = story_disp.diff(axis=1).drop(
        columns=['time', 'story_0'])/(h_story*ft)
    
    base_shear = -ground_reactions[bay_names].sum(axis=1)
    
    # isolators
    isol_columns = ['time', 'x', 'z', 'rot']
    isol_disp = pd.read_csv(data_dir+'isolator_displacement.csv', sep=' ', 
                                 header=None, names=isol_columns)
    
    force_columns = ['time', 'iFx', 'iFy', 'iFz', 'iMx', 'iMy', 'iMz', 
                    'jFx', 'jFy', 'jFz', 'jMx', 'jMy', 'jMz']
    isol_force = pd.read_csv(data_dir+'isolator_forces.csv', sep=' ', 
                                 header=None, names=force_columns)
    
    # All hystereses
    isol_type = run.isolator_system
    if isol_type == 'LRB':
        plt.figure()
        plt.plot(isol_disp['x'], isol_force['jFy'])
        plt.title('Isolator hystereses (LRB)')
        plt.xlabel('Displ (in)')
        plt.ylabel('V/N')
        plt.grid(True)
    else:
        plt.figure()
        plt.plot(isol_disp['x'], isol_force['jFy']/isol_force['iFx'])
        plt.title('Isolator hystereses (TFP)')
        plt.xlabel('Displ (in)')
        plt.ylabel('V/N')
        plt.grid(True)
    
    # base shear vs roof
    plt.figure()
    plt.plot(story_disp[story_names[-1]], base_shear)
    plt.title('Pushover curve (roof)')
    plt.xlabel('Roof displacement (in)')
    plt.ylabel('Base shear')
    plt.grid(True)
    plt.show()
    
    # base shear vs roof
    bldg_drift = (story_disp[story_names[-1]]-
                  story_disp[story_names[1]])/(h_bldg*12)
    plt.figure()
    plt.plot(bldg_drift, base_shear)
    plt.title('Pushover curve (superstructure only)')
    plt.xlabel('Building drift (roof - isolation)')
    plt.ylabel('Base shear')
    plt.grid(True)
    plt.show()
    
    # story drifts
    plt.figure()
    for story_name in story_drift.columns.tolist():
        plt.plot(story_drift[story_name], base_shear)
    plt.title('Drift pushover (ground reaction)')
    plt.ylabel('Base shear (ground rxn)')
    plt.xlabel('Drift ratio')
    plt.grid(True)
    plt.show()
    
def animate_gm(run, data_dir='./outputs/'):
    
    # run = troubleshoot_run
    # data_dir = './outputs/'
    import pandas as pd
    import matplotlib.pyplot as plt
    
    # plt.close('all')
    num_stories = run.num_stories
    
    # gather EDPs from opensees output
    # also collecting story 0, which is isol layer
    story_names = ['story_'+str(story)
                   for story in range(0,num_stories+1)]
    just_stories = story_names.copy()
    story_names.insert(0, 'time')
    
    # drift
    story_disp = pd.read_csv(data_dir+'inner_col_disp.csv', sep=' ', 
                                 header=None, names=story_names)
    story_vert = pd.read_csv(data_dir+'inner_col_vert.csv', sep=' ', 
                                 header=None, names=story_names)
    
    n = len(story_disp)
    
    h_story = run.h_story
    h_up = [fl * h_story * 12 + 12 for fl in range(0,num_stories+1)]
    
    # dt = 0.005
    fig = plt.figure()
    ax = fig.add_subplot(autoscale_on=True, xlim=(-50, 50),
                         ylim=(0, h_story*num_stories*12+50))
    time_text = ax.text(0.05, 0.9, '', transform=ax.transAxes)
    time_template = 'time = %.1fs'
    line, = ax.plot([], [], 'o-', lw=2)
    trace, = ax.plot([], [], '.-', lw=1, ms=2)

    def animate(i):
        storyx = [story_disp[label][i] for label in just_stories]
        storyz_disp = [story_vert[label][i] for label in just_stories]
        storyz = [a + b for a, b in zip(storyz_disp, h_up)]
        
        storyx.insert(0, 0)
        storyz.insert(0, 0)
        line.set_data(storyx, storyz)
        
        time_text.set_text(time_template % (story_disp['time'][i]))
        return line, trace, time_text
    
    return(fig, animate, n)

    # animation.FuncAnimation(fig, animate, n, interval=1/40, blit=True)
    # plt.show()
    # ani.save(filename="../outputs/gm_animation.mp4", writer="ffmpeg")
    
    
    