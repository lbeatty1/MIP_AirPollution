# # Code to impute emissions rates, then output a file that specifies emissions per location per MWh of generation

# The first challenge will be to get emissions rates (lb/mwh).  To do this I'll be taking EIA data on net generation and EPA data on emissions to calculate rates.  There will be many missings that I will fill in by taking capacity-weighted technology-planning_year means.
# 
# Once I have emissions rates, the goal will be to output a series of shapefiles of location-specific emissions per MWh. A challenge here is assigning output to to specific plants.  I assign production based on capacity.
# 
# ### Brief Code Overview
# 1. Data cleaning (formatting columns, names, etc)
# 2. Merge EIA and EPA data into existing_gen_units using the EPA-EIA crosswalk. 
# 3. Impute generation for generators with missing generation.  To do this, I take plant-level generation and distribute that generation to generators based on each generator's capacity.
# 4. Calculate generation-weighted average emissions rates, then use those to fill in generators with missing emissions rates (missings get filled in with a technology-planningyear weighted mean).
# 5. Calculate marginal emissions by multiplying rates by that generator's share of capacity for its cluster.
# 6. Figure out emissions from new sources (here only natural gas)
# 7. Split the emissions output by planning year and write to shapefiles.



###########################
### 1. Data cleaning #####
###########################
globals().clear()

import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import geopandas as gpd
import fiona
import math
import zipfile
from shapely.geometry import Point
import yaml

#os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')
os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')

# READ EVERYTHING IN
from MIP_AirPollution.Endogenous.settings import *

with open("MIP_results_comparison/case_settings/26-zone/settings-atb2023/model_definition.yml", "r") as file:
    region_aggregations = yaml.safe_load(file)["region_aggregations"]
region_aggregations['FRCC']=['FRCC']

existing_gen_units = pd.DataFrame()
scenario='current_policies_short'

#check if folder exists, and if not, unzip corresponding folder
if not os.path.exists('AirPollution_Data/GenX inputs/'+scenario+'/'):
    with zipfile.ZipFile('AirPollution_Data/GenX inputs/'+scenario+'.zip', 'r') as zip_ref:
        zip_ref.extractall('AirPollution_Data/GenX inputs/'+scenario+'/')
else:

    print('Data/GenX inputs/'+scenario+'/'+" already exists")


existing_gen_units = pd.DataFrame()
# get years and file input names
for filename, year in year_inputs.items():
    existing_gen_units_temp = pd.read_csv('AirPollution_Data/GenX inputs/' + scenario + '/' + scenario + '/Inputs/Inputs_' + filename + '/extra_outputs/existing_gen_units.csv')
    existing_gen_units_temp['planning_year'] = year
    existing_gen_units = pd.concat([existing_gen_units, existing_gen_units_temp], ignore_index=True)

#filter out by retirement year

existing_gen_units = existing_gen_units.query('retirement_year>=planning_year')

#PG generators data
generators_data = pd.read_csv('switch/26-zone/in/foresight/'+scenario+'/gen_info.csv')

#EIA-EPA Crosswalk
crosswalk = pd.read_csv("AirPollution_Data/"+datafile_names['crosswalk'])

# EIA 860 for Generator Info, and location info
eia860 = pd.read_excel("AirPollution_Data/"+datafile_names['eia_860'], skiprows=1)
plants = pd.read_excel('AirPollution_Data/2___Plant_Y2022.xlsx', skiprows=1)


# EIA923 for Generation Info
eia923_fuels = pd.read_excel("AirPollution_Data/"+ datafile_names['eia_923'], sheet_name='Page 1 Generation and Fuel Data', skiprows=5)
eia923_generators = pd.read_excel("AirPollution_Data/"+ datafile_names['eia_923'], sheet_name='Page 4 Generator Data', skiprows=5)

#Emissions
emissions = pd.read_csv("AirPollution_Data/CAMD/facilities_emissions.csv")
#only want year 2020
emissions = emissions.query('year==2020')

# PM25
pm25 = pd.read_excel("AirPollution_Data/egrid-draft-pm-emissions.xlsx", sheet_name="2021 PM Unit-level Data", skiprows=1)

## Read in and format NEI ####

#nei data gives values for ammonia, vocs, and also pm2.5
#It also has so2 and nox output that mostly matches camd data
#I'll prioritise camd data, but fill in any missings with nei

#cems noncems just distinguish whether emissions were continuously monitored or imputed
#doesn't really matter for our purposes
nei_cems = pd.read_csv('AirPollution_Data/2020ha2_cb6_20k/inputs/ptegu/egucems_SmokeFlatFile_2020NEI_POINT_20230128_27mar2023_v1.csv', skiprows=16)
nei_noncems = pd.read_csv('AirPollution_Data/2020ha2_cb6_20k/inputs/ptegu//egunoncems_SmokeFlatFile_2020NEI_POINT_20230128_27mar2023_v0.csv', skiprows=15)
nei = pd.concat([nei_cems, nei_noncems])

#pull out the relevant pollutants
nei = nei.groupby(['oris_facility_code', 'oris_boiler_id', 'poll']).agg({'ann_value': 'sum'}).reset_index()
nei = nei[nei['poll'].isin(['CO', 'NH3', 'NOX', 'PM25-PRI', 'SO2', 'SO4', 'VOC'])]

#put weights in pounds
nei['poll']=nei['poll']+'_nei_tons'
nei['ann_value']=nei['ann_value']
nei = nei.pivot(index=['oris_facility_code', 'oris_boiler_id'], columns='poll', values='ann_value').reset_index()
nei = nei.rename(columns = {'oris_facility_code': 'CAMD_PLANT_ID', 'oris_boiler_id': 'CAMD_UNIT_ID'})


### IPM regions
ipm_regions = gpd.read_file('AirPollution_Data/IPM_Regions_201770405.shp')
zone_to_region = {
    zone: region for region, zones in region_aggregations.items() for zone in zones
}
ipm_regions["model_region"] = ipm_regions["IPM_Region"].map(zone_to_region)
model_regions = ipm_regions.dissolve(by="model_region", as_index=False)

print("Finished Reading Data")

#####################
## Format columns ###
#####################
print("Formatting Data")
existing_gen_units = existing_gen_units.rename(columns={'generator_id': 'EIA_GENERATOR_ID', 'plant_id_eia':'EIA_PLANT_ID'})

## EPA-EIA crosswalk
crosswalk = crosswalk[['CAMD_PLANT_ID', 'CAMD_UNIT_ID', 'CAMD_GENERATOR_ID', 'EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'EIA_UNIT_TYPE']]
crosswalk['EIA_GENERATOR_ID'] = crosswalk['EIA_GENERATOR_ID'].astype(str)

##############
## EIA Data###
##############

# filter out AK and HI
eia860 = eia860[~eia860['State'].isin(['HI', 'AK'])]
eia923_fuels = eia923_fuels[~eia923_fuels['Plant State'].isin(['HI', 'AK'])]
eia923_generators = eia923_generators[~eia923_generators['Plant State'].isin(['HI', 'AK'])]


#rename columns and change formats
eia860 = eia860[['Plant Code', 'Generator ID', 'Nameplate Capacity (MW)', 'Planned Retirement Year', 'Planned Retirement Month', 'Synchronized to Transmission Grid', 'Technology']]
eia860.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'Capacity', 'RetirementYear', 'RetirementMonth', 'SynchronizedToGrid', 'Technology']
eia860['EIA_GENERATOR_ID']=eia860['EIA_GENERATOR_ID'].astype(str)

plants = plants[['Plant Code', 'Longitude', 'Latitude']]
plants.columns = ['EIA_PLANT_ID', 'Longitude', 'Latitude']

eia923_fuels = eia923_fuels[['Plant Id', 'Plant Name', 'Plant State', 'Net Generation\n(Megawatthours)']]
eia923_fuels.columns = ['EIA_PLANT_ID', 'EIA_PLANT_NAME', 'EIA_STATE', 'NET_GEN_PLANT']
eia923_fuels = eia923_fuels.groupby('EIA_PLANT_ID').agg({'NET_GEN_PLANT': 'sum'}).reset_index()

eia923_generators = eia923_generators[['Plant Id', 'Generator Id', 'Net Generation\nYear To Date']]
eia923_generators.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'NET_GEN_GENERATOR']
eia923_generators['EIA_GENERATOR_ID'] = eia923_generators['EIA_GENERATOR_ID'].astype(str)

##############
##EPA data####
##############
pm25['UNITID'] = pm25['UNITID'].astype(str)
pm25 = pm25.groupby(['ORISPL', 'UNITID']).agg({'PM25AN': 'sum'}).reset_index()
pm25.columns = ['facilityId', 'unitId', 'pm25']
pm25['unitId']=pm25['unitId'].astype(str)
pm25['facilityId']=pm25['facilityId'].astype(int)

emissions['unitId']=emissions['unitId'].astype(str)
emissions['facilityId']=emissions['facilityId'].astype(int)

emissions = pd.merge(emissions, pm25, on=['facilityId', 'unitId'], how='left')
emissions['nox_tons'] = emissions['noxMass']
emissions['so2_tons'] = emissions['so2Mass']
emissions['pm25_tons'] = emissions['pm25']

#rename columns
emissions = emissions.rename(columns = {'facilityId': 'CAMD_PLANT_ID', 'unitId': 'CAMD_UNIT_ID'})


#####################################################################################
### 2. Merge EIA and EPA data into existing_gen_units using the EPA-EIA crosswalk
##################################################################################
#join existing_gen_units with crosswalk
existing_gen_units = pd.merge(existing_gen_units, crosswalk, on=['EIA_GENERATOR_ID', 'EIA_PLANT_ID'],how='left')

#in existing_gen_units, there's a fair amount of missing capacities that are available from eia data so I'm going to join in 
#eia860 and then fill in nans
existing_gen_units = pd.merge(existing_gen_units, eia860[['EIA_GENERATOR_ID', 'EIA_PLANT_ID', 'Capacity']], on=['EIA_GENERATOR_ID', 'EIA_PLANT_ID'], how='left')

#need net gen
existing_gen_units = pd.merge(existing_gen_units, eia923_fuels, on=['EIA_PLANT_ID'], how='left')
existing_gen_units = pd.merge(existing_gen_units, eia923_generators, on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID'], how='left')

#lastly, need emissions
existing_gen_units = pd.merge(existing_gen_units, emissions, on=['CAMD_PLANT_ID', 'CAMD_UNIT_ID'], how='left')

#nei emissions
existing_gen_units = pd.merge(existing_gen_units, nei, on=['CAMD_PLANT_ID', 'CAMD_UNIT_ID'], how='left')

#fill in missing capacities
existing_gen_units['capacity_mw']=existing_gen_units['capacity_mw'].combine_first(existing_gen_units['Capacity'])

#########################################################################################
### 3. Impute generation for generators with missing generation.  To do this, I take plant-level generation and distribute that generation to generators based on each generator's capacity.
##########################################################################################

# I'm going to calculate plant-level 'missing generation'
# Then divy up the missing generation to generators according to capacity in MW

summed_plant_gen = existing_gen_units.groupby(['EIA_PLANT_ID', 'planning_year']).agg({'NET_GEN_GENERATOR': 'sum'}).reset_index()
summed_plant_gen.columns=['EIA_PLANT_ID', 'planning_year', 'sum_generator_gen']

existing_gen_units = pd.merge(existing_gen_units, summed_plant_gen, on=['EIA_PLANT_ID', 'planning_year'], how='left')

existing_gen_units['missing_generator_generation']=existing_gen_units['NET_GEN_GENERATOR'].isna().astype(int)
existing_gen_units['missing_generation'] = existing_gen_units['NET_GEN_PLANT'] - existing_gen_units['sum_generator_gen']


missing_generators = existing_gen_units.query('missing_generator_generation==1').\
    groupby(['EIA_PLANT_ID', 'planning_year']).\
    agg({'capacity_mw': 'sum'}).\
    reset_index()
missing_generators.columns=['EIA_PLANT_ID', 'planning_year', 'missing_generator_capacity']

existing_gen_units = pd.merge(existing_gen_units, missing_generators, on=['EIA_PLANT_ID', 'planning_year'], how='left')

## Make imputation

existing_gen_units['pct_missing_capacity'] = (existing_gen_units['capacity_mw']/existing_gen_units['missing_generator_capacity'])*existing_gen_units['missing_generator_generation']
existing_gen_units['imputed_net_gen'] = existing_gen_units['pct_missing_capacity']*existing_gen_units['missing_generation']


#replace missings with imputed
existing_gen_units['NET_GEN_GENERATOR'] = existing_gen_units['NET_GEN_GENERATOR'].combine_first(existing_gen_units['imputed_net_gen'])

#############################################################################################
### 4. Calculate generation-weighted average emissions rates, then use those to fill in generators with missing emissions rates.
############################################################################################## 

#looks like there's broad agreement between camd and nei
#fill in missing camd data with nei data
print("Calculating Emissions Rates")

existing_gen_units['nox_tons'] = existing_gen_units['nox_tons'].combine_first(existing_gen_units['NOX_nei_tons'])
existing_gen_units['so2_tons'] = existing_gen_units['so2_tons'].combine_first(existing_gen_units['SO2_nei_tons'])
existing_gen_units['pm25_tons'] = existing_gen_units['pm25_tons'].combine_first(existing_gen_units['PM25-PRI_nei_tons'])

#get rates
existing_gen_units['nox_rate'] = existing_gen_units['nox_tons']/existing_gen_units['NET_GEN_GENERATOR']
existing_gen_units['so2_rate'] = existing_gen_units['so2_tons']/existing_gen_units['NET_GEN_GENERATOR']
existing_gen_units['pm25_rate'] = existing_gen_units['pm25_tons']/existing_gen_units['NET_GEN_GENERATOR']
existing_gen_units['nh3_rate'] = existing_gen_units['NH3_nei_tons']/existing_gen_units['NET_GEN_GENERATOR']
existing_gen_units['voc_rate'] = existing_gen_units['VOC_nei_tons']/existing_gen_units['NET_GEN_GENERATOR']


#for now I'm going to omit units with negative net_gen since it doesn't make sense for them to have negative 'rates'
#I'll replace the rates with sample weighted-means
existing_gen_units.loc[existing_gen_units['nox_rate']<0, 'nox_rate']=np.nan
existing_gen_units.loc[existing_gen_units['pm25_rate']<0, 'pm25_rate']=np.nan
existing_gen_units.loc[existing_gen_units['so2_rate']<0, 'so2_rate']=np.nan
existing_gen_units.loc[existing_gen_units['nh3_rate']<0, 'nh3_rate']=np.nan
existing_gen_units.loc[existing_gen_units['voc_rate']<0, 'voc_rate']=np.nan

existing_gen_units.loc[existing_gen_units['nox_rate'].isin([np.inf]), 'nox_rate']=np.nan
existing_gen_units.loc[existing_gen_units['pm25_rate'].isin([np.inf]), 'pm25_rate']=np.nan
existing_gen_units.loc[existing_gen_units['so2_rate'].isin([np.inf]), 'so2_rate']=np.nan
existing_gen_units.loc[existing_gen_units['nh3_rate'].isin([np.inf]), 'nh3_rate']=np.nan
existing_gen_units.loc[existing_gen_units['voc_rate'].isin([np.inf]), 'voc_rate']=np.nan

############
## Calculate weighted average emissions rates by technology-planning year

# Define a function to calculate weighted average handling NaN values

def weighted_average(df):
    weighted_avgs = {}
    for col in df.columns:
        if '_rate' in col:  # Consider columns containing '_rate'
            df_valid = df.dropna(subset=[col, 'NET_GEN_GENERATOR'])
            if len(df_valid) == 0 or df_valid['NET_GEN_GENERATOR'].sum() == 0:
                weighted_avgs[col] = np.nan  # Return NaN if all weights in the group are zero
            else:
                weighted_avgs[col] = np.average(df_valid[col], weights=df_valid['NET_GEN_GENERATOR'])
    return pd.Series(weighted_avgs)

technology_rates = existing_gen_units.groupby(['technology', 'planning_year']).apply(weighted_average).reset_index()


#Fill in missings with entries from technology_rates

technology_rates = technology_rates[['technology', 'planning_year', 'nox_rate', 'pm25_rate', 'so2_rate', 'voc_rate', 'nh3_rate']]
technology_rates.columns = ['technology', 'planning_year', 'noxrate_imputed', 'pm25rate_imputed', 'so2rate_imputed', 'vocrate_imputed', 'nh3rate_imputed']

existing_gen_units = pd.merge(existing_gen_units, technology_rates, on=['technology', 'planning_year'], how='left')

############################################################################################
### 5. Calculate marginal emissions by multiplying rates by that generator's share of capacity for its cluster.
############################################################################################ 
print("Calculating Cluster Emissions Rates")
column = 'capacity_mw'

technology_year_total = existing_gen_units.groupby(['Resource', 'planning_year']).agg({column : 'sum'}).reset_index()
technology_year_total.columns = ['Resource', 'planning_year', 'technology_total']

#merge in total capacity
existing_gen_units = pd.merge(existing_gen_units, technology_year_total, on=['Resource', 'planning_year'], how='left')


existing_gen_units['pct_total']=existing_gen_units[column]/existing_gen_units['technology_total']

existing_gen_units['nox_predicted']=existing_gen_units['pct_total']*existing_gen_units['noxrate_imputed']
existing_gen_units['so2_predicted']=existing_gen_units['pct_total']*existing_gen_units['so2rate_imputed']
existing_gen_units['pm25_predicted']=existing_gen_units['pct_total']*existing_gen_units['pm25rate_imputed']
existing_gen_units['voc_predicted']=existing_gen_units['pct_total']*existing_gen_units['vocrate_imputed']
existing_gen_units['nh3_predicted']=existing_gen_units['pct_total']*existing_gen_units['nh3rate_imputed']


#merge in plant locations
existing_gen_units = pd.merge(existing_gen_units, plants, on=['EIA_PLANT_ID'], how='left')


#Add in CCS
# It looks like all new NGCT has heat rate of 6.36 and all new CCCCS has heat rate of 7.16
# For now, I'm just going to run with this
appendrows = technology_rates[technology_rates['technology']=='Natural Gas Fired Combined Cycle']
appendrows['technology'] = 'Natural Gas Fired Combined Cycle With CCS'

ccspenalty = 7.16/6.36

ratecolumns=['noxrate_imputed', 'so2rate_imputed', 'pm25rate_imputed', 'nh3rate_imputed', 'vocrate_imputed']
appendrows[ratecolumns]=appendrows[ratecolumns].apply(lambda x: x * ccspenalty)
technology_rates = pd.concat([technology_rates, appendrows])


### Now deal with new generation
new_sites = eia860.dropna(subset=["Technology"])
new_sites = new_sites[new_sites['Technology'].str.contains('Natural Gas')]
new_sites = pd.merge(new_sites, plants, how='left', on='EIA_PLANT_ID')

#make retired sites a geopandas
geometry = [Point(lon, lat) for lon, lat in zip(new_sites['Longitude'], new_sites['Latitude'])]
new_sites = gpd.GeoDataFrame(new_sites, geometry=geometry, crs='EPSG:4326')


#model_regions['region'] = model_regions['IPM_Region'].map({region: val for val, regions in cost_multiplier_region_map.items() for region in regions})
model_regions = model_regions.to_crs('EPSG:4326')

new_sites = gpd.sjoin(new_sites, model_regions, how="left", op="intersects")

new_sites_df = pd.DataFrame(new_sites)
new_sites_df = new_sites_df.dropna(subset=['model_region'])

# look for plants matched with multiple model regions
# For now I'm just going to take the top row, which will lead to a couple inconsistencies
#hopefully the shapefiles will become in better shape
new_sites_df = new_sites_df.groupby(['EIA_GENERATOR_ID', 'EIA_PLANT_ID']).first().reset_index()

# #want to distribute new capacity evenly to retired sites
# #be agnostic about type of natural gas plant -- eg new cc capacity can go at an old ct site
new_sites_total= new_sites_df.groupby(['model_region']).agg({'Capacity':'sum'}).reset_index()
new_sites_total.columns = ['model_region', 'Tot_Capacity']

new_sites_df = pd.merge(new_sites_df, new_sites_total, how='left', on=['model_region'])
new_sites_df['pct_total']=new_sites_df['Capacity']/new_sites_df['Tot_Capacity']

new_sites_df = new_sites_df[['pct_total', 'Longitude', 'Latitude', 'model_region']]
new_sites_df = new_sites_df.rename(columns={'model_region':'region'})

newgenerators = generators_data[generators_data['GENERATION_PROJECT'].str.contains('naturalgas_')]
newgenerators.loc[newgenerators['GENERATION_PROJECT'].str.contains('_ccavg'), 'technology']= 'Natural Gas Fired Combined Cycle'
newgenerators.loc[newgenerators['GENERATION_PROJECT'].str.contains('_ctavg'), 'technology']= 'Natural Gas Fired Combustion Turbine'
newgenerators.loc[newgenerators['GENERATION_PROJECT'].str.contains('_ccccsavg'), 'technology']= 'Natural Gas Fired Combined Cycle With CCS'


newgenerators.loc[newgenerators['GENERATION_PROJECT'].str.contains('_cc_'), 'technology']= 'Natural Gas Fired Combined Cycle'
newgenerators.loc[newgenerators['GENERATION_PROJECT'].str.contains('_ct_'), 'technology']= 'Natural Gas Fired Combustion Turbine'
newgenerators.loc[newgenerators['GENERATION_PROJECT'].str.contains('_cc_95_ccs'), 'technology']= 'Natural Gas Fired Combined Cycle With CCS'

newgenerators = pd.merge(newgenerators, technology_rates, how='left', on=['technology'])
newgenerators = newgenerators.merge(new_sites_df, how="cross")
newgenerators = newgenerators[newgenerators['gen_load_zone']==newgenerators['region']]

newgenerators['nox_predicted']=newgenerators['pct_total']*newgenerators['noxrate_imputed']
newgenerators['so2_predicted']=newgenerators['pct_total']*newgenerators['so2rate_imputed']
newgenerators['pm25_predicted']=newgenerators['pct_total']*newgenerators['pm25rate_imputed']
newgenerators['voc_predicted']=newgenerators['pct_total']*newgenerators['vocrate_imputed']
newgenerators['nh3_predicted']=newgenerators['pct_total']*newgenerators['nh3rate_imputed']

newgenerators = newgenerators[['Longitude', 'Latitude', 'GENERATION_PROJECT', 'planning_year', 'nox_predicted', 'so2_predicted', 'pm25_predicted', 'voc_predicted', 'nh3_predicted']]

#bind all emissions sources together

existing_gen_units = existing_gen_units[['Longitude', 'Latitude', 'Resource', 'planning_year', 'nox_predicted', 'so2_predicted', 'pm25_predicted', 'voc_predicted', 'nh3_predicted']]
emissions=pd.concat([existing_gen_units, newgenerators], ignore_index=True)
emissions['Resource']= emissions['Resource'].fillna(emissions['GENERATION_PROJECT'])

print(emissions.shape[0])
#aggregate emissions in same spot/cluster
emissions=emissions.groupby(['Longitude', 'Latitude', 'Resource', 'planning_year']).agg({'nox_predicted':'sum', 'so2_predicted':'sum', 'pm25_predicted':'sum', 'voc_predicted':'sum', 'nh3_predicted':'sum'}).reset_index()
print(emissions.shape[0])


# ## 7. Split the emissions output by planning year and write to shapefiles.
print("Writing emissions data to shapefiles")
for input,year in year_inputs.items():
    emissions_temp = emissions[emissions['planning_year']==year]
    
    emissions_temp.columns = ['Longitude', 'Latitude', 'Resource', 'planning_year', 'NOx', 'SOx', 'PM2_5', 'VOC', 'NH3']
    print(emissions_temp.shape[0])

    emissions_temp = gpd.GeoDataFrame(
        emissions_temp, geometry = gpd.points_from_xy(emissions_temp.Longitude, emissions_temp.Latitude), crs='EPSG:4326')
    emissions_temp = emissions_temp.dropna().reset_index(drop=True)

    emissions_temp.to_file(filename='MIP_Air_OutData/'+scenario+'_simplified_marginal_emissions_'+str(year)+'.shp')


