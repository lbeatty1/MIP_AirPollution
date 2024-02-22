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

model='GenX'


#%%
## Read in all data
emissions = pd.DataFrame()
scenarios = ['26z-short-base-50', '26z-short-current-policies', '26z-short-base-200', '26z-short-no-ccs']
scenarios=['26z-short-base-50', '26z-short-current-policies', '26z-short-base-200']
years = ['2020', '2030']
for scenario in scenarios:
    print('reading: '+scenario)
    for year in years:
        temp = gpd.read_file('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/ISRM_result_'+year+'.shp')
        temp['year']=year
        temp['scenario']=scenario
        emissions = pd.concat([emissions, temp])
        print(year)

#make file directories
for scenario in scenarios:
    if not os.path.exists('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/'):
        os.makedirs('MIP_AirPollution/Figures/Output/' + scenario + '/' + model )

    if not os.path.exists('MIP_results_comparison/'+scenario+'/AirPollution/'):
        os.makedirs('MIP_results_comparison/'+scenario+'/AirPollution')

#Plot output -- map of concentrations
#read in states
states = gpd.read_file('tl_2022_us_state/tl_2022_us_state.shp')
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

print('making concentration plots')
for scenario in scenarios:
    for year in years:
        print('deaths: '+scenario+year)

        emissions_temp = emissions[emissions['year']==year]
        emissions_temp = emissions_temp[emissions_temp['scenario']==scenario]
        for column in columns_to_plot:

            #want scales to be the same for each plot
            if year=='2020':
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
            cbar.set_label(column+' concentration (μg m$^{-3}$)')  # Set color bar label

            plt.axis('off')
            plt.savefig('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/ISRM_' +year+'_'+ column + '_concentrationmap.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')
            plt.savefig('MIP_results_comparison/'+scenario+'/AirPollution/ISRM_'+year+'_'+ column + '_concentrationmap.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')

print('making death plots')
deaths = pd.DataFrame(emissions[['Asiandeath', 'Blackdeath', 'Latinodeat', 'Nativedeat', 'WhiteNoL_1', 'year', 'scenario']])
deaths = deaths.groupby(['scenario','year']).sum().reset_index()

for scenario in scenarios:
    plt.figure(figsize=(10, 6))
    print('deaths: '+scenario)

    deaths_temp = deaths[deaths['scenario']==scenario]
    # Plot mortality rates
    plt.plot(deaths_temp['year'], deaths_temp['Latinodeat'], marker='o', label='Latino Deaths')
    plt.plot(deaths_temp['year'], deaths_temp['WhiteNoL_1'], marker='o', label='White/Non-hispanic Deaths')
    plt.plot(deaths_temp['year'], deaths_temp['Blackdeath'], marker='o', label='Black Deaths')
    plt.plot(deaths_temp['year'], deaths_temp['Asiandeath'], marker='o', label='Asian Deaths')

    # Add labels and title
    plt.xlabel('Year')
    plt.ylabel('Total Deaths')
    plt.title('Deaths Attributable to PM2.5 by Racial Group')
    plt.legend()

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



for scenario in scenarios:
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
    plt.xlabel('Year')
    plt.ylabel('Death Rate')
    plt.title('Death Rate Attributable to PM2.5 by Racial Group')
    plt.legend()

    # Show plot
    plt.grid(True)
    plt.savefig('MIP_AirPollution/Figures/Output/' + scenario + '/' + model + '/ISRM_deathrate_by_group.jpg', format='jpg',dpi=300, bbox_inches='tight')
    plt.savefig('MIP_results_comparison/'+scenario+'/AirPollution/ISRM_deathrate_by_group.jpg', format='jpg',
                dpi=300, bbox_inches='tight')


## plot death rates across scenario
for year in years:
    
    deaths_temp = death_rates[death_rates['year']==year]

    bar_width = 0.35
    space_between_groups= 2
    index = np.arange(len(deaths_temp)) * (bar_width * 5 + space_between_groups)
    plt.figure(figsize=(10, 6))

    plt.bar(index, deaths_temp['Asianrate'], bar_width, label='Asian Death Rate', color='blue', alpha=0.7)
    plt.bar(index + bar_width, deaths_temp['Blackrate'], bar_width, label='Black Death Rate', color='green', alpha=0.7)
    plt.bar(index + 2*bar_width, deaths_temp['Latinorate'], bar_width, label='Latino Death Rate', color='red', alpha=0.7)
    plt.bar(index + 3*bar_width, deaths_temp['WhiteNoLatrate'], bar_width, label='White Death Rate', color='yellow', alpha=0.7)
    plt.bar(index + 4*bar_width, deaths_temp['Nativerate'], bar_width, label='Native Death Rate', color='purple', alpha=0.7)


    plt.title('Death Rates by Scenario')
    plt.xlabel('Scenario')
    plt.ylabel('Death Rate')
    plt.xticks(index + 4*bar_width/2, deaths_temp.scenario)
    plt.legend()

    plt.savefig('MIP_AirPollution/Figures/Output/ISRM_deathrate_by_scenario_'+year+'.jpg', format='jpg',dpi=300, bbox_inches='tight')

