#%%
globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from matplotlib.colors import LinearSegmentedColormap



os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')

from MIP_AirPollution.Downscaled.settings import *
model='GenX'

jobs = pd.read_csv('MIP_AirPollution/Downscaled/Jobs/employment.csv', header=None)
states = gpd.read_file('tl_2022_us_state/tl_2022_us_state.shp')
states = states[~states['STUSPS'].isin(['AS', 'AK', 'GU', 'MP', 'VI', 'HI', 'PR'])]

jobs.columns=['planning_year', 'State', 'jobs', 'scenario']

#plot 2027 to 2050 difference
jobs_dif = jobs[jobs['planning_year'].isin([2027,2050])]
jobs_dif = jobs_dif.sort_values('planning_year') 
jobs_dif['lag_jobs'] = jobs_dif.groupby(['State', 'scenario'])['jobs'].shift(1)
jobs_dif['pct_change']=(jobs_dif['jobs']-jobs_dif['lag_jobs'])/jobs_dif['lag_jobs']
jobs_dif = jobs_dif[jobs_dif['planning_year']==2050]
jobs_dif['pct_change']=jobs_dif['pct_change']*100

min_dif = min(0, min(jobs_dif['pct_change']))
max_dif = max(jobs_dif['pct_change'])
for scenario in scenario_dictionary:
    jobs_dif_temp=jobs_dif[jobs_dif['scenario']==scenario]

    merged_data = states.merge(jobs_dif_temp, left_on='NAME', right_on='State',how='left')
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    merged_data.plot(column='pct_change', 
                     ax=ax, 
                     legend=True, 
                     cmap='OrRd',
                     edgecolor='black',
                     linewidth=0.5,
                     vmin=min_dif,
                     vmax=max_dif)

    plt.title('Percent Change in Energy Employment by State - 2027 to 2050', fontsize=15)
    plt.savefig('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/jobs_change.jpg', format='jpg',
            dpi=300, bbox_inches='tight')

### 
#Plot overall employment relative to current_policies
jobs_relative = jobs[jobs['planning_year']==2050]
jobs_relative = jobs_relative.groupby(['scenario']).agg({'jobs':'sum'}).reset_index()
counterfac_number = jobs_relative[jobs_relative['scenario']=='full-current-policies']
counterfac_number = float(counterfac_number['jobs'])

jobs_relative['percent_dif']=(jobs_relative['jobs']-counterfac_number)/counterfac_number
jobs_relative = jobs_relative[jobs_relative['scenario']!='full-current-policies']
plt.figure(figsize=(8, 6))  # Set the figure size
plt.bar(jobs_relative['scenario'], jobs_relative['percent_dif'], color='skyblue') 

# Add titles and labels
plt.title('Percent Difference in Aggregate Jobs in \n 2050 Relative to Current Policies', fontsize=15)
plt.xticks(rotation=-90)

plt.show()
plt.savefig('MIP_AirPollution/Figures/Output/Jobs_2050_relative_difference.jpg', format='jpg',
            dpi=300, bbox_inches='tight')