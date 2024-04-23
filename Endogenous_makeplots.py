globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from matplotlib.colors import LinearSegmentedColormap



os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')

scenario = 'current_policies'

coefs = pd.read_csv('MIP_AirPollution/marginal_gen_exposure_coefs_2050.csv', dtype={'Exposure':float}, low_memory=False)
coefs2 = pd.read_csv('MIP_AirPollution/marginal_gen_exposure_coefs_2050.csv', low_memory=True)

def update_technology(row):
    if 'naturalgas_ccavg' in row['Cluster']:
        return 'natural gas cc'
    elif 'natural_gas_fired_combined' in row['Cluster']:
        return 'natural gas cc'
    elif 'naturalgas_ctavg' in row['Cluster']:
        return 'natural gas ct'
    elif 'natural_gas_fired_combustion' in row['Cluster']:
        return 'natural gas ct'
    elif 'coal' in row['Cluster']:
        return 'coal'
    else:
        return np.nan

coefs['technology'] = coefs.apply(update_technology, axis=1)
coefs2['technology']= coefs2.apply(update_technology, axis=1)

summary=coefs.groupby(['technology', 'Pollutant']).agg({'Exposure':'mean'}).reset_index()
print(summary.groupby('technology').agg({'Exposure':'sum'}))

year='2050'
emis = gpd.read_file('InMap/MIP_Emissions/marginal_emissions_'+year+'.shp')
emis = pd.DataFrame(emis[['NOx', 'SOx', 'PM2_5', 'NH3', 'VOC', 'Resource']])

emis = emis.groupby(['Resource']).agg({'NOx':'sum', 'PM2_5':'sum', 'NH3':'sum', 'SOx':'sum', 'PM2_5':'sum'}).reset_index()

def update_technology(row):
    if 'naturalgas_ccavg' in row['Resource']:
        return 'natural gas cc'
    elif 'natural_gas_fired_combined' in row['Resource']:
        return 'natural gas cc'
    elif 'naturalgas_ctavg' in row['Resource']:
        return 'natural gas ct'
    elif 'natural_gas_fired_combustion' in row['Resource']:
        return 'natural gas ct'
    elif 'coal' in row['Resource']:
        return 'coal'
    else:
        return np.nan
    
emis['technology'] = emis.apply(update_technology, axis=1)

print(emis.groupby(['technology']).agg({'NOx':'mean', 'PM2_5':'mean', 'NH3':'mean', 'SOx':'mean', 'PM2_5':'mean'}).reset_index())