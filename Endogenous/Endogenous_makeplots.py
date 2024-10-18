globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import ListedColormap



os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')

scenario = 'base_short'
years = [2027, 2030]
result_dir = f'switch/26-zone/out/foresight/'
cost_limits = [50,100,200]

#read in exposure coefs
coefs=pd.DataFrame()
for y in years:
    coefs = pd.concat([coefs,
                       pd.read_csv(
                           f"MIP_Air_OutData/Marginal_Coefficients/{scenario}_marginal_exposure_coefs_{y}.csv",
                           index_col=0)]
    )

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
        return 'other: biomass, petroleum liquids'
    elif 'petroleum' in row['Cluster']:
        return 'other: biomass, petroleum liquids'
    else:
        return np.nan

coefs['technology'] = coefs.apply(update_technology, axis=1)

summary=coefs.groupby(['technology', 'Race']).agg({'Exposure':'mean'}).reset_index()
print(summary)

emis = []
for year in years:
    shapefile_path = f'MIP_Air_OutData/MIP_Emissions/{scenario}_marginal_emissions_{y}.shp'

    gdf = gpd.read_file(shapefile_path)
    
    # Append the GeoDataFrame to the list
    emis.append(gdf)

emis = gpd.GeoDataFrame(pd.concat(emis, ignore_index=True))

# Optionally: Set a consistent CRS if they need to match
emis = pd.DataFrame(emis[['NOx', 'SOx', 'PM2_5', 'NH3', 'VOC', 'Resource']])

emis = emis.groupby(['Resource']).agg({'NOx':'sum', 'PM2_5':'sum', 'NH3':'sum', 'SOx':'sum', 'PM2_5':'sum', 'VOC':'sum'}).reset_index()

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

emis_summary = emis.groupby(['technology']).agg({'NOx':'mean', 'PM2_5':'mean', 'NH3':'mean', 'SOx':'mean', 'PM2_5':'mean', 'VOC':'mean'}).reset_index()

bar_width = 0.15  # Adjusted width to fit more bars
index = np.arange(len(emis_summary['technology']))
fig, ax = plt.subplots()

bar1 = ax.bar(index, emis_summary['PM2_5'], bar_width, label='PM2.5', color='b')
bar2 = ax.bar(index + bar_width, emis_summary['SOx'], bar_width, label='SOx', color='g')
bar3 = ax.bar(index + 2*bar_width, emis_summary['NOx'], bar_width, label='NOx', color='r')
bar4 = ax.bar(index + 3*bar_width, emis_summary['NH3'], bar_width, label='NH3', color='yellow')
bar5 = ax.bar(index + 4*bar_width, emis_summary['VOC'], bar_width, label='VOC', color='orange')  # Changed color to 'orange'

ax.set_xlabel('Technology')
ax.set_ylabel('Emissions')
ax.set_title('Emissions by Technology')
ax.set_xticks(index + 2*bar_width)  # Shift ticks to the middle of the grouped bars
ax.set_xticklabels(emis_summary['technology'])
ax.legend()

plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/emissions_by_technology.png', dpi=300, bbox_inches='tight')  # DPI for high resolution

#################################
## Now plot exposure coefficients
#################################
exposure_wide = summary.pivot(index='technology', columns='Race', values='Exposure').reset_index()

bar_width = 0.15 
index = np.arange(len(exposure_wide['technology']))
fig, ax = plt.subplots()

bar1 = ax.bar(index, exposure_wide['Asian'], bar_width, label='Asian', color='b')
bar2 = ax.bar(index + bar_width, exposure_wide['Black'], bar_width, label='Black', color='g')
bar3 = ax.bar(index + 2*bar_width, exposure_wide['Latino'], bar_width, label='Latino', color='r')
bar4 = ax.bar(index + 3*bar_width, exposure_wide['Native'], bar_width, label='Native Amer', color='yellow')
bar5 = ax.bar(index + 4*bar_width, exposure_wide['WhiteNoLat'], bar_width, label='White', color='orange')  # Changed color to 'orange'

ax.set_xlabel('Technology')
ax.set_ylabel('Marginal Exposure per MWh')
ax.set_title('Exposure by Technology')
ax.set_xticks(index + 2*bar_width)  # Shift ticks to the middle of the grouped bars
ax.set_xticklabels(exposure_wide['technology'])
ax.legend()

plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/exposure_by_technology.png', dpi=300, bbox_inches='tight')  # DPI for high resolution

####################33##########
## Plot Results --CAPACITY #####
#################################

#read in capacity results
capacity=pd.read_csv(f"{result_dir}{scenario}/gen_cap.csv",
                     index_col=0)
capacity['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/gen_cap.csv",
                         index_col=0)
    tempdat['scenario']=f'{scenario}_{c}'
    capacity = pd.concat([capacity,tempdat])

ipm_regions = gpd.read_file('Data/IPM_Regions/national_emm_boundaries.shp')
capacity_spatial = capacity.groupby(['gen_load_zone', 'PERIOD', 'scenario']).agg({'GenCapacity':'sum'}).reset_index()
ipm_regions = ipm_regions.merge(capacity_spatial, left_on='model_regi', right_on='gen_load_zone', how='left')

#plot capacity in each region relative to base scenario
for c in cost_limits:
    for y in years:
        base = ipm_regions[ipm_regions['scenario']==f'{scenario}']
        base = base[base['PERIOD']==y]
        base = pd.DataFrame(base[['model_regi', 'GenCapacity']])
        base.rename(columns={'GenCapacity': 'Base_GenCapacity'}, inplace=True)


        plotdata = ipm_regions[ipm_regions['scenario']==f'{scenario}_{c}']
        plotdata = plotdata[plotdata['PERIOD']==y]

        plotdata = plotdata.merge(base, on='model_regi', how='left')
        plotdata['GenDif'] = plotdata['GenCapacity']/plotdata['Base_GenCapacity']

        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        plotdata.plot(column='GenDif', 
                        ax=ax, 
                        legend=True, 
                        cmap='OrRd',
                        edgecolor='black')

        ax.set_title('Generation Capacity Relative to Base', fontsize=15)
        ax.set_axis_off() 

        plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/Generation_Capacity_Relative_{y}_{c}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution

capacity_spatial = capacity.groupby(['gen_load_zone', 'PERIOD', 'scenario', 'gen_energy_source']).agg({'GenCapacity':'sum'}).reset_index()
for tech in ['Wind', 'Solar', 'Naturalgas', 'Coal']:
    capacity_spatial_temp = capacity_spatial[capacity_spatial['gen_energy_source']==tech]
    capacity_spatial_temp = capacity_spatial_temp[['scenario', 'PERIOD', 'gen_load_zone', 'GenCapacity']]
    capacity_spatial_temp.rename(columns={'GenCapacity': f'GenCapacity_{tech}'}, inplace=True)

    ipm_regions = ipm_regions.merge(capacity_spatial_temp, left_on=['model_regi', 'PERIOD', 'scenario'], right_on=['gen_load_zone','PERIOD', 'scenario'], how='left')

    #plot capacity in each region relative to base scenario
    for c in cost_limits:
        for y in years:
            base = ipm_regions[ipm_regions['scenario']==f'{scenario}']
            base = base[base['PERIOD']==y]
            base = pd.DataFrame(base[['model_regi', f'GenCapacity_{tech}']])
            base.rename(columns={f'GenCapacity_{tech}': 'Base_GenCapacity'}, inplace=True)


            plotdata = ipm_regions[ipm_regions['scenario']==f'{scenario}_{c}']
            plotdata = plotdata[plotdata['PERIOD']==y]

            plotdata = plotdata.merge(base, on='model_regi', how='left')
            plotdata['GenDif'] = plotdata[f'GenCapacity_{tech}']/plotdata['Base_GenCapacity']

            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            plotdata.plot(column='GenDif', 
                            ax=ax, 
                            legend=True, 
                            cmap='OrRd',
                            edgecolor='black')

            # Optional: Customize the plot further
            ax.set_title('Generation Capacity Relative to Base', fontsize=15)
            ax.set_axis_off()  # Turn off the axis for a cleaner look

            # Show the plot
            plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/Generation_Capacity_Relative_{tech}_{y}_{c}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution


####################33##########
## Plot Results --GENERATION #####
#################################

#read in capacity results
dispatch=pd.read_csv(f"{result_dir}{scenario}/dispatch_gen_annual_summary.csv",
                     index_col=0)
dispatch['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/dispatch_gen_annual_summary.csv",
                         index_col=0)
    tempdat['scenario']=f'{scenario}_{c}'
    dispatch = pd.concat([dispatch,tempdat])

ipm_regions = gpd.read_file('Data/IPM_Regions/national_emm_boundaries.shp')
dispatch_spatial = dispatch.groupby(['gen_load_zone', 'period', 'scenario']).agg({'Energy_GWh_typical_yr':'sum'}).reset_index()
ipm_regions = ipm_regions.merge(dispatch_spatial, left_on='model_regi', right_on='gen_load_zone', how='left')

#plot generation in each region relative to base scenario
for c in cost_limits:
    for y in years:
        base = ipm_regions[ipm_regions['scenario']==f'{scenario}']
        base = base[base['period']==y]
        base = pd.DataFrame(base[['model_regi', 'Energy_GWh_typical_yr']])
        base.rename(columns={'Energy_GWh_typical_yr': 'Base_Energy_GWh'}, inplace=True)


        plotdata = ipm_regions[ipm_regions['scenario']==f'{scenario}_{c}']
        plotdata = plotdata[plotdata['period']==y]

        plotdata = plotdata.merge(base, on='model_regi', how='left')
        plotdata['GenDif'] = plotdata['Energy_GWh_typical_yr']/plotdata['Base_Energy_GWh']

        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        plotdata.plot(column='GenDif', 
                        ax=ax, 
                        legend=True, 
                        cmap='OrRd',
                        edgecolor='black')

        ax.set_title(f'Generation Relative to Base', fontsize=15)
        ax.set_axis_off() 

        plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/Dispatch_Relative_{y}_{c}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution

dispatch_spatial = dispatch.groupby(['gen_load_zone', 'period', 'scenario', 'gen_energy_source']).agg({'Energy_GWh_typical_yr':'sum'}).reset_index()
for tech in ['Wind', 'Solar', 'Naturalgas', 'Coal', 'Electricity']:
    dispatch_spatial_temp = dispatch_spatial[dispatch_spatial['gen_energy_source']==tech]
    dispatch_spatial_temp = dispatch_spatial_temp[['scenario', 'period', 'gen_load_zone', 'Energy_GWh_typical_yr']]
    dispatch_spatial_temp.rename(columns={'Energy_GWh_typical_yr': f'Energy_GWh_{tech}'}, inplace=True)

    ipm_regions = ipm_regions.merge(dispatch_spatial_temp, left_on=['model_regi', 'period', 'scenario'], right_on=['gen_load_zone','period', 'scenario'], how='left')

    #plot capacity in each region relative to base scenario
    for c in cost_limits:
        for y in years:
            base = ipm_regions[ipm_regions['scenario']==f'{scenario}']
            base = base[base['period']==y]
            base = pd.DataFrame(base[['model_regi', f'Energy_GWh_{tech}']])
            base.rename(columns={f'Energy_GWh_{tech}': 'Base_Energy_GWh'}, inplace=True)


            plotdata = ipm_regions[ipm_regions['scenario']==f'{scenario}_{c}']
            plotdata = plotdata[plotdata['period']==y]

            plotdata = plotdata.merge(base, on='model_regi', how='left')
            plotdata['GenDif'] = plotdata[f'Energy_GWh_{tech}']-plotdata['Base_Energy_GWh']

            vmin = plotdata['GenDif'].min()
            vmax = plotdata['GenDif'].max()

            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            plotdata.plot(column='GenDif', 
                        ax=ax, 
                        legend=True, 
                        cmap='OrRd',
                        edgecolor='black',
                        vmin=vmin,  # Set minimum value for the colormap
                        vmax=vmax,
                        legend_kwds={'label': 'Generation Difference (GWh)',  # Title for the colorbar
                                     'orientation': 'vertical'})  # Set maximum value for the colormap

            ax.set_title(f'Generation Relative to Base: {tech}', fontsize=15)
            ax.set_axis_off() 
            plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/Dispatch_Relative_{tech}_{y}_{c}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution


dispatch = dispatch.groupby(['gen_tech', 'period', 'scenario']).agg({'Energy_GWh_typical_yr':'sum'}).reset_index()

other_techs = dispatch[dispatch['scenario']==scenario]
other_techs = other_techs[other_techs['Energy_GWh_typical_yr']<1000]
other_techs = other_techs['gen_tech'].tolist()
dispatch.loc[dispatch['gen_tech'].isin(other_techs), 'gen_tech'] = 'other'

for year in years:
    data_year = dispatch[dispatch['period'] == year]
    
    data_pivot = data_year.pivot_table(index='scenario', columns='gen_tech', values='Energy_GWh_typical_yr', aggfunc='sum')
    
    ax = data_pivot.plot(kind='bar', stacked=True, figsize=(10, 6), cmap='tab20')
    
    ax.set_title(f'Energy (GWh) by Scenario and Technology - Year {year}', fontsize=16)
    ax.set_ylabel('Energy (GWh)', fontsize=12)
    ax.set_xlabel('Scenario', fontsize=12)
    
    plt.legend(title='Technology', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/Dispatch_Relative_by_scenario_{year}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution

#####################
## Group Exposure
group_exposure=pd.read_csv(f"{result_dir}{scenario}/GroupExposure.csv")
group_exposure['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/GroupExposure.csv")
    tempdat['scenario']=f'{scenario}_{c}'
    group_exposure = pd.concat([group_exposure,tempdat])


for y in years:
    exposure_wide = group_exposure.pivot(index=['scenario', 'SetProduct_OrderedSet_2'], columns='SetProduct_OrderedSet_1', values='GroupExposure').reset_index()
    exposure_wide = exposure_wide[exposure_wide['SetProduct_OrderedSet_2']==y]
    bar_width = 0.15 
    index = np.arange(len(exposure_wide['scenario']))
    fig, ax = plt.subplots()

    bar1 = ax.bar(index, exposure_wide['Asian'], bar_width, label='Asian', color='b')
    bar2 = ax.bar(index + bar_width, exposure_wide['Black'], bar_width, label='Black', color='g')
    bar3 = ax.bar(index + 2*bar_width, exposure_wide['Latino'], bar_width, label='Latino', color='r')
    bar4 = ax.bar(index + 3*bar_width, exposure_wide['Native'], bar_width, label='Native Amer', color='yellow')
    bar5 = ax.bar(index + 4*bar_width, exposure_wide['WhiteNoLat'], bar_width, label='White', color='orange')  # Changed color to 'orange'

    ax.set_xlabel('Scenario')
    ax.set_ylabel('Average Exposure by Race')
    ax.set_title('Exposure by Technology')
    ax.set_xticks(index + 2*bar_width)  # Shift ticks to the middle of the grouped bars
    ax.set_xticklabels(exposure_wide['scenario'])
    ax.legend()

    plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/exposure_by_scenario_{y}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution

##
## PPF

group_exposure_max = group_exposure.groupby(['SetProduct_OrderedSet_2', 'scenario']).agg({'GroupExposure':'max'}).reset_index()
group_exposure_max['cost'] = group_exposure_max['scenario'].str.replace(f'{scenario}', '', regex=False)
group_exposure_max['cost'] = group_exposure_max['cost'].str.replace('_', '', regex=False)
group_exposure_max['cost'] = pd.to_numeric(group_exposure_max['cost'])
group_exposure_max.fillna(0, inplace=True)

colors = {2027: 'blue', 2030: 'green'}  # Assign specific colors to each year

for year in group_exposure_max['SetProduct_OrderedSet_2'].unique():
    subset = group_exposure_max[group_exposure_max['SetProduct_OrderedSet_2'] == year]
    plt.scatter(subset['cost'], subset['GroupExposure'], color=colors[year], label=str(year))

plt.xlabel('Cost')
plt.ylabel('Result')
plt.title('Cost vs Result (Colored by Year)')

plt.legend(title='Year')

plt.savefig(f'MIP_AirPollution/Figures/EndogenousResults/{scenario}/exposure_cost_PPF.png', dpi=300, bbox_inches='tight')  # DPI for high resolution
