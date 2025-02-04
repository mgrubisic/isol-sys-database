############################################################################
#               Figure generation (plotting, ML, inverse design)

# Created by:   Huy Pham
#               University of California, Berkeley

# Date created: April 2024

# Description:  Main file which imports the structural database and starts the
# loss estimation

# Open issues:  (1) 

############################################################################
import sys
# caution: path[0] is reserved for script path (or '' in REPL)
sys.path.insert(1, '../')

import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from doe import GP

plt.close('all')

main_obj = pd.read_pickle("../../data/loss/tfp_mf_db_doe_loss_max.pickle")

# with open("../../data/tfp_mf_db.pickle", 'rb') as picklefile:
#     main_obj = pickle.load(picklefile)
    
main_obj.calculate_collapse()

df_raw = main_obj.doe_analysis
df_raw = df_raw.reset_index(drop=True)

# remove the singular outlier point
from scipy import stats
df = df_raw[np.abs(stats.zscore(df_raw['collapse_prob'])) < 10].copy()

df = df.drop(columns=['index'])
# df = df_whole.head(100).copy()

df['max_drift'] = df.PID.apply(max)
df['log_drift'] = np.log(df['max_drift'])

df['max_velo'] = df.PFV.apply(max)
df['max_accel'] = df.PFA.apply(max)

df['T_ratio'] = df['T_m'] / df['T_fb']
df['T_ratio_e'] = df['T_m'] / df['T_fbe']
pi = 3.14159
g = 386.4

zetaRef = [0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
BmRef   = [0.8, 1.0, 1.2, 1.5, 1.7, 1.9, 2.0]
df['Bm'] = np.interp(df['zeta_e'], zetaRef, BmRef)

df['gap_ratio'] = (df['constructed_moat']*4*pi**2)/ \
    (g*(df['sa_tm']/df['Bm'])*df['T_m']**2)

df_loss = main_obj.loss_data
df_loss_max = main_obj.max_loss
#%%
# make a generalized 2D plotting grid, defaulted to gap and Ry
# grid is based on the bounds of input data
def make_2D_plotting_space(X, res, x_var='gap_ratio', y_var='RI', 
                           all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                           third_var_set = None, fourth_var_set = None,
                           x_bounds=None, y_bounds=None):
    
    if x_bounds == None:
        x_min = min(X[x_var])
        x_max = max(X[x_var])
    else:
        x_min = x_bounds[0]
        x_max = x_bounds[1]
    if y_bounds == None:
        y_min = min(X[y_var])
        y_max = max(X[y_var])
    else:
        y_min = y_bounds[0]
        y_max = y_bounds[1]
    xx, yy = np.meshgrid(np.linspace(x_min,
                                     x_max,
                                     res),
                         np.linspace(y_min,
                                     y_max,
                                     res))

    rem_vars = [i for i in all_vars if i not in [x_var, y_var]]
    third_var = rem_vars[0]
    fourth_var = rem_vars[-1]
       
    xx = xx
    yy = yy
    
    if third_var_set is None:
        third_var_val= X[third_var].median()
    else:
        third_var_val = third_var_set
    if fourth_var_set is None:
        fourth_var_val = X[fourth_var].median()
    else:
        fourth_var_val = fourth_var_set
    
    
    X_pl = pd.DataFrame({x_var:xx.ravel(),
                         y_var:yy.ravel(),
                         third_var:np.repeat(third_var_val,
                                             res*res),
                         fourth_var:np.repeat(fourth_var_val, 
                                              res*res)})
    X_plot = X_pl[all_vars]
                         
    return(X_plot)

# hard-coded
def make_design_space(res):
    xx, yy, uu, vv = np.meshgrid(np.linspace(0.6, 1.5,
                                             res),
                                 np.linspace(0.5, 2.25,
                                             res),
                                 np.linspace(2.0, 4.0,
                                             res),
                                 np.linspace(0.1, 0.25,
                                             res))
                                 
    X_space = pd.DataFrame({'gap_ratio':xx.ravel(),
                         'RI':yy.ravel(),
                         'T_ratio':uu.ravel(),
                         'zeta_e':vv.ravel()})

    return(X_space)

###############################################################################
    # Full prediction models
###############################################################################

# two ways of doing this
        
        # 1) predict impact first (binary), then fit the impact predictions 
        # with the impact-only SVR and likewise with non-impacts. This creates
        # two tiers of predictions that are relatively flat (impact dominated)
        # 2) using expectations, get probabilities of collapse and weigh the
        # two (cost|impact) regressions with Pr(impact). Creates smooth
        # predictions that are somewhat moderate
        
def predict_DV(X, impact_pred_mdl, hit_loss_mdl, miss_loss_mdl,
               outcome='cost_50%'):
        
#        # get points that are predicted impact from full dataset
#        preds_imp = impact_pred_mdl.svc.predict(self.X)
#        df_imp = self.X[preds_imp == 1]

    # get probability of impact
    if 'log_reg_kernel' in impact_pred_mdl.named_steps.keys():
        probs_imp = impact_pred_mdl.predict_proba(impact_pred_mdl.K_pr)
    else:
        probs_imp = impact_pred_mdl.predict_proba(X)

    miss_prob = probs_imp[:,0]
    hit_prob = probs_imp[:,1]
    
    # weight with probability of collapse
    # E[Loss] = (impact loss)*Pr(impact) + (no impact loss)*Pr(no impact)
    # run SVR_hit model on this dataset
    outcome_str = outcome+'_pred'
    expected_DV_hit = pd.DataFrame(
            {outcome_str:np.multiply(
                    hit_loss_mdl.predict(X).ravel(),
                    hit_prob)})
            
#        # get points that are predicted no impact from full dataset
#        df_mss = self.X[preds_imp == 0]
    
    # run miss model on this dataset
    expected_DV_miss = pd.DataFrame(
            {outcome_str:np.multiply(
                    miss_loss_mdl.predict(X).ravel(),
                    miss_prob)})
    
    expected_DV = expected_DV_hit + expected_DV_miss
    
    # self.median_loss_pred = pd.concat([loss_pred_hit,loss_pred_miss], 
    #                                   axis=0).sort_index(ascending=True)
    
    return(expected_DV)
#%% collapse fragility def

plt.rcParams["text.usetex"] = True
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"

# collapse as a probability
from scipy.stats import lognorm
from math import log, exp

collapse_drift_def_mu_std = 0.1


from scipy.stats import norm
inv_norm = norm.ppf(0.84)
beta_drift = 0.25
mean_log_drift = exp(log(collapse_drift_def_mu_std) - beta_drift*inv_norm) # 0.9945 is inverse normCDF of 0.84
# mean_log_drift = 0.05
ln_dist = lognorm(s=beta_drift, scale=mean_log_drift)

label_size = 16
clabel_size = 12
x = np.linspace(0, 0.15, 200)

mu = log(mean_log_drift)

ln_dist = lognorm(s=beta_drift, scale=mean_log_drift)
p = ln_dist.cdf(np.array(x))


fig, ax = plt.subplots(1, 1, figsize=(8,6))

ax.plot(x, p, label='Collapse (peak)', color='blue')

mu_irr = log(0.01)
ln_dist_irr = lognorm(s=0.3, scale=exp(mu_irr))
p_irr = ln_dist_irr.cdf(np.array(x))

# ax.plot(x, p_irr, color='red', label='Irreparable (residual)')

axis_font = 20
subt_font = 18
xright = 0.0
xleft = 0.15
ax.set_ylim([0,1])
ax.set_xlim([0, xleft])
ax.set_ylabel('Collapse probability', fontsize=axis_font)
ax.set_xlabel('Peak drift ratio', fontsize=axis_font)

ax.vlines(x=exp(mu), ymin=0, ymax=0.5, color='blue', linestyle=":")
ax.hlines(y=0.5, xmin=xright, xmax=exp(mu), color='blue', linestyle=":")
ax.text(0.01, 0.52, r'$\theta = %.3f$'% mean_log_drift , fontsize=axis_font, color='blue')
ax.plot([exp(mu)], [0.5], marker='*', markersize=15, color="blue", linestyle=":")

upper = ln_dist.ppf(0.84)
ax.vlines(x=upper, ymin=0, ymax=0.84, color='blue', linestyle=":")
ax.hlines(y=0.84, xmin=xright, xmax=upper, color='blue', linestyle=":")
ax.text(0.01, 0.87, r'$\theta = %.3f$' % upper, fontsize=axis_font, color='blue')
ax.plot([upper], [0.84], marker='*', markersize=15, color="blue", linestyle=":")

lower= ln_dist.ppf(0.16)
ax.vlines(x=lower, ymin=0, ymax=0.16, color='blue', linestyle=":")
ax.hlines(y=0.16, xmin=xright, xmax=lower, color='blue', linestyle=":")
ax.text(0.01, 0.19, r'$\theta = %.3f$' % lower, fontsize=axis_font, color='blue')
ax.plot([lower], [0.16], marker='*', markersize=15, color="blue", linestyle=":")


# ax.set_title('Replacement fragility definition', fontsize=axis_font)
ax.grid()
# ax.legend(fontsize=label_size, loc='upper center')
# plt.show()
# plt.savefig('./figures/collapse_def.eps')

#%% collapse fragility def
import numpy as np
from scipy.stats import norm
inv_norm = norm.ppf(0.84)
x = np.linspace(0, 0.15, 200)
mu = log(0.1)- 0.25*inv_norm
sigma = 0.25;

ln_dist = lognorm(s=sigma, scale=exp(mu))
p = ln_dist.cdf(np.array(x))

# plt.close('all')
fig, ax = plt.subplots(1, 1, figsize=(8,6))

ax.plot(x, p, label='Collapse', color='blue')

mu_irr = log(0.01)
ln_dist_irr = lognorm(s=0.3, scale=exp(mu_irr))
p_irr = ln_dist_irr.cdf(np.array(x))

ax.plot(x, p_irr, color='red', label='Irreparable')

axis_font = 20
subt_font = 18
xleft = 0.15
ax.set_ylim([0,1])
ax.set_xlim([0, xleft])
ax.set_ylabel('Limit state probability', fontsize=axis_font)
ax.set_xlabel('Drift ratio', fontsize=axis_font)

ax.vlines(x=exp(mu), ymin=0, ymax=0.5, color='blue', linestyle=":")
ax.hlines(y=0.5, xmin=exp(mu), xmax=0.15, color='blue', linestyle=":")
ax.text(0.105, 0.52, r'PID = 0.078', fontsize=axis_font, color='blue')
ax.plot([exp(mu)], [0.5], marker='*', markersize=15, color="blue", linestyle=":")

ax.vlines(x=0.1, ymin=0, ymax=0.84, color='blue', linestyle=":")
ax.hlines(y=0.84, xmin=0.1, xmax=xleft, color='blue', linestyle=":")
ax.text(0.105, 0.87, r'PID = 0.10', fontsize=axis_font, color='blue')
ax.plot([0.10], [0.84], marker='*', markersize=15, color="blue", linestyle=":")

lower= ln_dist.ppf(0.16)
ax.vlines(x=lower, ymin=0, ymax=0.16, color='blue', linestyle=":")
ax.hlines(y=0.16, xmin=lower, xmax=xleft, color='blue', linestyle=":")
ax.text(0.105, 0.19, r'PID = 0.061', fontsize=axis_font, color='blue')
ax.plot([lower], [0.16], marker='*', markersize=15, color="blue", linestyle=":")


ax.hlines(y=0.5, xmin=0.0, xmax=exp(mu_irr), color='red', linestyle=":")
lower = ln_dist_irr.ppf(0.16)
ax.hlines(y=0.16, xmin=0.0, xmax=lower, color='red', linestyle=":")
upper = ln_dist_irr.ppf(0.84)
ax.hlines(y=0.84, xmin=0.0, xmax=upper, color='red', linestyle=":")
ax.plot([lower], [0.16], marker='*', markersize=15, color="red", linestyle=":")
ax.plot([0.01], [0.5], marker='*', markersize=15, color="red", linestyle=":")
ax.plot([upper], [0.84], marker='*', markersize=15, color="red", linestyle=":")
ax.vlines(x=upper, ymin=0, ymax=0.84, color='red', linestyle=":")
ax.vlines(x=0.01, ymin=0, ymax=0.5, color='red', linestyle=":")
ax.vlines(x=lower, ymin=0, ymax=0.16, color='red', linestyle=":")

ax.text(0.005, 0.19, r'RID = 0.007', fontsize=axis_font, color='red')
ax.text(0.005, 0.87, r'RID = 0.013', fontsize=axis_font, color='red')
ax.text(0.005, 0.53, r'RID = 0.010', fontsize=axis_font, color='red')

ax.set_title('Replacement fragility definition', fontsize=axis_font)
ax.grid()
ax.legend(fontsize=label_size, loc='upper center')
plt.show()
#%% normalize DVs and prepare all variables
df['bldg_area'] = df['L_bldg']**2 * (df['num_stories'] + 1)

df['replacement_cost'] = 600.0*(df['bldg_area'])
df['total_cmp_cost'] = df_loss_max['cost_50%']
df['cmp_replace_cost_ratio'] = df['total_cmp_cost']/df['replacement_cost']
df['median_cost_ratio'] = df_loss['cost_50%']/df['replacement_cost']
df['cmp_cost_ratio'] = df_loss['cost_50%']/df['total_cmp_cost']

df['replacement_time'] = df['bldg_area']/1000*365
df['total_cmp_time'] = df_loss_max['time_l_50%']
df['cmp_replace_time_ratio'] = df['total_cmp_time']/df['replacement_time']
df['median_time_ratio'] = df_loss['time_l_50%']/df['replacement_time']
df['cmp_time_ratio'] = df_loss['time_l_50%']/df['total_cmp_time']

df['replacement_freq'] = df_loss['replacement_freq']

df[['B_50%', 'C_50%', 'D_50%', 'E_50%']] = df_loss[['B_50%', 'C_50%', 'D_50%', 'E_50%']]

df['impacted'] = pd.to_numeric(df['impacted'])

cost_var = 'median_cost_ratio'
time_var = 'median_time_ratio'
covariate_list = ['gap_ratio', 'RI', 'T_ratio', 'zeta_e']
#%% ml training

# make prediction objects for impacted and non-impacted datasets
df_hit = df[df['impacted'] == 1]
mdl_cost_hit = GP(df_hit)
mdl_cost_hit.set_covariates(covariate_list)
mdl_cost_hit.set_outcome(cost_var)
mdl_cost_hit.test_train_split(0.2)

df_miss = df[df['impacted'] == 0]
mdl_cost_miss = GP(df_miss)
mdl_cost_miss.set_covariates(covariate_list)
mdl_cost_miss.set_outcome(cost_var)
mdl_cost_miss.test_train_split(0.2)

mdl_time_hit = GP(df_hit)
mdl_time_hit.set_covariates(covariate_list)
mdl_time_hit.set_outcome(time_var)
mdl_time_hit.test_train_split(0.2)

mdl_time_miss = GP(df_miss)
mdl_time_miss.set_covariates(covariate_list)
mdl_time_miss.set_outcome(time_var)
mdl_time_miss.test_train_split(0.2)

mdl_repl_hit = GP(df_hit)
mdl_repl_hit.set_covariates(covariate_list)
mdl_repl_hit.set_outcome('replacement_freq')
mdl_repl_hit.test_train_split(0.2)

mdl_repl_miss = GP(df_miss)
mdl_repl_miss.set_covariates(covariate_list)
mdl_repl_miss.set_outcome('replacement_freq')
mdl_repl_miss.test_train_split(0.2)

mdl_unconditioned = GP(df)
mdl_unconditioned.set_covariates(covariate_list)
mdl_unconditioned.set_outcome(cost_var)
mdl_unconditioned.test_train_split(0.2)

#%%  dumb scatters

# plt.close('all')
plt.rcParams["text.usetex"] = True
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 22
subt_font = 18
label_size = 20
title_font = 24

mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 

y_var = 'median_cost_ratio'
fig = plt.figure(figsize=(13, 10))

ax1=fig.add_subplot(2, 2, 1)

cmap = plt.cm.coolwarm
sc = ax1.scatter(df['gap_ratio'], df[y_var], alpha=0.2, c=df['impacted'], cmap=cmap)
ax1.set_ylabel('Median loss ratio', fontsize=axis_font)
ax1.set_xlabel(r'$GR$', fontsize=axis_font)
ax1.set_title('a) Gap ratio', fontsize=title_font)
ax1.set_ylim([0, 0.3])

from matplotlib.lines import Line2D
custom_lines = [Line2D([0], [0], marker='o', color='w', label='No impact',
                          markerfacecolor=cmap(0.), alpha=0.4, markersize=15),
                Line2D([0], [0], marker='o', color='w', label='Wall impact',
                       markerfacecolor=cmap(1.), alpha=0.4, markersize=15)]
ax1.legend(custom_lines, ['No impact', 'Impact'], fontsize=subt_font)
ax1.grid(True)

ax2=fig.add_subplot(2, 2, 2)

ax2.scatter(df['RI'], df[y_var], alpha=0.3, c=df['impacted'], cmap=cmap)
ax2.set_xlabel(r'$R_y$', fontsize=axis_font)
ax2.set_title('b) Superstructure strength', fontsize=title_font)
ax2.set_ylim([0, 0.3])
ax2.grid(True)

ax3=fig.add_subplot(2, 2, 3)

ax3.scatter(df['T_ratio'], df[y_var], alpha=0.3, c=df['impacted'], cmap=cmap)
# ax3.scatter(df['T_ratio_e'], df[y_var])
ax3.set_ylabel('Median loss ratio', fontsize=axis_font)
ax3.set_xlabel(r'$T_M/T_{fb}$', fontsize=axis_font)
ax3.set_title('c) Bearing period ratio', fontsize=title_font)
ax3.set_ylim([0, 0.3])
ax3.grid(True)

ax4=fig.add_subplot(2, 2, 4)

ax4.scatter(df['zeta_e'], df[y_var], alpha=0.3, c=df['impacted'], cmap=cmap)
ax4.set_xlabel(r'$\zeta_M$', fontsize=axis_font)
ax4.set_title('d) Bearing damping', fontsize=title_font)
ax4.set_ylim([0, 0.3])
ax4.grid(True)

fig.tight_layout()
plt.show()

#%% weird pie plot
def plot_pie(x, ax, r=1): 
    # radius for pieplot size on a scatterplot
    patches, texts = ax.pie(x[['B_50%','C_50%','D_50%','E_50%']], 
           center=(x['gap_ratio'],x['RI']), radius=r, colors=plt.cm.Set2.colors)
    
    return(patches)

    
fig, ax = plt.subplots(1, 1, figsize=(8, 8))


df_mini = df[df['B_50%'].notnull()].head(200)
df_mini = df_mini[df_mini['gap_ratio'] < 2.5]
df_mini = df_mini[df_mini['gap_ratio'] >0.5]
df_pie = df_mini.copy()

ax.scatter(x=df_pie['gap_ratio'], y=df_pie['RI'], s=0)
# git min/max values for the axes
# y_init = ax.get_ylim()
# x_init = ax.get_xlim()
df_pie.apply(lambda x : plot_pie(x, ax, r=0.04), axis=1)
patch = plot_pie(df_pie.iloc[-1], ax, r=0.04)

ax.set_xlabel(r'Gap ratio', fontsize=axis_font)
ax.set_ylabel(r'$R_y$', fontsize=axis_font)
ax.set_title(r'Repair cost makeup by component', fontsize=title_font)
ax.set_xlim([0.4, 2.5])
ax.set_ylim([0.5, 2.25])
_ = ax.yaxis.set_ticks(np.arange(0.5, 2.1, 0.5))
_ = ax.xaxis.set_ticks(np.arange(0.5, 2.1, 0.5))
# _ = ax.set_title('My')
ax.set_frame_on(True)
labels = ['Structure \& facade', 'Partitions \& lighting', 'MEP', 'Storage']
plt.legend(patch, labels, loc='lower right', fontsize=14)
# plt.axis('equal')
# plt.tight_layout()
ax.grid()


#%% impact effect
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 
warnings.filterwarnings("ignore", category=FutureWarning) 

plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 18
subt_font = 18
label_size = 16
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 

#plt.close('all')
import seaborn as sns

# make grid and plot classification predictions

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(13, 4))
sns.boxplot(y=cost_var, x= "impacted", data=df,  showfliers=False,
            boxprops={'facecolor': 'none'},
            width=0.6, ax=ax1)
sns.stripplot(x='impacted', y=cost_var, data=df, ax=ax1, jitter=True,
              alpha=0.3, color='steelblue')
ax1.set_title('Median repair cost', fontsize=subt_font)
ax1.set_ylabel('Repair cost ratio', fontsize=axis_font)
ax1.set_xlabel('Impact', fontsize=axis_font)
ax1.set_yscale('log')

sns.boxplot(y=time_var, x= "impacted", data=df,  showfliers=False,
            boxprops={'facecolor': 'none'},
            width=0.6, ax=ax2)
sns.stripplot(x='impacted', y=time_var, data=df, ax=ax2, jitter=True,
              alpha=0.3, color='steelblue')
ax2.set_title('Median sequential repair time', fontsize=subt_font)
ax2.set_ylabel('Repair time ratio', fontsize=axis_font)
ax2.set_xlabel('Impact', fontsize=axis_font)
ax2.set_yscale('log')

sns.boxplot(y="replacement_freq", x= "impacted", data=df,  showfliers=False,
            boxprops={'facecolor': 'none'},
            width=0.5, ax=ax3)
sns.stripplot(x='impacted', y='replacement_freq', data=df, ax=ax3, jitter=True,
              alpha=0.3, color='steelblue')
ax3.set_title('Replacement frequency', fontsize=subt_font)
ax3.set_ylabel('Replacement frequency', fontsize=axis_font)
ax3.set_xlabel('Impact', fontsize=axis_font)
# ax3.set_yscale('log')
fig.tight_layout()
plt.show()

#%% impact prediction

print('========== Fitting impact classification (GPC) ============')

# prepare the problem
mdl_impact = GP(df)
mdl_impact.set_covariates(covariate_list)
mdl_impact.set_outcome('impacted', use_ravel=True)
mdl_impact.test_train_split(0.2)

mdl_impact.fit_gpc(kernel_name='rbf_iso')

mdl_impact.fit_kernel_logistic(kernel_name='rbf')

# predict the entire dataset
preds_imp = mdl_impact.gpc.predict(mdl_impact.X)
probs_imp = mdl_impact.gpc.predict_proba(mdl_impact.X)

# we've done manual CV to pick the hyperparams that trades some accuracy
# in order to lower false negatives
from sklearn.metrics import confusion_matrix

tn, fp, fn, tp = confusion_matrix(mdl_impact.y, preds_imp).ravel()
print('False negatives: ', fn)
print('False positives: ', fp)

#%% Classification plot

plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 22
title_font = 22
subt_font = 18
import matplotlib as mpl
label_size = 18
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 

# plt.close('all')
# make grid and plot classification predictions

fig, ax = plt.subplots(1, 1, figsize=(9,7))

xvar = 'gap_ratio'
yvar = 'T_ratio'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 2.0, fourth_var_set = 0.15)
xx = X_plot[xvar]
yy = X_plot[yvar]

# # GPC impact prediction
# Z = mdl_impact.gpc.predict_proba(X_plot)[:,1]


# kernel logistic impact prediction
K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)
probs_imp = mdl_impact.log_reg_kernel.predict_proba(K_space)
Z = probs_imp[:,1]

x_pl = np.unique(xx)
y_pl = np.unique(yy)

# collapse predictions
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_classif = Z.reshape(xx_pl.shape)

# ax1.imshow(
#         Z,
#         interpolation="nearest",
#         extent=(xx.min(), xx.max(),
#                 yy.min(), yy.max()),
#         aspect="auto",
#         origin="lower",
#         cmap=plt.cm.Greys,
#     )

plt.imshow(
        Z_classif,
        interpolation="nearest",
        extent=(xx.min(), xx.max(),
                yy.min(), yy.max()),
        aspect="auto",
        origin="lower",
        cmap=plt.cm.Blues,
    )
plt_density = 200
cs = plt.contour(xx_pl, yy_pl, Z_classif, linewidths=1.1, cmap='Blues', vmin=-1,
                  levels=np.linspace(0.1,1.0,num=10))
plt.clabel(cs, fontsize=clabel_size)

ax.scatter(df_hit[xvar][:plt_density],
            df_hit[yvar][:plt_density],
            s=40, c='darkblue', marker='v', edgecolors='crimson', label='Impacted')

ax.scatter(df_miss[xvar][:plt_density],
            df_miss[yvar][:plt_density],
            s=40, c='azure', edgecolors='k', label='No impact')


ax.set_xlim(0.3, 2.5)
ax.set_title(r'Impact likelihood: $R_y = 2.0$, $\zeta_M = 0.15$', fontsize=title_font)
ax.set_xlabel(r'$GR$', fontsize=axis_font)
ax.set_ylabel(r'$T_M/T_{fb}$', fontsize=axis_font)

fig.tight_layout()
plt.show()


#%% fit regressions for impact / non-impact set

# Fit conditioned DVs using kernel ridge

print('========== Fitting regressions (kernel ridge) ============')

# fit impacted set
mdl_cost_hit.fit_kernel_ridge(kernel_name='rbf')
mdl_time_hit.fit_kernel_ridge(kernel_name='rbf')

# fit no impact set
mdl_cost_miss.fit_kernel_ridge(kernel_name='rbf')
mdl_time_miss.fit_kernel_ridge(kernel_name='rbf')


mdl_repl_hit.fit_kernel_ridge(kernel_name='rbf')
mdl_repl_miss.fit_kernel_ridge(kernel_name='rbf')


print('========== Fitting regressions (GPR) ============')

# Fit conditioned DVs using GPR

# fit impacted set
mdl_cost_hit.fit_gpr(kernel_name='rbf_iso')
mdl_time_hit.fit_gpr(kernel_name='rbf_iso')

# fit no impact set
mdl_cost_miss.fit_gpr(kernel_name='rbf_iso')
mdl_time_miss.fit_gpr(kernel_name='rbf_iso')


mdl_repl_hit.fit_gpr(kernel_name='rbf_iso')
mdl_repl_miss.fit_gpr(kernel_name='rbf_iso')

mdl_unconditioned.fit_gpr(kernel_name='rbf_iso')

print('========== Fitting ordinary ridge (OR) ============')

# Fit conditioned DVs using GPR

# fit impacted set
mdl_cost_hit.fit_ols_ridge()
mdl_time_hit.fit_ols_ridge()

# fit no impact set
mdl_cost_miss.fit_ols_ridge()
mdl_time_miss.fit_ols_ridge()


mdl_repl_hit.fit_ols_ridge()
mdl_repl_miss.fit_ols_ridge()

mdl_unconditioned.fit_gpr(kernel_name='rbf_iso')
#%% plot no-impact regressions
axis_font = 20
subt_font = 18

xvar = 'T_ratio'
yvar = 'zeta_e'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 1.0, fourth_var_set = 2.0)
xx = X_plot[xvar]
yy = X_plot[yvar]
Z = mdl_cost_miss.gpr.predict(X_plot)


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_regr = Z.reshape(xx_pl.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# Plot the surface.
surf = ax.plot_surface(xx_pl, yy_pl, Z_regr, cmap=plt.cm.coolwarm,
                       linewidth=0, antialiased=False,
                       alpha=0.5)

ax.scatter(df_miss[xvar], df_miss[yvar], df_miss[cost_var],
           c=df_miss[cost_var], alpha=0.3,
           edgecolors='k')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_regr, zdir='z', offset=-1e5, cmap='coolwarm')
cset = ax.contour(xx_pl, yy_pl, Z_regr, zdir='x', offset=xlim[0], cmap='coolwarm_r')
cset = ax.contour(xx_pl, yy_pl, Z_regr, zdir='y', offset=ylim[1], cmap='coolwarm')

ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.set_zlim([0, 0.2])
ax.set_xlabel('$T_M/ T_{fb}$', fontsize=axis_font)
ax.set_ylabel('$\zeta_M$', fontsize=axis_font)
# ax.set_zlabel('Median loss ($)', fontsize=axis_font)
# ax.set_title('Median cost predictions given no impact (RBF kernel ridge)')
fig.tight_layout()
plt.show()

#%% plot yes-impact regressions
axis_font = 20
subt_font = 18

xvar = 'T_ratio'
yvar = 'zeta_e'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 1.0, fourth_var_set = 2.0)
xx = X_plot[xvar]
yy = X_plot[yvar]
Z = mdl_cost_hit.kr.predict(X_plot)


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_regr = Z.reshape(xx_pl.shape)

fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
# Plot the surface.
surf = ax.plot_surface(xx_pl, yy_pl, Z_regr, cmap=plt.cm.coolwarm,
                       linewidth=0, antialiased=False,
                       alpha=0.5)

ax.scatter(df_hit[xvar], df_hit[yvar], df_hit[cost_var],
           c=df_hit[cost_var], alpha=0.3,
           edgecolors='k')

ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_regr, zdir='z', offset=-1e5, cmap='coolwarm')
cset = ax.contour(xx_pl, yy_pl, Z_regr, zdir='x', offset=xlim[0], cmap='coolwarm_r')
cset = ax.contour(xx_pl, yy_pl, Z_regr, zdir='y', offset=ylim[1], cmap='coolwarm')

ax.set_xlabel('$T_M/ T_{fb}$', fontsize=axis_font)
ax.set_ylabel('$\zeta_M$', fontsize=axis_font)
# ax.set_zlabel('Median loss ($)', fontsize=axis_font)
# ax.set_title('Median cost predictions given no impact (RBF kernel ridge)')
fig.tight_layout()
plt.show()

#%% unconditioned models

plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 18
subt_font = 18
label_size = 12
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 
# plt.close('all')

fig = plt.figure(figsize=(16, 7))

#################################
xvar = 'RI'
yvar = 'gap_ratio'

res = 75
X_plot = make_2D_plotting_space(mdl_unconditioned.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 3.0, fourth_var_set = 0.15)
xx = X_plot[xvar]
yy = X_plot[yvar]

x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)


Z = mdl_unconditioned.gpr.predict(X_plot)
Z_unconditioned = Z.reshape(xx_pl.shape)

ax=fig.add_subplot(1, 3, 1)
cs = ax.contour(xx_pl, Z_unconditioned, yy_pl, linewidths=1.1, cmap='coolwarm',
                 levels=np.arange(0.5, 3.0, step=0.25))
ax.scatter(df[xvar], df[cost_var], color='steelblue', alpha=0.5,
          edgecolors='k')
ax.clabel(cs, fontsize=label_size)
ax.set_xlabel(r'$R_y$', fontsize=axis_font)
ax.grid(visible=True)
ax.plot(0.65, 0.01, color='red', label=r'$GR$')
ax.legend(fontsize=axis_font, loc='center left')
ax.set_ylabel('Median loss ratio', fontsize=axis_font)
# ax.set_ylim([0.1, 0.5])
# ax.set_xlim([0.3, 2.5])
plt.show()

#################################
# show dichotomy of data


ax=fig.add_subplot(1, 3, 2)

cmap = plt.cm.coolwarm
sc = ax.scatter(df[xvar], df[cost_var], alpha=0.4, c=df['impacted'], 
                edgecolors='k', cmap=cmap)
ax.set_xlabel(r'$R_y$', fontsize=axis_font)
# ax.set_title('a) Gap ratio', fontsize=title_font)
# ax.set_xlim([0.3, 2.5])
from matplotlib.lines import Line2D
custom_lines = [Line2D([0], [0], marker='o', color='w', label='No impact',
                          markerfacecolor=cmap(0.), alpha=0.4, markersize=15),
                Line2D([0], [0], marker='o', color='w', label='Wall impact',
                       markerfacecolor=cmap(1.), alpha=0.4, markersize=15)]
ax.legend(custom_lines, ['No impact', 'Impact'], fontsize=subt_font)
ax.grid(True)

#################################
# plot conditioned fits
cmap=plt.cm.coolwarm
ax=fig.add_subplot(2, 3, 3)

Z = mdl_cost_hit.gpr.predict(X_plot)
Z_hit_cond = Z.reshape(xx_pl.shape)

cs = ax.contour(xx_pl, Z_hit_cond, yy_pl, linewidths=1.1, cmap='coolwarm',
                 levels=np.arange(0.5, 3.0, step=0.25))
ax.scatter(df_hit[xvar], df_hit[cost_var], color=cmap(1.), alpha=0.5,
          edgecolors='k')
ax.clabel(cs, fontsize=label_size)
ax.set_xlabel(r'$R_y$', fontsize=axis_font)
ax.grid(visible=True)
# ax.set_ylim([0.1, 0.5])
# ax.set_xlim([0.3, 2.5])
plt.show()


ax=fig.add_subplot(2, 3, 6)

Z = mdl_cost_miss.gpr.predict(X_plot)
Z_hit_cond = Z.reshape(xx_pl.shape)

cs = ax.contour(xx_pl, Z_hit_cond, yy_pl, linewidths=1.1, cmap='coolwarm',
                 levels=np.arange(0.5, 3.0, step=0.25))
ax.scatter(df_miss[xvar], df_miss[cost_var], color=cmap(0.), alpha=0.5,
          edgecolors='k')
ax.clabel(cs, fontsize=label_size)
ax.set_xlabel(r'$R_y$', fontsize=axis_font)
ax.grid(visible=True)
ax.set_ylim([0.0, 0.05])
# ax.set_xlim([0.7, 4.0])
plt.show()

#%% 3d surf for replacement risk
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 18
subt_font = 18
label_size = 12
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 
# plt.close('all')

fig = plt.figure(figsize=(16, 7))



#################################
xvar = 'gap_ratio'
yvar = 'RI'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 3.0, fourth_var_set = 0.15)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_repl_hit.gpr, mdl_repl_miss.gpr, outcome='replacement_freq')


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_surf = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 1, projection='3d')
surf = ax.plot_surface(xx_pl, yy_pl, Z_surf, cmap='Blues',
                       linewidth=0, antialiased=False, alpha=0.6,
                       vmin=-0.1)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.scatter(df[xvar], df[yvar], df['replacement_freq'], c=df['replacement_freq'],
           edgecolors='k', alpha = 0.7, cmap='Blues')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='x', offset=xlim[0], cmap='Blues_r')
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='y', offset=ylim[1], cmap='Blues')

ax.set_xlabel('Gap ratio', fontsize=axis_font)
ax.set_ylabel('$R_y$', fontsize=axis_font)
#ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
ax.set_title('$T_M/T_{fb} = 3.0$, $\zeta_M = 0.15$', fontsize=subt_font)

#################################
xvar = 'T_ratio'
yvar = 'zeta_e'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 1.0, fourth_var_set = 2.0)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_cost_hit.gpr, mdl_cost_miss.gpr, outcome='replacement_freq')


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_surf = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 2, projection='3d')
surf = ax.plot_surface(xx_pl, yy_pl, Z_surf, cmap='Blues',
                       linewidth=0, antialiased=False, alpha=0.6,
                       vmin=-0.1)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.scatter(df[xvar], df[yvar], df['replacement_freq'], c=df['replacement_freq'],
           edgecolors='k', alpha = 0.7, cmap='Blues')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='x', offset=xlim[0], cmap='Blues_r')
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='y', offset=ylim[1], cmap='Blues')

ax.set_xlabel('$T_M/ T_{fb}$', fontsize=axis_font)
ax.set_ylabel('$\zeta_M$', fontsize=axis_font)
#ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
ax.set_title('$GR = 1.0$, $R_y = 2.0$', fontsize=subt_font)
fig.tight_layout()

# #################################
# xvar = 'gap_ratio'
# yvar = 'RI'

# res = 75
# X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
#                             all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
#                             third_var_set = 3.0, fourth_var_set = 0.15)
# xx = X_plot[xvar]
# yy = X_plot[yvar]

# Z = predict_DV(X_plot, mdl_impact.gpc, 
#                mdl_time_hit.gpr, mdl_time_miss.gpr, outcome=time_var)


# x_pl = np.unique(xx)
# y_pl = np.unique(yy)
# xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

# Z_time = np.array(Z).reshape(xx_pl.shape)

# ax=fig.add_subplot(1, 3, 3, projection='3d')
# surf = ax.plot_surface(xx_pl, yy_pl, Z_cost, cmap='Blues',
#                        linewidth=0, antialiased=False, alpha=0.6,
#                        vmin=-0.1)

# ax.xaxis.pane.fill = False
# ax.yaxis.pane.fill = False
# ax.zaxis.pane.fill = False

# ax.scatter(df[xvar], df[yvar], df[time_var], c=df[time_var],
#            edgecolors='k', alpha = 0.7, cmap='Blues')

# xlim = ax.get_xlim()
# ylim = ax.get_ylim()
# zlim = ax.get_zlim()
# cset = ax.contour(xx_pl, yy_pl, Z_cost, zdir='x', offset=xlim[0], cmap='Blues_r')
# cset = ax.contour(xx_pl, yy_pl, Z_cost, zdir='y', offset=ylim[1], cmap='Blues')

# ax.set_xlabel('Gap ratio', fontsize=axis_font)
# ax.set_ylabel('$R_y$', fontsize=axis_font)
# #ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
# ax.set_title('c) Replacement time (GPR)', fontsize=subt_font)

# fig.tight_layout(w_pad=0.0)

#%% 2d contours for replacement

plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 18
subt_font = 18
label_size = 12
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 
# plt.close('all')

fig = plt.figure(figsize=(16, 7))



#################################
xvar = 'gap_ratio'
yvar = 'RI'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 3.0, fourth_var_set = 0.15)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_repl_hit.gpr, mdl_repl_miss.gpr, outcome='replacement_freq')


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_contour = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 1)

plt_density = 200
lvls = [0.025, 0.05, 0.10, 0.2, 0.3]
cs = plt.contour(xx_pl, yy_pl, Z_contour, linewidths=1.1, cmap='Blues', vmin=-1,
                 levels=lvls)
plt.clabel(cs, fontsize=clabel_size)
plt.scatter(df[xvar][:plt_density], df[yvar][:plt_density], 
            c=df['replacement_freq'][:plt_density],
            edgecolors='k', s=20.0, cmap=plt.cm.Blues, vmax=5e-1)
plt.xlim([0.3, 2.0])
plt.ylim([0.5, 2.25])
plt.xlabel('$GR$', fontsize=axis_font)
plt.ylabel('$R_y$', fontsize=axis_font)
plt.grid(True)

#################################
xvar = 'T_ratio'
yvar = 'zeta_e'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 1.0, fourth_var_set = 2.0)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_repl_hit.gpr, mdl_repl_miss.gpr, outcome='replacement_freq')


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_contour = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 2)

plt_density = 200
lvls = [0.025, 0.05, 0.10, 0.2, 0.3]
cs = ax.contour(xx_pl, yy_pl, Z_contour, linewidths=1.1, cmap='Blues', vmin=-1,
                 levels=lvls)
plt.clabel(cs, fontsize=clabel_size)
ax.scatter(df[xvar][:plt_density], df[yvar][:plt_density], 
            c=df['replacement_freq'][:plt_density],
            edgecolors='k', s=20.0, cmap=plt.cm.Blues, vmax=5e-1)
plt.xlim([2.0, 5.0])
plt.ylim([0.1, 0.25])
plt.xlabel('$T_M/T_{fb}$', fontsize=axis_font)
plt.ylabel('$\zeta_M$', fontsize=axis_font)
plt.grid(True)
plt.show()

#%% 3d surf for cost ratio
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 18
subt_font = 18
label_size = 12
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 
# plt.close('all')

fig = plt.figure(figsize=(16, 7))



#################################
xvar = 'gap_ratio'
yvar = 'RI'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 3.0, fourth_var_set = 0.15)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_repl_hit.gpr, mdl_repl_miss.gpr, outcome=cost_var)


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_surf = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 1, projection='3d')
surf = ax.plot_surface(xx_pl, yy_pl, Z_surf, cmap='Blues',
                       linewidth=0, antialiased=False, alpha=0.6,
                       vmin=-0.1)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.scatter(df[xvar], df[yvar], df[cost_var], c=df[cost_var],
           edgecolors='k', alpha = 0.7, cmap='Blues')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='x', offset=xlim[0], cmap='Blues_r')
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='y', offset=ylim[1], cmap='Blues')

ax.set_xlabel('Gap ratio', fontsize=axis_font)
ax.set_ylabel('$R_y$', fontsize=axis_font)
#ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
ax.set_title('$T_M/T_{fb} = 3.0$, $\zeta_M = 0.15$', fontsize=subt_font)

#################################
xvar = 'T_ratio'
yvar = 'zeta_e'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 1.0, fourth_var_set = 2.0)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_cost_hit.gpr, mdl_cost_miss.gpr, outcome=cost_var)


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_surf = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 2, projection='3d')
surf = ax.plot_surface(xx_pl, yy_pl, Z_surf, cmap='Blues',
                       linewidth=0, antialiased=False, alpha=0.6,
                       vmin=-0.1)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.scatter(df[xvar], df[yvar], df[cost_var], c=df[cost_var],
           edgecolors='k', alpha = 0.7, cmap='Blues')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='x', offset=xlim[0], cmap='Blues_r')
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='y', offset=ylim[1], cmap='Blues')

ax.set_xlabel('$T_M/ T_{fb}$', fontsize=axis_font)
ax.set_ylabel('$\zeta_M$', fontsize=axis_font)
#ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
ax.set_title('$GR = 1.0$, $R_y = 2.0$', fontsize=subt_font)
fig.tight_layout()

#%% 3d surf for time ratio
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"
axis_font = 18
subt_font = 18
label_size = 12
mpl.rcParams['xtick.labelsize'] = label_size 
mpl.rcParams['ytick.labelsize'] = label_size 
# plt.close('all')

fig = plt.figure(figsize=(16, 7))



#################################
xvar = 'gap_ratio'
yvar = 'RI'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 3.0, fourth_var_set = 0.15)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_repl_hit.gpr, mdl_repl_miss.gpr, outcome=time_var)


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_surf = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 1, projection='3d')
surf = ax.plot_surface(xx_pl, yy_pl, Z_surf, cmap='Blues',
                       linewidth=0, antialiased=False, alpha=0.6,
                       vmin=-0.1)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.scatter(df[xvar], df[yvar], df[time_var], c=df[time_var],
           edgecolors='k', alpha = 0.7, cmap='Blues')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='x', offset=xlim[0], cmap='Blues_r')
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='y', offset=ylim[1], cmap='Blues')

ax.set_xlabel('Gap ratio', fontsize=axis_font)
ax.set_ylabel('$R_y$', fontsize=axis_font)
#ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
ax.set_title('$T_M/T_{fb} = 3.0$, $\zeta_M = 0.15$', fontsize=subt_font)

#################################
xvar = 'T_ratio'
yvar = 'zeta_e'

res = 75
X_plot = make_2D_plotting_space(mdl_impact.X, res, x_var=xvar, y_var=yvar, 
                            all_vars=['gap_ratio', 'RI', 'T_ratio', 'zeta_e'],
                            third_var_set = 1.0, fourth_var_set = 2.0)
xx = X_plot[xvar]
yy = X_plot[yvar]

K_space = mdl_impact.get_kernel(X_plot, kernel_name='rbf', gamma=0.25)

Z = predict_DV(X_plot, mdl_impact.log_reg_kernel, 
               mdl_cost_hit.gpr, mdl_cost_miss.gpr, outcome=time_var)


x_pl = np.unique(xx)
y_pl = np.unique(yy)
xx_pl, yy_pl = np.meshgrid(x_pl, y_pl)

Z_surf = np.array(Z).reshape(xx_pl.shape)

ax=fig.add_subplot(1, 2, 2, projection='3d')
surf = ax.plot_surface(xx_pl, yy_pl, Z_surf, cmap='Blues',
                       linewidth=0, antialiased=False, alpha=0.6,
                       vmin=-0.1)
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False

ax.scatter(df[xvar], df[yvar], df[time_var], c=df[time_var],
           edgecolors='k', alpha = 0.7, cmap='Blues')

xlim = ax.get_xlim()
ylim = ax.get_ylim()
zlim = ax.get_zlim()
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='x', offset=xlim[0], cmap='Blues_r')
cset = ax.contour(xx_pl, yy_pl, Z_surf, zdir='y', offset=ylim[1], cmap='Blues')

ax.set_xlabel('$T_M/ T_{fb}$', fontsize=axis_font)
ax.set_ylabel('$\zeta_M$', fontsize=axis_font)
#ax1.set_zlabel('Median loss ($)', fontsize=axis_font)
ax.set_title('$GR = 1.0$, $R_y = 2.0$', fontsize=subt_font)
fig.tight_layout()