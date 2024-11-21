#%%
globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns


os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')

from MIP_AirPollution.Downscaled.settings import *
model='GenX'


#%%
## Read in all data
emissions = pd.DataFrame()

for scenario in scenario_dictionary:
    print('reading: '+scenario)
    for file, year in year_inputs.items():
        temp = gpd.read_file('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/ISRM_result_'+f"{year}"+'.shp')
        temp['year']=year
        temp['scenario']=scenario
        emissions = pd.concat([emissions, temp])
        print(year)

#make file directories
for scenario in scenario_dictionary:
    if not os.path.exists('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/'):
        os.makedirs('MIP_AirPollution/Figures/Output/' + scenario + '/' + model )

    if not os.path.exists('MIP_results_comparison/'+scenario+'/AirPollution/'):
        os.makedirs('MIP_results_comparison/'+scenario+'/AirPollution')

#Plot output -- map of concentrations
#read in states
states = gpd.read_file('Data/tl_2022_us_state/tl_2022_us_state.shp')
states = states[~states['STUSPS'].isin(['AS', 'AK', 'GU', 'MP', 'VI', 'HI', 'PR'])]

print('finding intersection with land')
## Make all crs equal and throw out grid cells outside of U.S.
states = states.to_crs(emissions.crs)
intersects = emissions.geometry.intersects(states.unary_union)
emissions['intersects'] = intersects
emissions = emissions[emissions['intersects']==True]

# #Make concentration plots
columns_to_plot = ['TotalPM25']
quant_dict={}

#%%
print('making concentration plots')
for scenario in scenario_dictionary:
    for file, year in year_inputs.items():
        print('concentration: '+scenario+f"{year}")

        emissions_temp = emissions[emissions['year']==year]
        emissions_temp = emissions_temp[emissions_temp['scenario']==scenario]
        for column in columns_to_plot:

            #want scales to be the same for each plot
            if year==2027:
                print("Defining scale")
                q = 0.99  # Truncate results at the 99th percentile for better visualization
                cut = np.quantile(emissions_temp[column], q)
                quant_dict[column]=cut

            fig, ax = plt.subplots(figsize=(10, 8))

            # Plot data with color scale truncated at the specified quantile
            emissions_temp.plot(vmin=0, vmax=cut, cmap="OrRd", column=column, ax=ax)

            # Plot states boundaries
            states.boundary.plot(ax=ax, color='black', linewidth=0.2)

            # Add color bar
            sm = plt.cm.ScalarMappable(cmap='OrRd', norm=plt.Normalize(vmin=0, vmax=quant_dict[column]))
            sm._A = []  # Fake empty array for the colorbar
            cbar = fig.colorbar(sm, fraction=0.03)  
            cbar.set_label(column+' concentration (μg m$^{-3}$)', fontsize=18)  # Set color bar label
            cbar.ax.tick_params(labelsize=14)

            plt.axis('off')
            plt.savefig('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/ISRM_' +f"{year}"+'_'+ column + '_concentrationmap.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')
            plt.savefig('MIP_results_comparison/'+scenario+'/AirPollution/ISRM_'+f"{year}"+'_'+ column + '_concentrationmap.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')


#%%
print('making death plots')
deaths = pd.DataFrame(emissions[['Asiandeath', 'Blackdeath', 'Latinodeat', 'Nativedeat', 'WhiteNoL_1', 'year', 'scenario']])
deaths = deaths.groupby(['scenario','year']).sum().reset_index()

for scenario in scenario_dictionary:
    plt.figure(figsize=(10, 6))
    print('deaths: '+scenario)

    deaths_temp = deaths[deaths['scenario']==scenario]
    # Plot mortality rates
    plt.plot(deaths_temp['year'], deaths_temp['Latinodeat'], marker='o', label='Latino Deaths')
    plt.plot(deaths_temp['year'], deaths_temp['WhiteNoL_1'], marker='o', label='White/Non-hispanic Deaths')
    plt.plot(deaths_temp['year'], deaths_temp['Blackdeath'], marker='o', label='Black Deaths')
    plt.plot(deaths_temp['year'], deaths_temp['Asiandeath'], marker='o', label='Asian Deaths')

    # Add labels and title
    plt.xlabel('Year', fontsize=16)
    plt.ylabel('Total Deaths', fontsize=16)
    plt.title('Deaths Attributable to PM2.5 by Racial Group', fontsize=20)
    plt.legend(fontsize=14)

    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)

    # Show plot
    plt.grid(True)
    plt.savefig('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/ISRM_death_by_group.jpg', format='jpg',dpi=300, bbox_inches='tight')
    plt.savefig('MIP_results_comparison/'+scenario+'/AirPollution/ISRM_death_by_group.jpg', format='jpg',
                dpi=300, bbox_inches='tight')

# ### Plot death rates across time
    
print('making death rate plots')
death_rates = pd.DataFrame(emissions[['Asiandeath', 'Blackdeath', 'Latinodeat', 'Nativedeat', 'WhiteNoL_1', 'Asian', 'Black', 'Latino', 'Native', 'WhiteNoLat', 'year', 'scenario']])
death_rates = death_rates.groupby(['scenario','year']).sum().reset_index()
death_rates['Asianrate'] = death_rates['Asiandeath']/death_rates['Asian']
death_rates['Blackrate'] = death_rates['Blackdeath']/death_rates['Black']
death_rates['Latinorate'] = death_rates['Latinodeat']/death_rates['Latino']
death_rates['Nativerate'] = death_rates['Nativedeat']/death_rates['Native']
death_rates['WhiteNoLatrate'] = death_rates['WhiteNoL_1']/death_rates['WhiteNoLat']



for scenario in scenario_dictionary:
    print('deathrates: '+scenario)
    plt.figure(figsize=(10, 6))

    deaths_temp = death_rates[death_rates['scenario']==scenario]
    # Plot mortality rates
    plt.plot(deaths_temp['year'], deaths_temp['Latinorate'], marker='o', label='Latino Death Rate')
    plt.plot(deaths_temp['year'], deaths_temp['WhiteNoLatrate'], marker='o', label='White/Non-hispanic Death Rate')
    plt.plot(deaths_temp['year'], deaths_temp['Blackrate'], marker='o', label='Black Death Rate')
    plt.plot(deaths_temp['year'], deaths_temp['Asianrate'], marker='o', label='Asian Death Rate')
    plt.plot(deaths_temp['year'], deaths_temp['Nativerate'], marker='o', label='Native Death Rate')

    # Add labels and title
    plt.xlabel('Year', fontsize=16)
    plt.ylabel('Death Rate', fontsize=16)
    plt.title('Death Rate Attributable to PM2.5 by Racial Group', fontsize=20)
    plt.legend(fontsize=14)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)

    # Show plot
    plt.grid(True)
    plt.savefig('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/ISRM_deathrate_by_group.jpg', format='jpg',dpi=300, bbox_inches='tight')
    plt.savefig('MIP_results_comparison/'+scenario+'/AirPollution/ISRM_deathrate_by_group.jpg', format='jpg',
                dpi=300, bbox_inches='tight')


#%%
## plot death rates across scenario
for file, year in year_inputs.items():
    
    deaths_temp = death_rates[death_rates['year']==year]

    if year==2027:
        cut = deaths_temp[['Asianrate', 'Blackrate', 'Latinorate', 'WhiteNoLatrate', 'Nativerate']].max().max()
        cut = cut*1.06


    bar_width = 0.7
    space_between_groups= 5
    index = np.arange(len(deaths_temp)) * (bar_width + space_between_groups)
    plt.figure(figsize=(12, 6))

    plt.bar(index, deaths_temp['Asianrate'], bar_width, label='Asian Death Rate', color='blue', alpha=0.7)
    plt.bar(index + bar_width, deaths_temp['Blackrate'], bar_width, label='Black Death Rate', color='green', alpha=0.7)
    plt.bar(index + 2*bar_width, deaths_temp['Latinorate'], bar_width, label='Latino Death Rate', color='red', alpha=0.7)
    plt.bar(index + 3*bar_width, deaths_temp['WhiteNoLatrate'], bar_width, label='White Death Rate', color='yellow', alpha=0.7)
    plt.bar(index + 4*bar_width, deaths_temp['Nativerate'], bar_width, label='Native Death Rate', color='purple', alpha=0.7)
    
    plt.ylim(0, cut)


    plt.title('Death Rates by Scenario', fontsize=24)
    plt.xlabel('Scenario', fontsize=19)
    plt.ylabel('Death Rate', fontsize=19)
    plt.xticks(index + 4*bar_width/2, deaths_temp.scenario, fontsize=11, rotation=-25, ha='left')
    plt.legend(fontsize=11)
    plt.yticks(fontsize=11)



    plt.savefig('MIP_AirPollution/Figures/Output/ISRM_deathrate_by_scenario_'+f"{year}"+'.jpg', format='jpg',dpi=300, bbox_inches='tight')
    plt.savefig('MIP_results_comparison/AirPollution/ISRM_deathrate_by_scenario_'+f"{year}"+'.jpg', format='jpg',
                dpi=300, bbox_inches='tight')

# %%
df_long = death_rates.melt(
    id_vars=['year', 'scenario'],
    value_vars=['WhiteNoLatrate', 'Nativerate', 'Latinorate', 'Blackrate', 'Asianrate'],
    var_name='Race',
    value_name='Rate'
)

# Create the plot
plt.figure(figsize=(12, 6))
sns.lineplot(
    data=df_long,
    x='year',
    y='Rate',
    hue='Race',     
    style='scenario',  
    markers=True,
    dashes=False
)

plt.title('Death Rates Across Time by Race and Scenario', fontsize=14)
plt.xlabel('Year', fontsize=12)
plt.ylabel('Death Rate', fontsize=12)
plt.legend(title='Race / Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

plt.savefig('MIP_AirPollution/Figures/Output/ISRM_deathrate_by_scenario_by_year.jpg', format='jpg',dpi=300, bbox_inches='tight')
plt.savefig('MIP_results_comparison/AirPollution/ISRM_deathrate_by_scenario_by_year.jpg', format='jpg',
            dpi=300, bbox_inches='tight')

###
#Filter out a few scenarios

# Create the plot
plt.figure(figsize=(12, 6))
sns.lineplot(
    data=df_long[df_long['scenario'].isin(['full-current-policies', 'full-base-200'])],
    x='year',
    y='Rate',
    hue='Race',     
    style='scenario',  
    markers=True,
    dashes=False
)

plt.title('Death Rates Across Time by Race and Scenario', fontsize=14)
plt.xlabel('Year', fontsize=12)
plt.ylabel('Death Rate', fontsize=12)
plt.legend(title='Race / Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.show()

plt.savefig('MIP_AirPollution/Figures/Output/ISRM_deathrate_by_scenario_by_year_selectedscenarios.jpg', format='jpg',dpi=300, bbox_inches='tight')
plt.savefig('MIP_results_comparison/AirPollution/ISRM_deathrate_by_scenario_by_year_selectedscenarios.jpg', format='jpg',
            dpi=300, bbox_inches='tight')