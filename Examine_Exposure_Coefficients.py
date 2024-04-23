import time
import numpy as np
import pandas as pd
import geopandas as gpd
import os
import seaborn as sns
import matplotlib.pyplot as plt



os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')

coefficients = pd.read_csv('MIP_AirPollution/marginal_gen_exposure_coefs_2030.csv')

coefficients = coefficients.groupby(['Race', 'Cluster']).agg({'Exposure':'sum'}).reset_index()


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
    elif 'biomass' in row['Cluster']:
        return 'biomass'
    elif 'petroleum_liquids' in row['Cluster']:
        return 'petroleum liquids'
    else:
        return np.nan
    
coefficients['technology'] = coefficients.apply(update_technology, axis=1)

mean = coefficients.groupby('technology').agg({'Exposure':'mean'}).reset_index()

plt.figure(figsize=(10, 6))
for tech, group_data in coefficients.groupby('technology'):
    sns.kdeplot(data=group_data['Exposure'], label=tech, cumulative=True)

plt.title('CDF of Exposure Coefficients by Technology')
plt.xlabel('Exposure Coefficient')
plt.ylabel('Density')
plt.legend(title='Technology')
plt.savefig('MIP_AirPollution/Figures/CDF_exposure_coef.png')
plt.show()

test = coefficients[coefficients['Exposure']<0]