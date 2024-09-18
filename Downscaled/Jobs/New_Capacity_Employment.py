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
import zipfile
import shapefile

os.chdir('C:/Users/lfernandezintriago/OneDrive - Environmental Defense Fund - edf.org/Documents/GitHub/')

### define model/scenario
model = 'GenX'
#scenario = '26z-short-base-50'
scenario = 'full-base-200'

job_coefs = pd.read_csv('MIP_AirPollution-main/Job_Coefficients.csv')
new_capacity = pd.read_csv('MIP_results_comparison/'+scenario+'/'+model+'_results_summary/aggregated_capacity_calc.csv')

#only need coefs for jobs/GW
job_coefs = job_coefs[job_coefs['Units']=='jobs/GW capacity']
#i don't know what mining or transportation jobs from capacity go???
job_coefs['Subresource'] = job_coefs['Subresource'].str.strip()

job_coefs = job_coefs[(job_coefs['Subresource'].isna())|(job_coefs['Subresource']=='utility-scale solar')]
job_coefs = job_coefs.rename(columns={'Resource':'tech_type'})
#new_capacity.loc[new_capacity['resource_name'].str.contains('biomass'), 'tech_type'] = 'Biomass'

new_capacity['tech_type'] = new_capacity['tech_type'].str.lower()
job_coefs['tech_type']=job_coefs['tech_type'].str.lower()
new_capacity = pd.merge(new_capacity, job_coefs, how='left', on='tech_type')

#nothing for hydro, batteries
new_capacity['capacity_GW']=new_capacity['new_build_value']/1000
new_capacity['jobs'] = new_capacity['capacity_GW']*new_capacity['Parameter Value']

employment = new_capacity.groupby(['zone', 'tech_type','planning_year']).agg({'jobs':'sum'}).reset_index()

##############################
## divy up population by 26z region to states -- more code than I need but might be useful later
##############################

url = "https://www2.census.gov/programs-surveys/popest/datasets/2020-2022/counties/totals/co-est2022-alldata.csv"
#url2 = "https://www2.census.gov/geo/tiger/TIGER2022/COUNTY/tl_2022_us_county.zip"

counties = pd.read_csv(url, encoding='latin-1')

counties = counties[['STNAME','CTYNAME','ESTIMATESBASE2020','POPESTIMATE2020','POPESTIMATE2021', 'POPESTIMATE2022']]

#counties.columns = ['Location', '2020Base','2020', '2021', '2022', 'Pop']

state =  counties [counties ['STNAME'] == counties ['CTYNAME']]

counties_shape = gpd.read_file(r'C:\Users\lfernandezintriago\OneDrive - Environmental Defense Fund - edf.org\Documents\EDF\Projects\Sloan\Data\tl_2022_us_county\tl_2022_us_county.shp')
