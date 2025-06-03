globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import ListedColormap
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
import yaml
from mpl_toolkits.axes_grid1 import make_axes_locatable
from shapely.geometry import LineString
# import matplotlib.colors as mcolors




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
    'current_policies_short_50': '$50 Billion',
    'current_policies_short_100': '$100 Billion',
    'current_policies_short_200': '$200 Billion'
}
scenario_order = ['Base Case', '$50 Billion', '$100 Billion', '$200 Billion']

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
lighter_blue = mix(dark_blue, white, 0.3)

def round_up_to_step(high, low, step):
    steps = math.ceil((high - low) / step)
    return low + steps * step


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

## transmission
transmission = pd.read_csv(f"{result_dir}{scenario}/transmission.csv")
transmission['scenario']=scenario
for c in cost_limits:
    tempdat = pd.read_csv(f"{result_dir}{scenario}_{c}/transmission.csv")
    tempdat['scenario']=f'{scenario}_{c}'
    transmission = pd.concat([transmission, tempdat])

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
ax.set_xlabel('Technology', fontsize=16, fontweight='bold')
ax.set_ylabel('Mean Emissions (Tons/MWh)', fontsize=18, fontweight='bold')
ax.set_title('Mean Emissions by Technology', fontsize=18, fontweight='bold')


# Rotate x-axis labels
ax.set_xticks(index + 2*bar_width)
ax.set_xticklabels(emis_summary['technology'], rotation=0, ha='center')
ax.tick_params(axis='x', labelsize=16)

# Legend and layout
ax.legend(fontsize=16)
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
ax.set_xlabel('Technology', fontsize=16, fontweight='bold')
ax.set_ylabel('Marginal Exposure per MWh', fontsize=18, fontweight='bold')
ax.set_title('Exposure by Technology', fontsize=18, fontweight='bold')

# X-axis tick settings
ax.set_xticks(index + 2*bar_width)
ax.set_xticklabels(exposure_wide['technology'], rotation=0, ha='center')
ax.tick_params(axis='x', labelsize=16)

# Legend and layout
ax.legend(fontsize=16)
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
    
    ax.set_title(f'Energy (GWh) by Scenario and Technology - Year {year}', fontsize=20)
    ax.set_ylabel('Energy (GWh)', fontsize=18)
    ax.set_xlabel('Scenario', fontsize=18)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0, fontsize=18)  # <-- This sets x labels to horizontal

    # if year == 2050:
    #         plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=18)

    # else:
    #     ax.get_legend().remove()

    if year == 2050:
        # Get handles and labels from the original axis
        handles, labels = ax.get_legend_handles_labels()

        # Create a new figure for the legend
        fig_legend = plt.figure(figsize=(8, 6))
        
        # Add legend and store it in a variable
        legend = fig_legend.legend(
            handles, labels,
            loc='center',
            fontsize=18,
            frameon=False,
            ncol=2,
            title='Technology'
        )
        
        # Set legend title font size
        legend.get_title().set_fontsize(24)

        # Save the figure with the legend
        fig_legend.savefig(
            f'MIP_AirPollution/Figures/EndogenousPaper/Legend_{year}.png',
            dpi=300,
            bbox_inches='tight'
        )
        plt.close(fig_legend)
        
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

#calculate difference in dispatch
dispatch_spatial['dif']=dispatch_spatial['Energy_GWh_typical_yr']-dispatch_spatial['Base_Gen']

## first, figure out what big, small differences in generation are

max_dif = dispatch_spatial['dif'].max()
min_dif = dispatch_spatial['dif'].min()
max_dif = max(abs(max_dif), abs(min_dif))

c=200
y=2050
tech = 'Solar'

plotdata = dispatch_spatial[dispatch_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['period']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]

plotdata = ipm_regions.merge(plotdata, left_on='model_region', right_on='gen_load_zone', how='left')

plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = math.floor(plotdata['dif'].min()/5000)*5000
high = math.ceil(plotdata['dif'].max()/5000)*5000
ticks = np.arange(low, high+1, 20000)
rounded_high = round_up_to_step(high, low, 10000)

plot_red = mix(white, dark_red, abs(low/max_dif))
plot_blue = mix(white, dark_blue, rounded_high/max_dif)
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, plot_red),                              # low end
        ((0 - low) / (high - low), white),             # midpoint
        (1.0, plot_blue)                               # high end
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

cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Solar Generation in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/solar_generation_map.png", dpi=300, bbox_inches='tight')

##############
## Wind ######
##############

c=200
y=2050
tech = 'Wind'

plotdata = dispatch_spatial[dispatch_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['period']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]

plotdata = ipm_regions.merge(plotdata, left_on='model_region', right_on='gen_load_zone', how='left')
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = 0
high = math.ceil(plotdata['dif'].max()/5000)*5000
ticks = np.arange(low, high+1, 20000)
rounded_high = round_up_to_step(high, low, 20000)

plot_blue = mix(white, dark_blue, rounded_high/max_dif)
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, white),                              # low end
        (1.0, plot_blue)                               # high end
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

cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Wind Generation in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/wind_generation_map.png", dpi=300, bbox_inches='tight')

####################
### Naturalgas #####
####################
c=200
y=2050
tech = 'Naturalgas'

plotdata = dispatch_spatial[dispatch_spatial['scenario']==f'{scenario}_{c}']
plotdata = plotdata[plotdata['period']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]

plotdata = ipm_regions.merge(plotdata, left_on='model_region', right_on='gen_load_zone', how='left')
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = math.floor(plotdata['dif'].min()/5000)*5000
high = math.ceil(plotdata['dif'].max()/5000)*5000
ticks = np.arange(low, high+1, 40000)
rounded_high = round_up_to_step(high, low, 40000)

plot_red = mix(white, dark_red, abs(low/max_dif))
plot_blue = mix(white, dark_blue, rounded_high/max_dif)
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, plot_red),                              # low end
        ((0 - low) / (high - low), white),             # midpoint
        (1.0, plot_blue)                               # high end
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

cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Natural Gas Generation in 2050 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/naturalgas_generation_map.png", dpi=300, bbox_inches='tight')


## Show that coal gets killed off faster with more money

c=200
y=2027
tech = 'Coal'

plotdata = dispatch_spatial
plotdata = plotdata[plotdata['period']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]

maxdif = plotdata['dif'].min()

plotdata = plotdata[plotdata['scenario']==f'{scenario}_{c}']
plotdata = ipm_regions.merge(plotdata, left_on='model_region', right_on='gen_load_zone', how='left')
plotdata['dif'] = plotdata['dif'].fillna(0)
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = math.floor(plotdata['dif'].min()/10000)*10000
high = 0 
ticks = np.arange(low, high+1, 20000)
rounded_high = round_up_to_step(high, low, 20000)

plot_red = mix(white, dark_red, low/maxdif)
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, plot_red),                              # low end
        (1.0, white)                               # high end
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

cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Coal Generation in 2027 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/coal_generation_map_2027_200B.png", dpi=300, bbox_inches='tight')


c=50
y=2027
tech = 'Coal'

plotdata = dispatch_spatial
plotdata = plotdata[plotdata['period']==y]
plotdata = plotdata[plotdata['gen_energy_source']==tech]

maxdif = plotdata['dif'].min()

plotdata = plotdata[plotdata['scenario']==f'{scenario}_{c}']
plotdata = ipm_regions.merge(plotdata, left_on='model_region', right_on='gen_load_zone', how='left')
plotdata['dif'] = plotdata['dif'].fillna(0)
plotdata = gpd.GeoDataFrame(plotdata, geometry='geometry')
plotdata.to_crs("EPSG:4326", inplace=True)

# Create custom diverging colormap
low = math.floor(plotdata['dif'].min()/10000)*10000
high = 0 
ticks = np.arange(low, high+1, 20000)
rounded_high = round_up_to_step(high, low, 20000)

plot_red = mix(white, dark_red, low/maxdif)
custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, plot_red),                              # low end
        (1.0, white)                               # high end
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

cbar = plt.colorbar(sm, ax=ax, ticks=ticks)
cbar.set_label("Difference (GWh)")

ax.set_title("Coal Generation in 2027 with $200B Budget \n Relative to Base", fontsize=15)
ax.set_axis_off()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/coal_generation_map_2027_50B.png", dpi=300, bbox_inches='tight')

##################
## Transmission ##
##################
base = transmission[transmission['scenario']==f'{scenario}']
base = pd.DataFrame(base[['PERIOD', 'trans_lz1', 'trans_lz2', 'TxCapacityNameplateAvailable']])
base.rename(columns={'TxCapacityNameplateAvailable': 'Base_Capacity'}, inplace=True)

transmission = pd.merge(transmission, base, how='left', on=['PERIOD', 'trans_lz1', 'trans_lz2'])
c=200
y=2050
plotdata = transmission[transmission['PERIOD']==y]
plotdata = plotdata[plotdata['scenario']==f'{scenario}_{c}']
plotdata['dif']=plotdata['TxCapacityNameplateAvailable']-plotdata['Base_Capacity']


#get capacity differences
capacity_tot = capacity.groupby(['scenario', 'gen_load_zone', 'PERIOD']).agg({'GenCapacity':'sum'}).reset_index()
base = capacity_tot[capacity_tot['scenario']==f'{scenario}']
base = pd.DataFrame(base[['PERIOD', 'gen_load_zone', 'GenCapacity']])
base.rename(columns={'GenCapacity':'Base_Capacity'}, inplace=True)
capacity_tot = pd.merge(capacity_tot, base, how='left', on=['PERIOD', 'gen_load_zone'])
capacity_tot = capacity_tot[capacity_tot['scenario']==f'{scenario}_{c}']
capacity_tot = capacity_tot[capacity_tot['PERIOD']==y]
capacity_tot['dif'] = capacity_tot['GenCapacity']-capacity_tot['Base_Capacity']

# Ensure the centroids are available
ipm_regions = ipm_regions.merge(capacity_tot, left_on='model_region', right_on='gen_load_zone', how='left')
ipm_regions.to_crs("EPSG:4326", inplace=True)
ipm_regions['centroid'] = ipm_regions.geometry.centroid

# Create a dictionary mapping region names to centroids
region_centroids = ipm_regions.set_index('model_region')['centroid'].to_dict()

# Function to get centroid from region name
def get_centroid(region):
    return region_centroids.get(region)

# Create a GeoDataFrame of transmission lines
lines = []
for _, row in plotdata.iterrows():
    start = get_centroid(row['trans_lz1'])
    end = get_centroid(row['trans_lz2'])
    if start is not None and end is not None:
        line = LineString([start, end])
        lines.append({'geometry': line, 'dif': row['dif']})

lines_gdf = gpd.GeoDataFrame(lines, crs=ipm_regions.crs)


custom_cmap = LinearSegmentedColormap.from_list(
    "custom_RdBu_subset",
    [
        (0.0, white),                              # low end
        (1.0, dark_blue)                           # high end
    ]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
trans_norm = Normalize(vmin=0, vmax=lines_gdf['dif'].max())

trans_cmap = LinearSegmentedColormap.from_list(
    "yellow_to_red",
    ["#ffffcc", "#ffeda0", "#feb24c", "#f03b20", "#bd0026"]
)

# Use Normalize instead of TwoSlopeNorm for true linear spacing
norm = Normalize(vmin=0, vmax=ipm_regions['dif'].max())

#plot
fig, ax = plt.subplots(figsize=(10, 10))

# Plot the regions
ipm_regions.plot(column='dif', cmap=custom_cmap, norm=norm, edgecolor='black', ax=ax)

# Plot transmission lines
lines_gdf.plot(ax=ax, 
               linewidth=4, 
               column='dif', 
               cmap=trans_cmap, 
               norm=trans_norm)

# Set map extent
ax.set_xlim([-107, -82])
ax.set_ylim([25, 37])
ax.set_title("Difference in Transmission and Generation Capacity from Base \n with $200B Budget")
ax.axis('off')

# Add colorbars in separate axes to prevent overlap
divider = make_axes_locatable(ax)
cax1 = divider.append_axes("right", size="3%", pad=0.2)  # More padding
cax2 = divider.append_axes("right", size="3%", pad=0.9)  # Further to the right

# First colorbar
sm1 = plt.cm.ScalarMappable(norm=norm, cmap=custom_cmap)
sm1._A = []
cbar1 = fig.colorbar(sm1, cax=cax1)
cbar1.set_label("Difference in Total Capacity")

# Second colorbar
sm2 = plt.cm.ScalarMappable(norm=trans_norm, cmap=trans_cmap)
sm2._A = []
cbar2 = fig.colorbar(sm2, cax=cax2)
cbar2.set_label("Difference in Transmission Capacity")

plt.tight_layout()
plt.show()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/transmission_capacity_substitution.png", dpi=300, bbox_inches='tight')

####################
## Emissions #######
####################

emissions = dispatch.groupby(['period', 'scenario_2', 'scenario']).agg({'DispatchEmissions_tCO2_per_typical_yr':'sum'}).reset_index()
emissions = pd.merge(emissions, group_exposure_max, how='left', left_on=['period', 'scenario'], right_on=['SetProduct_OrderedSet_2', 'scenario'])

# Sort data for proper line drawing
emissions_sorted = emissions.sort_values(by=['scenario_2', 'period'])
emissions_sorted = emissions_sorted.rename(columns={'scenario_2': 'Scenario', 'period':'Year'})
emissions_sorted['DispatchEmissions_tCO2_per_typical_yr']=emissions_sorted['DispatchEmissions_tCO2_per_typical_yr']/1e9

# Create base scatter plot
plt.figure(figsize=(10, 6))
sns.scatterplot(
    data=emissions_sorted,
    x='DispatchEmissions_tCO2_per_typical_yr',
    y='GroupExposure',
    hue='Year',
    style='Scenario',
    palette='viridis',
    s=130,
    alpha=0.8
)

# Draw lines connecting points within each 'scenario_2' group
for scenario, group_df in emissions_sorted.groupby('Scenario'):
    plt.plot(
        group_df['DispatchEmissions_tCO2_per_typical_yr'],
        group_df['GroupExposure'],
        marker='',  # no additional markers
        color='grey',
        linestyle='-',
        linewidth=1,
        alpha=0.5,
        label=None
    )


# Labels and layout
plt.xlabel('Dispatch Emissions (Billion tCO₂/year)')
plt.ylabel('Group Exposure')
plt.title('CO2 Emissions versus Max(Group Exposure)')

plt.grid(True)
plt.tight_layout()
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.show()
fig.savefig("MIP_AirPollution/Figures/EndogenousPaper/emissions_vs_exposure.png", dpi=300, bbox_inches='tight')
