############################################################################
#               Temporary RC shear wall design script

# Created by:   Huy Pham
#               University of California, Berkeley

# Date created: September 2022

# Description:  

# Open issues:  (1) forces need to adjust Ry for structural system

############################################################################

from design_superstructure import get_story_forces


ft = 12.0
ksi = 1000.0
psi = 1.0
kip = 1000.0

D_m = 22.12
K_e = 40.073
zeta_e = 0.15
W_tot = 3530
n_frames = 2
W_s = 2227.5
R_y = 2.0

wx, hx, hCol, hsx, wLoad, Fx, V_s = get_story_forces(D_m, K_e, W_tot, W_s, 
                                                    n_frames, zeta_e, 
                                                    R_y, 'SW')
# unit conversion to pounds/in
wx = wx*kip
wLoad = wLoad*kip
Fx = Fx*kip
V_u = V_s*kip

L_bay = 22.5*ft
l_w = L_bay

import numpy as np
from math import ceil

h_w = np.sum(hsx)

is_squat = (h_w <= 2*l_w)

# squat wall design
l_be = 0.2*l_w

f_c = 4000.0*psi
f_yc = 60000.0*psi
f_ys = 75000.0*psi

# required area
# all assuming normalweight concrete
A_cv = V_u / (4*(f_c**(0.5)))
b_w = ceil(A_cv / l_w)

# P-M design
# loads already account combos and LL reduction
M_u = np.sum(Fx*hx)
M_n = M_u / 0.65 # phi for Grade 60 steel
P_u = np.sum(wLoad)*(90*ft)
rho_l = 0.0025
T_s2= rho_l*f_ys*(0.6*l_w)*b_w
T_s1 = (M_n - P_u*(0.4*l_w) - T_s2*(0.4*l_w))/(0.8*l_w)
A_s1 = T_s1/f_ys

# nominal shear strength and transverse steel
# 
if (h_w/l_w <= 1.5):
    alpha_c = 3.0 * psi
elif (h_w/l_w >= 2.0):
    alpha_c = 2.0 * psi
else:
    alpha_c = np.interp(h_w/l_w, [1.5, 2.5], [3.0, 2.0])

phi = 0.6
rho_t = 1/f_ys * (V_u/(phi*l_w*b_w) - alpha_c * (f_c**(0.5)))

two_curtains = V_u > 2*A_cv*(f_c**(0.5))

# minimum reinforcement