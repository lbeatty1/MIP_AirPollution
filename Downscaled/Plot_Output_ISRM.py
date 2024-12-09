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
import sys


os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')
sys.path.append(os.path.abspath('C:/Users/laure/Documents/Switch-USA-PG/'))

from MIP_AirPollution.Downscaled.settings import *

#rather than read in all data (very time consuming)
#I'm going to selectively plot model/scenarios
#I'll keep them in a data dictionary so I don't need to repeatedly read them in
data_dict = {}

#read in states
states = gpd.read_file('Data/tl_2022_us_state/tl_2022_us_state.shp')
states = states[~states['STUSPS'].isin(['AS', 'AK', 'GU', 'MP', 'VI', 'HI', 'PR'])]

#keep palette consistent across plots
palette = sns.color_palette("bright")
color_mapping = {
    'Latino': palette[0],       # Red
    'WhiteNoL_1': palette[1],  # Blue
    'Black': palette[2],       # Green
    'Asian': palette[3],       # Purple
    'Native': palette[4]       # Orange
}

## Read in data
def read_scenario_data(scenario, model, states_gdf):
    result = pd.DataFrame()
    print(f'reading in {scenario}, {model}')
    for file,year in year_inputs.items():
        if not os.path.exists('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/ISRM_result_'+f"{year}"+'.shp'):
            print(f"'{scenario}' emissions output doesn't exist... skipping...")
            continue
        temp = gpd.read_file('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/ISRM_result_'+f"{year}"+'.shp')
        temp['year']=year
        temp['scenario']=scenario
        temp['model']=model
        result = pd.concat([result, temp])

        #make file directories
        if not os.path.exists(f'MIP_AirPollution/Figures/Output/{scenario}/{model}'):
            os.makedirs(f'MIP_AirPollution/Figures/Output/{scenario}/{model}')

        if not os.path.exists(f'MIP_results_comparison/AirPollution/{scenario}/{model}'):
            os.makedirs(f'MIP_results_comparison/AirPollution/{scenario}/{model}')
    
    if result.empty:
        return(result)
        
    result = find_intersection_with_states(result, states_gdf)
    return(result)

def find_intersection_with_states(input_gdf, states_gfd):
    print("Finding intersection with land...")
    states_gfd = states_gfd.to_crs(input_gdf.crs)
    
    # Find intersections
    intersects = input_gdf.geometry.intersects(states_gfd.unary_union)
    input_gdf['intersects'] = intersects
    filtered_gdf = input_gdf[input_gdf['intersects'] == True]
    filtered_gdf = filtered_gdf.drop(columns=['intersects'])
    
    return filtered_gdf

#%%
# #Make concentration plots
def make_concentration_plots(models, scenarios, columns, states):
    print('making concentration plots')
    for model in models:
        for scenario in scenarios:
            quant_dict= {}
            key = f'{model}_{scenario}'
            if key in data_dict:
                plot_data = data_dict[key]
            else:
                data_dict[key]=read_scenario_data(scenario, model, states)
                plot_data = data_dict[key]

            for file,year in year_inputs.items():
                plot_temp = plot_data[plot_data['year']==year]
                for column in columns_to_plot:

                    #want scales to be the same for each plot
                    if year==2027:
                        print("Defining scale")
                        q = 0.99  # Truncate results at the 99th percentile for better visualization
                        cut = np.quantile(plot_temp[column], q)
                        quant_dict[column]=cut

                    fig, ax = plt.subplots(figsize=(10, 8))

                    # Plot data with color scale truncated at the specified quantile
                    plot_temp.plot(vmin=0, vmax=cut, cmap="OrRd", column=column, ax=ax)

                    # Plot states boundaries
                    states = states.to_crs(plot_temp.crs)
                    states.boundary.plot(ax=ax, color='black', linewidth=0.2)

                    # Add color bar
                    sm = plt.cm.ScalarMappable(cmap='OrRd', norm=plt.Normalize(vmin=0, vmax=quant_dict[column]))
                    sm._A = []  # Fake empty array for the colorbar
                    cbar = fig.colorbar(sm, fraction=0.03)  
                    cbar.set_label(column+' concentration (μg m$^{-3}$)', fontsize=18)  # Set color bar label
                    cbar.ax.tick_params(labelsize=14)

                    plt.axis('off')
                    plt.savefig(f'MIP_AirPollution/Figures/Output/{scenario}/{model}/ISRM_{year}_{column}_concentrationmap.jpg', format='jpg',
                                dpi=300, bbox_inches='tight')
                    plt.savefig(f'MIP_results_comparison/AirPollution/{scenario}/{model}/ISRM_{year}_{column}_{model}_concentrationmap.jpg', format='jpg',
                                dpi=300, bbox_inches='tight')


columns_to_plot = ['TotalPM25']
models = ['GenX', 'SWITCH']
scenarios = ['full-base-200', 'full-base-50', 'full-base-1000']
make_concentration_plots(models = models, scenarios=scenarios, states=states)

#%%
def make_death_timeseries(models, scenarios):
    print('making death over time plots')

    for model in models:
        for scenario in scenarios:
            key = f'{model}_{scenario}'
            if key in data_dict:
                plot_data = data_dict[key]
                print(f'{key} already in memory')
            else:
                data_dict[key]=read_scenario_data(scenario, model, states)
                plot_data = data_dict[key]
                
            deaths = pd.DataFrame(plot_data[['Asiandeath', 'Blackdeath', 'Latinodeat', 'Nativedeat', 'WhiteNoL_1', 'year', 'scenario', 'model']])
            deaths = deaths.groupby(['scenario','model', 'year']).sum().reset_index()

            plt.figure(figsize=(10, 6))
            print('deaths: '+scenario)

            # Plot mortality rates
            plt.plot(deaths['year'], deaths['Latinodeat'], marker='o', label='Latino Deaths', color=color_mapping['Latino'])
            plt.plot(deaths['year'], deaths['WhiteNoL_1'], marker='o', label='White/Non-hispanic Deaths', color=color_mapping['WhiteNoL_1'])
            plt.plot(deaths['year'], deaths['Blackdeath'], marker='o', label='Black Deaths', color=color_mapping['Black'])
            plt.plot(deaths['year'], deaths['Asiandeath'], marker='o', label='Asian Deaths', color=color_mapping['Asian'])

            # Add labels and title
            plt.xlabel('Year', fontsize=16)
            plt.ylabel('Total Deaths', fontsize=16)
            plt.title('Deaths Attributable to PM2.5 by Racial Group', fontsize=20)
            plt.legend(fontsize=14)

            plt.xticks(fontsize=12)
            plt.yticks(fontsize=12)

            # Show plot
            plt.grid(True)
            plt.savefig(f'MIP_AirPollution/Figures/Output/{scenario}/{model}/ISRM_death_by_group.jpg', format='jpg',dpi=300, bbox_inches='tight')
            plt.savefig(f'MIP_results_comparison/AirPollution/{scenario}/{model}/ISRM_death_by_group.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')
            

            death_rates = pd.DataFrame(plot_data[['Asiandeath', 'Blackdeath', 'Latinodeat', 'Nativedeat', 'WhiteNoL_1', 'Asian', 'Black', 'Latino', 'Native', 'WhiteNoLat', 'year', 'scenario', 'model']])
            death_rates = death_rates.groupby(['scenario','year', 'model']).sum().reset_index()
            death_rates['Asianrate'] = death_rates['Asiandeath']/death_rates['Asian']
            death_rates['Blackrate'] = death_rates['Blackdeath']/death_rates['Black']
            death_rates['Latinorate'] = death_rates['Latinodeat']/death_rates['Latino']
            death_rates['Nativerate'] = death_rates['Nativedeat']/death_rates['Native']
            death_rates['WhiteNoLatrate'] = death_rates['WhiteNoL_1']/death_rates['WhiteNoLat']


            print('deathrates: '+scenario)
            plt.figure(figsize=(10, 6))

            # Plot mortality rates
            plt.plot(death_rates['year'], death_rates['Latinorate'], marker='o', label='Latino Death Rate')
            plt.plot(death_rates['year'], death_rates['WhiteNoLatrate'], marker='o', label='White/Non-hispanic Death Rate')
            plt.plot(death_rates['year'], death_rates['Blackrate'], marker='o', label='Black Death Rate')
            plt.plot(death_rates['year'], death_rates['Asianrate'], marker='o', label='Asian Death Rate')
            plt.plot(death_rates['year'], death_rates['Nativerate'], marker='o', label='Native Death Rate')

            # Add labels and title
            plt.xlabel('Year', fontsize=16)
            plt.ylabel('Death Rate', fontsize=16)
            plt.title('Death Rate Attributable to PM2.5 by Racial Group', fontsize=20)
            plt.legend(fontsize=14)
            plt.xticks(fontsize=12)
            plt.yticks(fontsize=12)

            # Show plot
            plt.grid(True)
            plt.savefig(f'MIP_AirPollution/Figures/Output/{scenario}/{model}/ISRM_deathrate_by_group.jpg', format='jpg',dpi=300, bbox_inches='tight')
            plt.savefig(f'MIP_results_comparison/AirPollution/{scenario}/{model}/ISRM_deathrate_by_group.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')


models = ['GenX', 'SWITCH']
scenarios = ['full-base-200', 'full-current-policies']
make_death_timeseries(models, scenarios)

#%%
## plot death rates across scenario
def compare_death_scenarios(models, scenarios, scenario_comparison_name):
    #models should be list of models
    #scenarios should be list of scenarios
    #scenario_comparison_name should be a short description of scenarios that are being compared -- eg. transmission_constraint
    print('making death across scenario figures')
    for model in models:
        #read in data
        scenarios_compare = pd.DataFrame()
        scenarios_name = '_'.join(scenarios)
        for scenario in scenarios:
            key = f'{model}_{scenario}'
            if key in data_dict:
                plot_data = data_dict[key]
                print(f'{key} already in memory')
            else:
                data_dict[key]=read_scenario_data(scenario, model, states)
                plot_data = data_dict[key]
            scenarios_compare = pd.concat([scenarios_compare, plot_data])
            
        scenarios_compare = scenarios_compare.groupby(['scenario','year', 'model']).sum().reset_index()
        scenarios_compare['Asianrate'] = scenarios_compare['Asiandeath']/scenarios_compare['Asian']*1e6
        scenarios_compare['Blackrate'] = scenarios_compare['Blackdeath']/scenarios_compare['Black']*1e6
        scenarios_compare['Latinorate'] = scenarios_compare['Latinodeat']/scenarios_compare['Latino']*1e6
        scenarios_compare['Nativerate'] = scenarios_compare['Nativedeat']/scenarios_compare['Native']*1e6
        scenarios_compare['WhiteNoLatrate'] = scenarios_compare['WhiteNoL_1']/scenarios_compare['WhiteNoLat']*1e6

        #first make plot over time
        columns = ['Asianrate', 'Blackrate', 'Latinorate', 'Nativerate', 'WhiteNoLatrate']
        melted = scenarios_compare.melt(
            id_vars=['year', 'scenario'], 
            value_vars=columns,
            var_name='Race', 
            value_name='Rate'
        )
        scenarios_shapes = {scenario: marker for scenario, marker in zip(melted['scenario'].unique(), ['o', 's', 'D', '^', 'v'])}

        # Create the plot
        plt.figure(figsize=(12, 8))

        # Plot the lines
        sns.lineplot(
            data=melted,
            x='year',
            y='Rate',
            hue='Race',
            style='scenario',  # Lines don't depend on scenario
            linewidth=2,
            alpha=0.8
        )

        # Add labels and title
        plt.title('Death Rates by Race and Scenario Over Time', fontsize=16)
        plt.xlabel('Year', fontsize=14)
        plt.ylabel('Death Rate (per million)', fontsize=14)
        plt.legend(title='Race/Scenario', fontsize=12)
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)

        # Show the plot
        plt.tight_layout()
        plt.savefig(f'MIP_AirPollution/Figures/Output/Compare_scenarios_{scenario_comparison_name}_{model}.jpg', format='jpg',dpi=300, bbox_inches='tight')
        plt.savefig(f'MIP_results_comparison/AirPollution/Compare_scenarios_{scenario_comparison_name}_{model}.jpg', format='jpg',
                    dpi=300, bbox_inches='tight')

        for file, year in year_inputs.items():
            
            deaths_temp = scenarios_compare[scenarios_compare['year']==year]

            #makes scenarios appear in order specified above
            deaths_temp['scenario'] = pd.Categorical(
                deaths_temp['scenario'],
                categories = scenarios,
                ordered=True
            )
            deaths_temp = deaths_temp.sort_values('scenario')

            #keeps scale consistent across years
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
            plt.ylabel('Death Rate (per million)', fontsize=19)
            plt.xticks(index + 4*bar_width/2, deaths_temp.scenario, fontsize=11, rotation=-25, ha='left')
            plt.legend(fontsize=11)
            plt.yticks(fontsize=11)



            plt.savefig(f'MIP_AirPollution/Figures/Output/Compare_scenarios_{scenario_comparison_name}_{year}_{model}.jpg', format='jpg',dpi=300, bbox_inches='tight')
            plt.savefig(f'MIP_results_comparison/AirPollution/Compare_scenarios_{scenario_comparison_name}_{year}_{model}.jpg', format='jpg',
                        dpi=300, bbox_inches='tight')

models = ['GenX']
scenarios = ['full-base-50', 'full-base-200', 'full-base-1000']
compare_death_scenarios(models, scenarios, 'compare-escape-price')

scenarios = ['full-base-200', 'full-current-policies']
compare_death_scenarios(models, scenarios, 'current-base')

scenarios = ['full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx-50', 'full-base-200']
compare_death_scenarios(models, scenarios, 'transmissions-constraint')

scenarios = ['full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx-50', 'full-base-200', 'full-base-50', 'full-base-1000', 'full-current-policies']
compare_death_scenarios(models, scenarios, 'all-scenarios')
#%%
#Compare across models
scenarios = ['full-current-policies', 'full-base-200']
models = ['GenX', 'USENSYS', 'SWITCH', 'TEMOA']  
races = ['Asianrate', 'Blackrate', 'Latinorate', 'WhiteNoLatrate', 'Nativerate']

bar_width = 0.7
space_between_groups = 5

for scenario in scenarios:
    
    models_compare = pd.DataFrame()
    for model in models:
        #read in data
        key = f'{model}_{scenario}'
        if key in data_dict:
            plot_data = data_dict[key]
            print(f'{key} already in memory')
        else:
            data_dict[key]=read_scenario_data(scenario, model, states)
            plot_data = data_dict[key]
        models_compare = pd.concat([models_compare, plot_data])
    models_compare = models_compare.groupby(['scenario','year', 'model']).sum().reset_index()
    models_compare['Asianrate'] = models_compare['Asiandeath']/models_compare['Asian']*1e6
    models_compare['Blackrate'] = models_compare['Blackdeath']/models_compare['Black']*1e6
    models_compare['Latinorate'] = models_compare['Latinodeat']/models_compare['Latino']*1e6
    models_compare['Nativerate'] = models_compare['Nativedeat']/models_compare['Native']*1e6
    models_compare['WhiteNoLatrate'] = models_compare['WhiteNoL_1']/models_compare['WhiteNoLat']*1e6


    for file, year in year_inputs.items():

        deaths_temp = models_compare[models_compare['year'] == year]

        # Group by race
        index = np.arange(len(races)) * (bar_width + space_between_groups)
        plt.figure(figsize=(12, 6))

        # Plot bars for each model within each race group
        for i, model in enumerate(models):
            offset = i * bar_width  # Shift bars for each model
            model_data = deaths_temp[deaths_temp['model'] == model]

            # Aggregate data across rows (mean or sum if multiple entries exist)
            if len(model_data) > 1:
                race_values = model_data[races].mean(axis=0)  # Take mean across rows
            else:
                race_values = model_data[races].iloc[0]  # Single row, take values directly

            plt.bar(index + offset, race_values, bar_width, label=model, alpha=0.7)

        # Add labels and formatting
        plt.title(f'Death Rates by Race for {scenario_dictionary[scenario]}: {year}', fontsize=24)
        plt.xlabel('Race', fontsize=19)
        plt.ylabel('Death Rate (per million)', fontsize=19)
        plt.xticks(index + bar_width * (len(models) - 1) / 2, ['Asian', 'Black', 'Hispanic/Latino', 'White Non-Hispanic', 'Native American'], fontsize=11, rotation=-25, ha='left')
        plt.legend(title="Model", fontsize=11)
        plt.yticks(fontsize=11)
        
        plt.savefig(f'MIP_AirPollution/Figures/Output/DeathRate_Across_Models_{scenario_dictionary[scenario]}_{year}.png', format='jpg',dpi=300, bbox_inches='tight')
        plt.savefig(f'MIP_AirPollution/Figures/Output/DeathRate_Across_Models_{scenario_dictionary[scenario]}_{year}.png', format='jpg',
                    dpi=300, bbox_inches='tight')



#%%
#######################################
#### COMPARE WITH CO2 EMISSIONS #######
#######################################
models=['GenX']
scenarios = ['full-base-50', 'full-base-200', 'full-base-1000','full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx50', 'full-current-policies', 'full-base-200-commit', 'full-current-policies-retire', 'full-current-policies-commit']
emissions = pd.read_csv('MIP_results_comparison/compiled_results/all/emissions.csv')
emissions = emissions.groupby(['model', 'planning_year', 'case']).agg({'value':'sum'}).reset_index()

for model in models:
    #read in data
    scenarios_compare = pd.DataFrame()
    scenarios_name = '_'.join(scenarios)
    for scenario in scenarios:
        key = f'{model}_{scenario}'
        if key in data_dict:
            plot_data = data_dict[key]
            print(f'{key} already in memory')
        else:
            data_dict[key]=read_scenario_data(scenario, model, states)
            plot_data = data_dict[key]
        scenarios_compare = pd.concat([scenarios_compare, plot_data])
        
    scenarios_compare = scenarios_compare.groupby(['scenario','year', 'model']).sum().reset_index()
    scenarios_compare['Asianrate'] = scenarios_compare['Asiandeath']/scenarios_compare['Asian']*1e6
    scenarios_compare['Blackrate'] = scenarios_compare['Blackdeath']/scenarios_compare['Black']*1e6
    scenarios_compare['Latinorate'] = scenarios_compare['Latinodeat']/scenarios_compare['Latino']*1e6
    scenarios_compare['Nativerate'] = scenarios_compare['Nativedeat']/scenarios_compare['Native']*1e6
    scenarios_compare['WhiteNoLatrate'] = scenarios_compare['WhiteNoL_1']/scenarios_compare['WhiteNoLat']*1e6


emissions = pd.merge(emissions, scenarios_compare, how='left', left_on=['model', 'planning_year', 'case'], right_on=['model', 'year', 'scenario'])
emissions['value'] = emissions['value']/1e8

sns.scatterplot(
    data=emissions, 
    x='value', 
    y='deathsK', 
    hue='scenario', 
    style = 'planning_year',
    palette='bright',
    alpha=0.9
)

# Add labels and title
plt.title('CO2 Emissions vs Deaths', fontsize=16)
plt.xlabel('CO2 Emissions (100 million Tons)', fontsize=14)
plt.ylabel('Deaths per year', fontsize=14)

plt.legend(
    bbox_to_anchor=(1.05, 1),  
    loc='upper left',          
    borderaxespad=0.0          
)
# Show the plot
plt.savefig(f'MIP_AirPollution/Figures/Output/Deaths_vs_Emissions_{model}.png', format='jpg',dpi=300, bbox_inches='tight')
plt.savefig(f'MIP_AirPollution/Figures/Output/Deaths_vs_Emissions_{model}.png', format='jpg',
            dpi=300, bbox_inches='tight')
plt.close()

# Sort data by scenario and planning_year for proper line connections
emissions = emissions.sort_values(by=['scenario', 'planning_year'])
lines = []
for scenario, group in emissions.groupby('scenario'):
    group = group.sort_values(by='planning_year')
    for i in range(len(group) - 1):
        lines.append({
            'x_start': group.iloc[i]['value'],
            'y_start': group.iloc[i]['deathsK'],
            'x_end': group.iloc[i + 1]['value'],
            'y_end': group.iloc[i + 1]['deathsK'],
            'scenario': scenario
        })

        plt.figure(figsize=(10, 6))
lines_df = pd.DataFrame(lines)

# Overlay lines for adjacent points
for _, row in lines_df.iterrows():
    plt.plot(
        [row['x_start'], row['x_end']],
        [row['y_start'], row['y_end']],
        color=sns.color_palette('bright')[list(emissions['scenario'].unique()).index(row['scenario'])],
        alpha=0.6
    )

# Add scatter points
sns.scatterplot(
    data=emissions,
    x='value',
    y='deathsK',
    hue='scenario',
    style='planning_year',
    palette='bright',
    s=100,  # Size of points
    alpha=0.9
)

# Add labels and title
plt.title('CO2 Emissions vs Deaths', fontsize=16)
plt.xlabel('CO2 Emissions (100 million Tons)', fontsize=14)
plt.ylabel('Deaths per year', fontsize=14)

# Customize the legend
plt.legend(
    title='Scenario',
    bbox_to_anchor=(1.05, 1),
    loc='upper left',
    borderaxespad=0.0
)

# Tidy up the layout
plt.tight_layout()

# Show the plot
plt.savefig(f'MIP_AirPollution/Figures/Output/Deaths_vs_Emissions_withlines_{model}.png', format='jpg',dpi=300, bbox_inches='tight')
plt.savefig(f'MIP_AirPollution/Figures/Output/Deaths_vs_Emissions_withlines_{model}.png', format='jpg',
            dpi=300, bbox_inches='tight')
plt.close()

#%%
#######################################
###### COMPARE WITH COSTS #############
#######################################

models=['GenX']
scenarios = ['full-base-50', 'full-base-200', 'full-base-1000','full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx50', 'full-current-policies', 'full-base-200-commit', 'full-current-policies-retire', 'full-current-policies-commit']
costs = pd.read_csv('MIP_results_comparison/compiled_results/all/operational_costs.csv')
costs = costs.groupby(['model', 'planning_year', 'case']).agg({'Total':'sum'}).reset_index()
costs = costs[costs['planning_year']=='NPV']
costs['Total'] = costs['Total']/1e9
for model in models:
    #read in data
    scenarios_compare = pd.DataFrame()
    scenarios_name = '_'.join(scenarios)
    for scenario in scenarios:
        key = f'{model}_{scenario}'
        if key in data_dict:
            plot_data = data_dict[key]
            print(f'{key} already in memory')
        else:
            data_dict[key]=read_scenario_data(scenario, model, states)
            plot_data = data_dict[key]
        scenarios_compare = pd.concat([scenarios_compare, plot_data])
        
    scenarios_compare = scenarios_compare.groupby(['scenario', 'model']).sum().reset_index()
    scenarios_compare['Asianrate'] = scenarios_compare['Asiandeath']/scenarios_compare['Asian']*1e6
    scenarios_compare['Blackrate'] = scenarios_compare['Blackdeath']/scenarios_compare['Black']*1e6
    scenarios_compare['Latinorate'] = scenarios_compare['Latinodeat']/scenarios_compare['Latino']*1e6
    scenarios_compare['Nativerate'] = scenarios_compare['Nativedeat']/scenarios_compare['Native']*1e6
    scenarios_compare['WhiteNoLatrate'] = scenarios_compare['WhiteNoL_1']/scenarios_compare['WhiteNoLat']*1e6


costs = pd.merge(costs, scenarios_compare, how='left', left_on=['model', 'case'], right_on=['model', 'scenario'])
costs['Total'] = costs['Total']
costs['deathsK'] = costs['deathsK']/6 #average deaths per planning period
sns.scatterplot(
    data=costs, 
    x='Total', 
    y='deathsK', 
    hue='scenario', 
    palette='bright',
    alpha=0.9
)

# Add labels and title
plt.title('Total Costs vs Deaths', fontsize=16)
plt.xlabel('Total Costs (Billion $)', fontsize=14)
plt.ylabel('Average Deaths per year', fontsize=14)
plt.legend(title='Planning Year')

# Show the plot
plt.tight_layout()
plt.savefig(f'MIP_AirPollution/Figures/Output/Deaths_vs_Costs_{model}.png', format='jpg',dpi=300, bbox_inches='tight')
plt.savefig(f'MIP_AirPollution/Figures/Output/Deaths_vs_Costs_{model}.png', format='jpg',
            dpi=300, bbox_inches='tight')

# %%
#########################
### Break down costs
#########################
model='GenX'
scenarios = ['full-base-50', 'full-base-200', 'full-base-1000','full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx50', 'full-current-policies', 'full-current-policies-retire', 'full-current-policies-commit']
costs = pd.read_csv('MIP_results_comparison/compiled_results/all/operational_costs.csv')
costs = costs[costs['planning_year']=='NPV']
costs = costs[costs['case'].isin(scenarios)]
costs = costs[costs['model']==model]
#read in data
scenarios_compare = pd.DataFrame()
scenarios_name = '_'.join(scenarios)
for scenario in scenarios:
    key = f'{model}_{scenario}'
    if key in data_dict:
        plot_data = data_dict[key]
        print(f'{key} already in memory')
    else:
        data_dict[key]=read_scenario_data(scenario, model, states)
        plot_data = data_dict[key]
    scenarios_compare = pd.concat([scenarios_compare, plot_data])
scenarios_compare = scenarios_compare.groupby(['scenario', 'model', 'year']).sum().reset_index()
    
scenarios_compare['Total']=scenarios_compare['deathsK']*11.51*1e6 #VSL
scenarios_compare['Costs'] = 'Deaths'
scenarios_compare['case']=scenarios_compare['scenario']
scenarios_compare['Total'] = np.where(scenarios_compare['year'] == 2027, scenarios_compare['Total'] * 3, scenarios_compare['Total'] * 5)
scenarios_compare = scenarios_compare.groupby(['Costs', 'case']).agg({'Total':'sum'}).reset_index()
costs = pd.concat([costs, scenarios_compare])

costs = costs[['Costs', 'Total', 'case']]
costs['Total']=costs['Total']/1e9


#simplify and control order of bars
other_costs = ['cNSE', 'cNetworkExp', 'cStart', 'cUnmetRsv', 'cVOM']
costs['Costs'] = np.where(costs['Costs'].isin(other_costs), 'Other', costs['Costs'])

costs['Costs'] = pd.Categorical(costs['Costs'], categories=['Deaths','cCO2', 'cFix','cVar', 'Other'], ordered=True)
costs = costs.groupby(['case', 'Costs']).agg({'Total':'sum'}).reset_index()
costs = costs.sort_values(by=['case', 'Costs'])


pivot_df = costs.pivot_table(index='case', columns='Costs', values='Total', aggfunc='sum', fill_value=0)
column_order = ['cCO2', 'cFix', 'cVar', 'Other', 'Deaths']  # Adjust this order as needed
pivot_df = pivot_df[column_order]
# Plotting the stacked bar chart
pivot_df.plot(kind='bar', stacked=True, figsize=(10, 6))

ax = pivot_df.plot(kind='bar', stacked=True, figsize=(10, 6))

handles, labels = ax.get_legend_handles_labels()
order = list(reversed(column_order))  # Reverse the order
  # Ensure this matches your column_order
sorted_handles_labels = sorted(zip(handles, labels), key=lambda x: order.index(x[1]))
sorted_handles, sorted_labels = zip(*sorted_handles_labels)
ax.legend(sorted_handles, sorted_labels, title="Costs")

# Adding labels and title
plt.title('Costs by Case')
plt.xlabel('Case')
plt.ylabel('Costs (Billion $)')

# Show the plot
plt.tight_layout()
plt.savefig(f'MIP_AirPollution/Figures/Output/Costs_Barchart_{model}.png', format='jpg',dpi=300, bbox_inches='tight')
plt.savefig(f'MIP_AirPollution/Figures/Output/Costs_Barchart_{model}.png', format='jpg',
            dpi=300, bbox_inches='tight')
# %%
