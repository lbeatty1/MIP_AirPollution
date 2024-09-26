# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 15:03:05 2024

@author: lfernandezintriago
"""

globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from datetime import datetime

os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')

#os.chdir('C:/Users/lfernandezintriago/OneDrive - Environmental Defense Fund - edf.org/Documents/GitHub/MIP Project/MIP_AirPollution/Downscaled/Jobs')


with open('MIP_AirPollution/Downscaled/Jobs/employment.csv', 'w') as file:
    pass


from FN_New_Capacity_Employment import calculate_employment_new_capacity
from FN_Capacity_Employment     import calculate_employment_capacity
from FN_Production_Employment   import calculate_employment_production
from FN_Retired_Employment      import calculate_employment_retired_capacity
from FN_Transmission_Employment import calculate_employment_transmission



model = 'GenX'
scenario_vector = ['full-base-50',
                   'full-base-200', 
                   'full-base-1000', 
                   'full-current-policies', 
                   'full-current-policies-commit', 
                   'full-current-policies-retire', 
                   'full-base-200-tx-0', 
                   'full-base-200-tx-15', 
                   'full-base-200-tx-50']

planning_period_length = {
    2027: 3,
    2030: 5,
    2035: 5,
    2040: 5,  
    2045: 5,
    2050: 5,
}
#scenario_vector = ['full-base-50']

for sc in scenario_vector:
    scenario = sc
    print('running scenario: '+ scenario)

    employment_new_capacity  = calculate_employment_new_capacity(model, scenario)
    #jobs per planning period
    print('finished running new capacity')

    employment_capacity      = calculate_employment_capacity(model, scenario)
    #jobs per year
    print('finished running capacity')

    employment_retired       = calculate_employment_retired_capacity(model, scenario)
    #jobs per planning period
    print('finished running retirement')

    employment_production    = calculate_employment_production(model, scenario)
    #jobs per year
    print('finished running resource extraction')

    employment_transmission  = calculate_employment_transmission(model, scenario) 
    #jobs per year
    print('finished running transmission')

    #switch jobs per planning period to jobs per year
    employment_retired['planning_period_length'] = employment_retired['planning_year'].map(planning_period_length)
    employment_retired['jobs']=employment_retired['jobs']/employment_retired['planning_period_length']

    employment_new_capacity['planning_period_length'] = employment_new_capacity['planning_year'].map(planning_period_length)
    employment_new_capacity['jobs']=employment_new_capacity['jobs']/employment_new_capacity['planning_period_length']

    
    employment_concat = pd.concat([employment_new_capacity, employment_capacity])
    employment_concat = pd.concat([employment_concat,employment_retired]) 
    employment_concat = pd.concat([employment_concat,employment_production])
    employment_concat = pd.concat([employment_concat,employment_transmission])
    employment_concat= employment_concat.groupby(['planning_year', 'State'], as_index=False)['jobs'].sum()
    employment_concat['scenario']=scenario
    print(employment_concat)
    
    employment_concat.to_csv('MIP_AirPollution/Downscaled/Jobs/employment.csv',mode='a', index=False, header=False)

    
    