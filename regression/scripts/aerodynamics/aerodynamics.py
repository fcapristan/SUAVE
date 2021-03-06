# aerodynamics.py
# 
# Created:  Sep 2014, T. MacDonald
# Modified: Feb 2016, T. MacDonald
#
# Modified to match compressibility drag updates

import SUAVE
from SUAVE.Core import Units
from SUAVE.Core import Data


from mission_B737 import vehicle_setup

import numpy as np
import pylab as plt

import copy, time
from copy import deepcopy
import random
from SUAVE.Attributes.Gases.Air import Air

def main():
    
    # initialize the vehicle
    vehicle = vehicle_setup() 
    for wing in vehicle.wings:
        wing.areas.wetted   = 2.0 * wing.areas.reference
        wing.areas.exposed  = 0.8 * wing.areas.wetted
        wing.areas.affected = 0.6 * wing.areas.wetted  
        
        
    # initalize the aero model
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.geometry = vehicle
        
    aerodynamics.initialize()    
    
    
    #no of test points
    test_num = 11
    
    #specify the angle of attack
    angle_of_attacks = np.linspace(-.174,.174,test_num)[:,None] #* Units.deg
    
    
    # Cruise conditions (except Mach number)
    state = SUAVE.Analyses.Mission.Segments.Conditions.State()
    state.conditions = SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics()
    
    
    state.expand_rows(test_num)    
        
    # --------------------------------------------------------------------
    # Initialize variables needed for CL and CD calculations
    # Use a seeded random order for values
    # --------------------------------------------------------------------
    
    random.seed(1)
    Mc = np.linspace(0.05,0.9,test_num)
    random.shuffle(Mc)
    rho = np.linspace(0.3,1.3,test_num)
    random.shuffle(rho)
    mu = np.linspace(5*10**-6,20*10**-6,test_num)
    random.shuffle(mu)
    T = np.linspace(200,300,test_num)
    random.shuffle(T)
    pressure = np.linspace(10**5,10**6,test_num)
    
    # Changed after to preserve seed for initial testing
    Mc = Mc[:,None]
    rho = rho[:,None]
    mu = mu[:,None]
    T = T[:,None]
    pressure = pressure[:,None]
    
    air = Air()
    a = air.compute_speed_of_sound(T,pressure)
    
    re = rho*a*Mc/mu

    
    state.conditions.freestream.mach_number = Mc
    state.conditions.freestream.density = rho
    state.conditions.freestream.dynamic_viscosity = mu
    state.conditions.freestream.temperature = T
    state.conditions.freestream.pressure = pressure
    state.conditions.freestream.reynolds_number = re
    
    state.conditions.aerodynamics.angle_of_attack = angle_of_attacks   
    
    
    # --------------------------------------------------------------------
    # Surrogate
    # --------------------------------------------------------------------    
    
            
    #call the aero model        
    results = aerodynamics.evaluate(state)
    
    #build a polar for the markup aero
    polar = Data()    
    CL = results.lift.total
    CD = results.drag.total
    polar.lift = CL
    polar.drag = CD    
    
    
    # --------------------------------------------------------------------
    # Test compute Lift
    # --------------------------------------------------------------------
    
    
    
    #compute_aircraft_lift(conditions, configuration, geometry) 
    
    lift = state.conditions.aerodynamics.lift_coefficient
    lift_r = np.array([-2.42489437, -0.90696416, -0.53991953, -0.3044834 ,  -0.03710598,
                       0.31061936 ,  0.52106899,  0.77407765,  1.22389024,  1.86240501,
                       1.54587835])[:,None]
    
    lift_test = np.abs((lift-lift_r)/lift)
    
    print '\nCompute Lift Test Results\n'
    #print lift_test
        
    assert(np.max(lift_test)<1e-4), 'Aero regression failed at compute lift test'    
    
    
    # --------------------------------------------------------------------
    # Test compute drag 
    # --------------------------------------------------------------------
    
    #compute_aircraft_drag(conditions, configuration, geometry)
    
    # Pull calculated values
    drag_breakdown = state.conditions.aerodynamics.drag_breakdown
    
    # Only one wing is evaluated since they rely on the same function
    cd_c           = drag_breakdown.compressible['main_wing'].compressibility_drag
    cd_i           = drag_breakdown.induced.total
    cd_m           = drag_breakdown.miscellaneous.total
    # cd_m_fuse_base = drag_breakdown.miscellaneous.fuselage_base
    # cd_m_fuse_up   = drag_breakdown.miscellaneous.fuselage_upsweep
    # cd_m_nac_base  = drag_breakdown.miscellaneous.nacelle_base['turbo_fan']
    # cd_m_ctrl      = drag_breakdown.miscellaneous.control_gaps
    cd_p_fuse      = drag_breakdown.parasite['fuselage'].parasite_drag_coefficient
    cd_p_wing      = drag_breakdown.parasite['main_wing'].parasite_drag_coefficient
    cd_tot         = drag_breakdown.total
    
    
    (cd_c_r, cd_i_r, cd_m_r, cd_m_fuse_base_r, cd_m_fuse_up_r, cd_m_nac_base_r, cd_m_ctrl_r, cd_p_fuse_r, cd_p_wing_r, cd_tot_r) = reg_values()
    
    drag_tests = Data()
    drag_tests.cd_c = np.abs((cd_c-cd_c_r)/cd_c)
    drag_tests.cd_i = np.abs((cd_i-cd_i_r)/cd_i)
    drag_tests.cd_m = np.abs((cd_m-cd_m_r)/cd_m)
    ## Commented lines represent values not set by current drag functions, but to be recreated in the future
    # Line below is not normalized since regression values are 0, insert commented line if this changes
    # drag_tests.cd_m_fuse_base = np.abs((cd_m_fuse_base-cd_m_fuse_base_r)) # np.abs((cd_m_fuse_base-cd_m_fuse_base_r)/cd_m_fuse_base)
    # drag_tests.cd_m_fuse_up   = np.abs((cd_m_fuse_up - cd_m_fuse_up_r)/cd_m_fuse_up)
    # drag_tests.cd_m_ctrl      = np.abs((cd_m_ctrl - cd_m_ctrl_r)/cd_m_ctrl)
    drag_tests.cd_p_fuse      = np.abs((cd_p_fuse - cd_p_fuse_r)/cd_p_fuse)
    drag_tests.cd_p_wing      = np.abs((cd_p_wing - cd_p_wing_r)/cd_p_wing)
    drag_tests.cd_tot         = np.abs((cd_tot - cd_tot_r)/cd_tot)
    
    print '\nCompute Drag Test Results\n'
    #print drag_tests
    
    for i, tests in drag_tests.items():
        assert(np.max(tests)<1e-4),'Aero regression test failed at ' + i
    
    #return conditions, configuration, geometry, test_num
      

def reg_values():
    cd_c_r = np.array([  2.08459463e-09,   1.08648911e-09,   4.40666169e-23,   1.88258599e-09,
                         3.71806409e-04,   6.07658788e-05,   2.38156998e-09,   4.35875057e-11,
                         7.93890380e-05,   2.19714380e-03,   6.81119259e-14])
    
    cd_i_r = np.array([ 2.37792323e-01,  3.36989611e-02, 1.29763962e-02,  3.78292450e-03, 5.68310476e-05,
                        3.85710691e-03,  1.11551856e-02,   2.55851168e-02,  6.14241594e-02,  1.40294860e-01,
                        9.83364067e-02])
    cd_m_r = np.array([ 0.00116061,  0.00116061, 0.00116061,  0.00116061,  0.00116061,
                        0.00116061,  0.00116061,  0.00116061, 0.00116061,  0.00116061,
                        0.00116061])
    
    cd_m_fuse_base_r = np.array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.])
    
    cd_m_fuse_up_r   = np.array([  4.80530506e-05,   4.80530506e-05,   4.80530506e-05,
                                   4.80530506e-05,   4.80530506e-05,   4.80530506e-05,
                                   4.80530506e-05,   4.80530506e-05,   4.80530506e-05,
                                   4.80530506e-05,   4.80530506e-05])
    
    cd_m_nac_base_r = np.array([ 0.00033128,  0.00033128,  0.00033128,  0.00033128,  0.00033128,
                                0.00033128,  0.00033128,  0.00033128,  0.00033128,  0.00033128,
                                0.00033128])
    
    cd_m_ctrl_r     = np.array([ 0.0001,  0.0001,  0.0001,  0.0001,  0.0001,  0.0001,  0.0001,
                                 0.0001,  0.0001,  0.0001,  0.0001])
    
    cd_p_fuse_r     = np.array([0.00581516 ,  0.00688254,  0.01062775,  0.00675354,  0.00682628,
                                 0.00574868,  0.00707676, 0.00876415,  0.00686934,  0.00614271,
                                  0.00718073])
    
    cd_p_wing_r     = np.array([ 0.00568318,  0.00574321,  0.00911242,  0.00555159,  0.00636405,
                                  0.0048708 ,  0.00579879,  0.00734795,  0.00582637,  0.0054087,
                                 0.00583051])
    
    cd_tot_r        = np.array([ 0.2595146 ,  0.05226547,  0.04064861,  0.02131243,  0.01927301,
                                 0.01923316,  0.02958776,  0.048638 ,  0.08073247, 0.16186261,
                                 0.11868474])
    
    return cd_c_r[:,None], cd_i_r[:,None], cd_m_r[:,None], cd_m_fuse_base_r[:,None], cd_m_fuse_up_r[:,None], \
           cd_m_nac_base_r[:,None], cd_m_ctrl_r[:,None], cd_p_fuse_r[:,None], cd_p_wing_r[:,None], cd_tot_r[:,None]

if __name__ == '__main__':
    #(conditions, configuration, geometry, test_num) = main()
    main()
    
    print 'Aero regression test passed!'
    
    ## --------------------------------------------------------------------
    ## Drag Polar
    ## --------------------------------------------------------------------  
    
    # --------------------------------------------------------------------
    # Drag Polar
    # --------------------------------------------------------------------
    
    # initialize the vehicle
    vehicle = vehicle_setup() 
    for wing in vehicle.wings:
        wing.areas.wetted   = 2.0 * wing.areas.reference
        wing.areas.exposed  = 0.8 * wing.areas.wetted
        wing.areas.affected = 0.6 * wing.areas.wetted  
        
        
    # initalize the aero model
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.geometry = vehicle
    
    ## modify inviscid wings - linear model
    #inviscid_wings = SUAVE.Analyses.Aerodynamics.Linear_Lift()
    #inviscid_wings.settings.slope_correction_coefficient = 1.04
    #inviscid_wings.settings.zero_lift_coefficient = 2.*np.pi* 3.1 * Units.deg    
    #aerodynamics.process.compute.lift.inviscid_wings = inviscid_wings
    
    ## modify inviscid wings - avl model
    #inviscid_wings = SUAVE.Analyses.Aerodynamics.Surrogates.AVL()
    #inviscid_wings.geometry = vehicle
    #aerodynamics.process.compute.lift.inviscid_wings = inviscid_wings
    
    aerodynamics.initialize()    
    
    
    #no of test points
    test_num = 11
    
    #specify the angle of attack
    angle_of_attacks = np.linspace(-.174,.174,test_num) #* Units.deg
    
    
    # Cruise conditions (except Mach number)
    state = SUAVE.Analyses.Mission.Segments.Conditions.State()
    state.conditions = SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics()
    
    
    state.expand_rows(test_num)    
    
    #specify  the conditions at which to perform the aerodynamic analysis
    state.conditions.aerodynamics.angle_of_attack[:,0] = angle_of_attacks
    state.conditions.freestream.mach_number = np.array([0.8]*test_num)
    state.conditions.freestream.density = np.array([0.3804534]*test_num)
    state.conditions.freestream.dynamic_viscosity = np.array([1.43408227e-05]*test_num)
    state.conditions.freestream.temperature = np.array([218.92391647]*test_num)
    state.conditions.freestream.pressure = np.array([23908.73408391]*test_num)

    #call the aero model        
    results = aerodynamics.evaluate(state)
    
    #build a polar for the markup aero
    polar = Data()    
    CL = results.lift.total
    CD = results.drag.total
    polar.lift = CL
    polar.drag = CD
    

    ##load old results
    #old_polar = SUAVE.Input_Output.load('polar_M8.pkl') #('polar_old2.pkl')
    #CL_old = old_polar.lift
    #CD_old = old_polar.drag

    
    #plot the results
    plt.figure("Drag Polar")
    axes = plt.gca()     
    axes.plot(CD,CL,'bo-') #CD_old) #,CL_old,'*')
    axes.set_xlabel('$C_D$')
    axes.set_ylabel('$C_L$')
    
    
    plt.show(block=True) # here so as to not block the regression test
      
