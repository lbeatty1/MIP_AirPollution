# -*- coding: utf-8 -*-
"""
Created on Fri Jun 14 11:20:57 2024

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
os.chdir('C:/Users/lfernandezintriago/OneDrive - Environmental Defense Fund - edf.org/Documents/GitHub/MIP Project')

### define model/scenario
model = 'GenX'
#scenario = '26z-short-base-50'
scenario = 'full-base-200'

job_coefs = pd.read_csv('MIP_AirPollution/Downscaled/Jobs/Job_Coefficients.csv')
retirement = pd.read_csv('MIP_results_comparison/'+scenario+'/'+model+'_results_summary/aggregated_capacity_calc.csv')



#only need coefs for jobs/GW
job_coefs = job_coefs[job_coefs['Units']=='jobs/GW retired capacity']
#i don't know what mining or transportation jobs from capacity go???
job_coefs['Subresource'] = job_coefs['Subresource'].str.strip()

job_coefs = job_coefs[(job_coefs['Subresource'].isna())|(job_coefs['Subresource']=='utility-scale solar')]
job_coefs = job_coefs.rename(columns={'Resource':'tech_type'})
#retirement.loc[retirement['resource_name'].str.contains('biomass'), 'tech_type'] = 'Biomass'

retirement['tech_type'] = retirement['tech_type'].str.lower()
job_coefs['tech_type']=job_coefs['tech_type'].str.lower()
retirement = pd.merge(retirement, job_coefs, how='left', on='tech_type')

#nothing for hydro, batteries
retirement['capacity_GW']=retirement['retired_value']/1000
retirement['jobs'] = retirement['capacity_GW']*retirement['Parameter Value']

employment_retirement = retirement.groupby(['zone', 'tech_type','planning_year']).agg({'jobs':'sum'}).reset_index()

##############################
## divy up population by 26z region to states -- more code than I need but might be useful later
##############################

counties = pd.read_excel('Data/Jobs_Data/co-est2022-pop.xlsx', skiprows=3)
counties.columns = ['Location', '2020Base','2020', '2021', 'Pop']
counties = counties[counties['Location'].str.startswith('.')]
counties[['NAMELSAD', 'State']] = counties['Location'].str.split(', ', expand=True)
counties['NAMELSAD'] = counties['NAMELSAD'].str[1:]
counties = counties[['NAMELSAD', 'State', 'Pop']]

statepop = counties.groupby('State').agg({'Pop':'sum'}).rename(columns={'Pop':'StatePop'})
counties = pd.merge(counties, statepop, on='State', how='left')
counties['pct_statepop'] = counties['Pop']/counties['StatePop']

ipm_regions = gpd.read_file('Data/IPM_Regions/national_emm_boundaries.shp')
counties_shape = gpd.read_file('Data/Jobs_Data/tl_2022_us_county.shp')

ipm_regions = ipm_regions.to_crs(counties_shape.crs)

intersection = gpd.overlay(ipm_regions, counties_shape, how='intersection')

# Calculate the area of overlap for each intersecting polygon
intersection['overlap_area'] = intersection.geometry.area
#looks to me like ipm regions are supposed to be counties and slightly different resolutions causes more intersections than there should be
intersection = intersection[intersection['overlap_area'] == intersection.groupby(['STATEFP', 'NAME'])['overlap_area'].transform('max')]

state_fips_to_name = {
    1: 'Alabama', 2: 'Alaska', 4: 'Arizona', 5: 'Arkansas', 6: 'California',
    8: 'Colorado', 9: 'Connecticut', 10: 'Delaware', 11: 'District of Columbia',
    12: 'Florida', 13: 'Georgia', 15: 'Hawaii', 16: 'Idaho', 17: 'Illinois',
    18: 'Indiana', 19: 'Iowa', 20: 'Kansas', 21: 'Kentucky', 22: 'Louisiana',
    23: 'Maine', 24: 'Maryland', 25: 'Massachusetts', 26: 'Michigan',
    27: 'Minnesota', 28: 'Mississippi', 29: 'Missouri', 30: 'Montana',
    31: 'Nebraska', 32: 'Nevada', 33: 'New Hampshire', 34: 'New Jersey',
    35: 'New Mexico', 36: 'New York', 37: 'North Carolina', 38: 'North Dakota',
    39: 'Ohio', 40: 'Oklahoma', 41: 'Oregon', 42: 'Pennsylvania',
    44: 'Rhode Island', 45: 'South Carolina', 46: 'South Dakota',
    47: 'Tennessee', 48: 'Texas', 49: 'Utah', 50: 'Vermont', 51: 'Virginia',
    53: 'Washington', 54: 'West Virginia', 55: 'Wisconsin', 56: 'Wyoming'
}

# Map state FIPS codes to state names and create a new column
intersection['STATEFP']=intersection['STATEFP'].astype(int)
intersection['State'] = intersection['STATEFP'].map(state_fips_to_name)

intersection = pd.merge(intersection, counties, how='left', on=['NAMELSAD', 'State'])

pop_ipm = intersection.drop(columns='geometry').groupby('model_regi').agg({'Pop':'sum'}).reset_index().rename(columns={'Pop':'model_regi_pop'})
intersection = pd.merge(intersection, pop_ipm, how='left', on='model_regi')
intersection['pct_model_regi_pop'] = intersection['Pop']/intersection['model_regi_pop']

county_modelregi = intersection[['model_regi', 'NAME', 'State', 'Pop', 'StatePop', 'model_regi_pop', 'pct_statepop', 'pct_model_regi_pop']]

###################
# model region to states
model_region_pop = county_modelregi.groupby(['model_regi', 'State']).agg({'pct_model_regi_pop':'sum'}).reset_index()
model_region_pop = model_region_pop.rename(columns = {'model_regi':'zone'})
employment_retirement = pd.merge(employment_retirement, model_region_pop, how='left', on='zone')

employment_retirement['employment'] = employment_retirement['tech_type']+' retired'
employment_retirement = employment_retirement[['planning_year', 'State', 'jobs', 'employment']]# -*- coding: utf-8 -*-


