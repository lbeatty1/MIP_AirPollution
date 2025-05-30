globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import yaml



os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')

with open("MIP_results_comparison/case_settings/26-zone/settings-atb2023/model_definition.yml", "r") as file:
    region_aggregations = yaml.safe_load(file)["region_aggregations"]
region_aggregations['FRCC']=['FRCC']


scenario = 'current_policies_short'
years = [2027, 2030, 2035, 2040, 2045, 2050]
result_dir = f'switch/26-zone/out/'
cost_limits = [50,100,200]

if not os.path.exists('MIP_AirPollution/Figures/EndogenousResults/'+scenario+'/'):
    os.mkdir('MIP_AirPollution/Figures/EndogenousResults/'+scenario+'/')


def update_technology(row, column):
    if 'naturalgas_ccavg' in row[column]:
        return 'natural gas cc'
    elif 'natural_gas_fired_combined' in row[column]:
        return 'natural gas cc'
    elif 'naturalgas_ctavg' in row[column]:
        return 'natural gas ct'
    elif 'natural_gas_fired_combustion' in row[column]:
        return 'natural gas ct'
    elif 'coal' in row[column]:
        return 'coal'
    elif 'biomass' in row[column]:
        return 'biomass'
    elif 'petroleum' in row[column]:
        return 'petroleum liquids'
    elif 'solar' in row[column]:
        return 'solar'
    elif 'wind' in row[column]:
        return 'wind'
    elif 'batter' in row[column]:
        return 'batteries'
    else:
        return np.nan
    
emitting_techs = ['coal', 'biomass', 'petroleum liquids', 'natural gas cc', 'natural gas ct']
    
zone_to_region = {
    zone: region for region, zones in region_aggregations.items() for zone in zones
}

scenario_mapping = {
    'current_policies_short': 'Base Case',
    'current_policies_short_50': '$50 Billion Budget',
    'current_policies_short_100': '$100 Billion Budget',
    'current_policies_short_200': '$200 Billion Budget'
}
scenario_order = ['Base Case', '$50 Billion Budget', '$100 Billion Budget', '$200 Billion Budget']

# Get the RdBu colormap
rd_bu = plt.cm.get_cmap('RdBu')

# Sample colors:
dark_red = rd_bu(0.1)  
white = "#ffffff"
dark_blue = rd_bu(0.99) 

# Optional: mix dark red and white to get a consistent light red
def mix(color1, color2, ratio):
    """Mix two hex colors with a ratio (0 to 1)"""
    import matplotlib.colors as mcolors
    c1 = np.array(mcolors.to_rgb(color1))
    c2 = np.array(mcolors.to_rgb(color2))
    return mcolors.to_hex((1 - ratio) * c1 + ratio * c2)

light_red = mix(dark_red, white, 0.5)

#read in exposure coefs
coefs=pd.DataFrame()
for y in years:
    coefs = pd.concat([coefs,
                       pd.read_csv(
                           f"MIP_Air_OutData/{scenario}_marginal_exposure_coefs_{y}.csv",
                           index_col=0)]
    )

#read in emissions estimates
emis = []
for year in years:
    shapefile_path = f'MIP_Air_OutData/{scenario}_simplified_marginal_emissions_{y}.shp'

    gdf = gpd.read_file(shapefile_path)
    
    # Append the GeoDataFrame to the list
    emis.append(gdf)

emis = gpd.GeoDataFrame(pd.concat(emis, ignore_index=True))
emis = pd.DataFrame(emis[['NOx', 'SOx', 'PM2_5', 'NH3', 'VOC', 'Resource']])

emis = emis.groupby(['Resource']).agg({'NOx':'sum', 'PM2_5':'sum', 'NH3':'sum', 'SOx':'sum', 'PM2_5':'sum', 'VOC':'sum'}).reset_index()

#read in dispatch
dispatch=pd.read_csv(f"{result_dir}{scenario}/dispatch_gen_annual_summary.csv",
                     index_col=0)
dispatch['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/dispatch_gen_annual_summary.csv",
                         index_col=0)
    tempdat['scenario']=f'{scenario}_{c}'
    dispatch = pd.concat([dispatch,tempdat])


ipm_regions = gpd.read_file('AirPollution_Data/IPM_Regions_201770405.shp')
ipm_regions["model_region"] = ipm_regions["IPM_Region"].map(zone_to_region)
ipm_regions = ipm_regions.dissolve(by="model_region", as_index=False)
    
## Group Exposure
group_exposure=pd.read_csv(f"{result_dir}{scenario}/GroupExposure.csv")
group_exposure['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/GroupExposure.csv")
    tempdat['scenario']=f'{scenario}_{c}'
    group_exposure = pd.concat([group_exposure,tempdat])

## Plot coefs and emissions
coefs['technology'] = coefs.apply(update_technology, axis=1, column='Cluster')
summary=coefs.groupby(['technology', 'Race']).agg({'Exposure':'mean'}).reset_index()

emis['technology'] = emis.apply(update_technology, axis=1, column='Resource')
emis_summary = emis.groupby(['technology']).agg({'NOx':'mean', 'PM2_5':'mean', 'NH3':'mean', 'SOx':'mean', 'PM2_5':'mean', 'VOC':'mean'}).reset_index()
emis_summary = emis_summary.sort_values(by='SOx', ascending=False).reset_index(drop=True)
emis_summary = emis_summary[emis_summary['technology'].isin(emitting_techs)]
# Bar setup
bar_width = 0.15
index = np.arange(len(emis_summary['technology']))
fig, ax = plt.subplots(figsize=(12, 6))

# Use Tableau 10 colors from matplotlib
tab10 = plt.get_cmap('tab10').colors

# Plot bars with tab10 colors
bar1 = ax.bar(index, emis_summary['PM2_5'], bar_width, label='PM2.5', color=tab10[0])
bar2 = ax.bar(index + bar_width, emis_summary['SOx'], bar_width, label='SOx', color=tab10[1])
bar3 = ax.bar(index + 2*bar_width, emis_summary['NOx'], bar_width, label='NOx', color=tab10[2])
bar4 = ax.bar(index + 3*bar_width, emis_summary['NH3'], bar_width, label='NH3', color=tab10[3])
bar5 = ax.bar(index + 4*bar_width, emis_summary['VOC'], bar_width, label='VOC', color=tab10[4])

# Labels and title
ax.set_xlabel('Technology', fontsize=14, fontweight='bold')
ax.set_ylabel('Mean Emissions (Tons/MWh)', fontsize=14, fontweight='bold')
ax.set_title('Mean Emissions by Technology', fontsize=16, fontweight='bold')


# Rotate x-axis labels
ax.set_xticks(index + 2*bar_width)
ax.set_xticklabels(emis_summary['technology'], rotation=0, ha='center')

# Legend and layout
ax.legend()
plt.tight_layout()

# Save the figure
plt.savefig('MIP_AirPollution/Figures/EndogenousPaper/emissions_by_technology.png', dpi=300, bbox_inches='tight')

#####Exposure
exposure_wide = summary.pivot(index='technology', columns='Race', values='Exposure').reset_index()
exposure_wide = exposure_wide.set_index('technology')  # set as index for alignment
exposure_wide = exposure_wide.loc[emis_summary['technology']]  # reorder by emissions plot
exposure_wide = exposure_wide.reset_index()
# Set bar width and position
bar_width = 0.15
index = np.arange(len(exposure_wide['technology']))
fig, ax = plt.subplots(figsize=(12, 6))

# Use Tableau 10 color palette
tab10 = plt.get_cmap('tab10').colors

# Create grouped bar plot with consistent color/style
ax.bar(index, exposure_wide['Asian'], bar_width, label='Asian', color=tab10[0])
ax.bar(index + bar_width, exposure_wide['Black'], bar_width, label='Black', color=tab10[1])
ax.bar(index + 2*bar_width, exposure_wide['Latino'], bar_width, label='Latino', color=tab10[2])
ax.bar(index + 3*bar_width, exposure_wide['Native'], bar_width, label='Native Amer', color=tab10[3])
ax.bar(index + 4*bar_width, exposure_wide['WhiteNoLat'], bar_width, label='White', color=tab10[4])

# Labels and title (bold + larger font)
ax.set_xlabel('Technology', fontsize=14, fontweight='bold')
ax.set_ylabel('Marginal Exposure per MWh', fontsize=14, fontweight='bold')
ax.set_title('Exposure by Technology', fontsize=16, fontweight='bold')

# X-axis tick settings
ax.set_xticks(index + 2*bar_width)
ax.set_xticklabels(exposure_wide['technology'], rotation=45, ha='right')

# Legend and layout
ax.legend()
plt.tight_layout()

# Save figure
plt.savefig('MIP_AirPollution/Figures/EndogenousPaper/exposure_by_technology.png', dpi=300, bbox_inches='tight')

####################
## Plot dispatch ###
####################
dispatch['technology'] = dispatch.apply(update_technology, axis=1, column='gen_tech')
dispatch['scenario_2'] = dispatch['scenario'].replace(scenario_mapping)


for year in sorted(years, reverse=True):
    data_year = dispatch[dispatch['period'] == year]
    data_year['scenario_2'] = pd.Categorical(data_year['scenario_2'], categories=scenario_order, ordered=True)

    data_pivot = data_year.pivot_table(index='scenario_2', columns='gen_energy_source', values='Energy_GWh_typical_yr', aggfunc='sum')
    
    if year==2050:
        max_by_column = data_pivot.max()
        cols_to_keep = max_by_column[max_by_column > 1000].index
    
    data_pivot = data_pivot[cols_to_keep]

    ax = data_pivot.plot(kind='bar', stacked=True, figsize=(10, 6), cmap='tab20')
    
    ax.set_title(f'Energy (GWh) by Scenario and Technology - Year {year}', fontsize=16)
    ax.set_ylabel('Energy (GWh)', fontsize=12)
    ax.set_xlabel('Scenario', fontsize=12)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)  # <-- This sets x labels to horizontal

    if year == 2050:
            plt.legend(title='Technology', bbox_to_anchor=(1.05, 1), loc='upper left')
    else:
        ax.get_legend().remove()

    plt.tight_layout()
    plt.savefig(f'MIP_AirPollution/Figures/EndogenousPaper/Dispatch_Relative_by_scenario_{year}.png', dpi=300, bbox_inches='tight')  # DPI for high resolution


########### 
## Group Exposure

for y in years:
    exposure_wide = group_exposure.pivot(
        index=['scenario', 'SetProduct_OrderedSet_2'],
        columns='SetProduct_OrderedSet_1',
        values='GroupExposure'
    ).reset_index()

    # Filter year
    exposure_wide = exposure_wide[exposure_wide['SetProduct_OrderedSet_2'] == y].copy()

    # Map scenario names
    exposure_wide['scenario_2'] = exposure_wide['scenario'].replace(scenario_mapping)
    exposure_wide['scenario_2'] = pd.Categorical(exposure_wide['scenario_2'], categories=scenario_order, ordered=True)

    # Sort by scenario order
    exposure_wide = exposure_wide.sort_values('scenario_2')

    # Plot
    bar_width = 0.15
    index = np.arange(len(exposure_wide['scenario_2']))
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.bar(index, exposure_wide['Asian'], bar_width, label='Asian', color=tab10[0])
    ax.bar(index + bar_width, exposure_wide['Black'], bar_width, label='Black', color=tab10[1])
    ax.bar(index + 2 * bar_width, exposure_wide['Latino'], bar_width, label='Latino', color=tab10[2])
    ax.bar(index + 3 * bar_width, exposure_wide['Native'], bar_width, label='Native Amer', color=tab10[3])
    ax.bar(index + 4 * bar_width, exposure_wide['WhiteNoLat'], bar_width, label='White', color=tab10[4])

    # Labels and title
    ax.set_ylabel('Average Exposure by Race', fontsize=14, fontweight='bold')
    ax.set_title(f'Exposure by Scenario - Year {y}', fontsize=16, fontweight='bold')

    ax.set_xticks(index + 2 * bar_width)
    ax.set_xticklabels(exposure_wide['scenario_2'], rotation=0, ha='center')
    ax.legend()

    plt.tight_layout()
    plt.savefig(f'MIP_AirPollution/Figures/EndogenousPaper/exposure_by_scenario_{y}.png', dpi=300, bbox_inches='tight')
    plt.show()


########
## PPF

# Prepare data
group_exposure_max = group_exposure.groupby(['SetProduct_OrderedSet_2', 'scenario']) \
    .agg({'GroupExposure': 'max'}).reset_index()
group_exposure_max['cost'] = group_exposure_max['scenario'].str.replace(f'{scenario}', '', regex=False)
group_exposure_max['cost'] = group_exposure_max['cost'].str.replace('_', '', regex=False)
group_exposure_max['cost'] = pd.to_numeric(group_exposure_max['cost'])
group_exposure_max.fillna(0, inplace=True)
sorted_years = sorted(group_exposure_max['SetProduct_OrderedSet_2'].unique())
# Normalize years for color mapping
norm = plt.Normalize(min(sorted_years), max(sorted_years))
cmap = plt.cm.plasma  # You can change to 'plasma', 'cividis', etc.
colors = {year: cmap(norm(year)) for year in sorted_years}

# Plot
fig, ax = plt.subplots(figsize=(8, 6))
for year in sorted_years:
    subset = group_exposure_max[group_exposure_max['SetProduct_OrderedSet_2'] == year]
    ax.scatter(subset['cost'], subset['GroupExposure'], color=colors[year], label=str(year), s=60)

# Style
ax.set_xlabel('Budget', fontsize=14, fontweight='bold')
ax.set_ylabel('Max Exposure', fontsize=14, fontweight='bold')
ax.set_title('Budget vs Max(Pollution Exposure)', fontsize=16, fontweight='bold')
ax.legend(title='Year')
plt.tight_layout()

# Save
plt.savefig(f'MIP_AirPollution/Figures/EndogenousPaper/exposure_cost_PPF.png', dpi=300, bbox_inches='tight')
plt.show()

###################
## Plot Capacity ##
###################

capacity=pd.read_csv(f"{result_dir}{scenario}/gen_cap.csv",
                     index_col=0)
capacity['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/gen_cap.csv",
                         index_col=0)
    tempdat['scenario']=f'{scenario}_{c}'
    capacity = pd.concat([capacity,tempdat])


capacity_spatial = capacity.groupby(['gen_energy_source', 'gen_load_zone', 'PERIOD', 'scenario']).agg({'GenCapacity':'sum'}).reset_index()

base = capacity_spatial[capacity_spatial['scenario']==f'{scenario}']
base = pd.DataFrame(base[['gen_load_zone','gen_energy_source', 'GenCapacity', 'PERIOD']])
base.rename(columns={'GenCapacity': 'Base_GenCapacity'}, inplace=True)

capacity_spatial = pd.merge(capacity_spatial, base, on=['gen_load_zone', 'gen_energy_source', 'PERIOD'], how='left')

#calculate difference in capacity
capacity_spatial['dif']=capacity_spatial['GenCapacity']-capacity_spatial['Base_GenCapacity']
capacity_spatial['dif']=capacity_spatial['dif']/1000
capacity_spatial = capacity_spatial.merge(ipm_regions, right_on='model_region', left_on='gen_load_zone', how='left')

c=200
y=2050
tech = 'Solar'

plotdata = capacity_spatial[capacity_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['PERIOD']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = -5
high = plotdata['dif'].max()

custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, light_red),                              # low end
        ((0 - low) / (high - low), white),             # midpoint
        (1.0, dark_blue)                               # high end
    ]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
norm = Normalize(vmin=low, vmax=high)


# 3. Plot
fig, ax = plt.subplots(1, 1, figsize=(10, 6))

plotdata.plot(column='dif', 
              ax=ax, 
              cmap=custom_cmap, 
              edgecolor='black',
              norm=norm,
              legend=False)

# 4. Add colorbar
sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
sm.set_array([])

ticks = np.arange(-5, high + 1, 5)
cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GW)")

ax.set_title("Solar Generation Capacity in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()

fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/solar_capacity_map.png", dpi=300, bbox_inches='tight')

c=200
y=2050
tech = 'Wind'

plotdata = capacity_spatial[capacity_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['PERIOD']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Get the RdBu colormap
rd_bu = plt.cm.get_cmap('RdBu')

# Sample colors:
white = "#ffffff"
dark_blue = rd_bu(0.99)  # darkest blue end

# Create custom diverging colormap
low = 0
high = plotdata['dif'].max()

custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0, white),             # midpoint
        (1.0, dark_blue)                               # high end
    ]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
norm = Normalize(vmin=low, vmax=high)


# 3. Plot
fig, ax = plt.subplots(1, 1, figsize=(10, 6))

plotdata.plot(column='dif', 
              ax=ax, 
              cmap=custom_cmap, 
              edgecolor='black',
              norm=norm,
              legend=False)

# 4. Add colorbar
sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
sm.set_array([])

ticks = np.arange(-5, high + 1, 5)
cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GW)")

ax.set_title("Wind Generation Capacity in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()

fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/wind_capacity_map.png", dpi=300, bbox_inches='tight')


###################
## Plot Dispatch ##
###################
dispatch_spatial = dispatch.groupby(['gen_energy_source', 'gen_load_zone', 'period', 'scenario']).agg({'Energy_GWh_typical_yr':'sum'}).reset_index()

base = dispatch_spatial[dispatch_spatial['scenario']==f'{scenario}']
base = pd.DataFrame(base[['gen_load_zone','gen_energy_source', 'Energy_GWh_typical_yr', 'period']])
base.rename(columns={'Energy_GWh_typical_yr': 'Base_Gen'}, inplace=True)

dispatch_spatial = pd.merge(dispatch_spatial, base, on=['gen_load_zone', 'gen_energy_source', 'period'], how='left')

#calculate difference in capacity
dispatch_spatial['dif']=dispatch_spatial['Energy_GWh_typical_yr']-dispatch_spatial['Base_Gen']
dispatch_spatial = dispatch_spatial.merge(ipm_regions, right_on='model_region', left_on='gen_load_zone', how='left')

c=200
y=2050
tech = 'Solar'

plotdata = capacity_spatial[capacity_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['PERIOD']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = plotdata['dif'].min()
high = plotdata['dif'].max()

custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, light_red),                              # low end
        ((0 - low) / (high - low), white),             # midpoint
        (1.0, dark_blue)                               # high end
    ]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
norm = Normalize(vmin=low, vmax=high)


# 3. Plot
fig, ax = plt.subplots(1, 1, figsize=(10, 6))

plotdata.plot(column='dif', 
              ax=ax, 
              cmap=custom_cmap, 
              edgecolor='black',
              norm=norm,
              legend=False)

# 4. Add colorbar
sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
sm.set_array([])

ticks = np.arange(-5, high + 1, 5)
cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Solar Generation in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/solar_generation_map.png", dpi=300, bbox_inches='tight')



c=200
y=2050
tech = 'Wind'

plotdata = capacity_spatial[capacity_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['PERIOD']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = plotdata['dif'].min()
high = plotdata['dif'].max()

custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, white),                              # low end
        (1.0, dark_blue)                               # high end
    ]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
norm = Normalize(vmin=low, vmax=high)


# 3. Plot
fig, ax = plt.subplots(1, 1, figsize=(10, 6))

plotdata.plot(column='dif', 
              ax=ax, 
              cmap=custom_cmap, 
              edgecolor='black',
              norm=norm,
              legend=False)

# 4. Add colorbar
sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
sm.set_array([])

ticks = np.arange(-5, high + 1, 5)
cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Wind Generation in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/wind_generation_map.png", dpi=300, bbox_inches='tight')

### Naturalgas

c=200
y=2050
tech = 'Naturalgas'

plotdata = capacity_spatial[capacity_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['PERIOD']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = plotdata['dif'].min()
high = plotdata['dif'].max()

custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, dark_red),                              # low end
        ((0 - low) / (high - low), white),             # midpoint
        (1.0, dark_blue)                               # high end
    ]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
norm = Normalize(vmin=low, vmax=high)


# 3. Plot
fig, ax = plt.subplots(1, 1, figsize=(10, 6))

plotdata.plot(column='dif', 
              ax=ax, 
              cmap=custom_cmap, 
              edgecolor='black',
              norm=norm,
              legend=False)

# 4. Add colorbar
sm = plt.cm.ScalarMappable(cmap=custom_cmap, norm=norm)
sm.set_array([])

ticks = np.arange(5 * math.floor(low / 5), 5 * math.ceil(high / 5), 5)
cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Natural Gas Generation in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()

fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/naturalgas_generation_map.png", dpi=300, bbox_inches='tight')
