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

#os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')
os.chdir('C:/Users/lfernandezintriago/OneDrive - Environmental Defense Fund - edf.org/Documents/GitHub/MIP Project/MIP_AirPollution/Downscaled/Jobs/')



# Importing functions from existing scripts
from New_Capacity_Employment import employment_new_capacity
from Capacity_Employment import employment_capacity
from Retired_Employment import employment_retirement
from Production_Employment import employment_production

# Merging all employment DataFrames
merged_employment = employment_new_capacity.merge(employment_capacity, on='State', how='outer', suffixes=('_new', '_capacity'))
merged_employment = merged_employment.merge(employment_retirement, on='State', how='outer', suffixes=('', '_retired'))
merged_employment = merged_employment.merge(employment_production, on='State', how='outer', suffixes=('', '_production'))


#merged_employment.fillna(0, inplace=True)

# Calculating total jobs by state
merged_employment['total_jobs'] = (merged_employment['jobs_new'] +
                                   merged_employment['jobs_capacity'] +
                                   merged_employment['jobs_retired'] +
                                  merged_employment['jobs_production'])



# Selecting relevant columns for final output
#final_output = merged_employment[['State', 'total_jobs']]