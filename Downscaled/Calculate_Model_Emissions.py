globals().clear()


import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import geopandas as gpd
import fiona
import math
from shapely.geometry import Point

os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')

#pull in settings from settings file
from MIP_AirPollution.Downscaled.settings import *
scenario='current_policies_short'
scenario_name_2 = 'short-current-policies'
model='GenX'

###################################
## Read in EIA and EPA Data #######
###################################

#EIA-EPA Crosswalk
crosswalk = pd.read_csv(eia_datapath +"/epa_eia_crosswalk.csv")

# EIA 860 for Generator Info
eia860 = pd.read_excel(eia_datapath +"/eia860/3_1_Generator_Y2020.xlsx", skiprows=1)

# EIA923 for Generation Info
eia923_fuels = pd.read_excel(eia_datapath +"/eia923/EIA923_Schedules_2_3_4_5_M_12_2020_Final_Revision.xlsx", sheet_name='Page 1 Generation and Fuel Data', skiprows=5)
eia923_generators = pd.read_excel(eia_datapath +"/eia923/EIA923_Schedules_2_3_4_5_M_12_2020_Final_Revision.xlsx", sheet_name='Page 4 Generator Data', skiprows=5)

### Format Rows and Clean ####

## EPA-EIA crosswalk
crosswalk = crosswalk[['CAMD_PLANT_ID', 'CAMD_UNIT_ID', 'CAMD_GENERATOR_ID', 'EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'EIA_UNIT_TYPE']]
crosswalk['EIA_GENERATOR_ID'] = crosswalk['EIA_GENERATOR_ID'].astype(str)

# filter out AK and HI
eia860 = eia860[~eia860['State'].isin(['HI', 'AK'])]
eia923_fuels = eia923_fuels[~eia923_fuels['Plant State'].isin(['HI', 'AK'])]
eia923_generators = eia923_generators[~eia923_generators['Plant State'].isin(['HI', 'AK'])]


#rename columns and change formats
eia860 = eia860[['Plant Code', 'Generator ID', 'Nameplate Capacity (MW)', 'Planned Retirement Year', 'Planned Retirement Month', 'Synchronized to Transmission Grid', 'Technology']]
eia860.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'Capacity', 'RetirementYear', 'RetirementMonth', 'SynchronizedToGrid', 'Technology']
eia860['EIA_GENERATOR_ID']=eia860['EIA_GENERATOR_ID'].astype(str)

eia923_fuels = eia923_fuels[['Plant Id', 'Plant Name', 'Plant State', 'Net Generation\n(Megawatthours)']]
eia923_fuels.columns = ['EIA_PLANT_ID', 'EIA_PLANT_NAME', 'EIA_STATE', 'NET_GEN_PLANT']
eia923_fuels = eia923_fuels.groupby('EIA_PLANT_ID').agg({'NET_GEN_PLANT': 'sum'}).reset_index()

eia923_generators = eia923_generators[['Plant Id', 'Generator Id', 'Net Generation\nYear To Date']]
eia923_generators.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'NET_GEN_GENERATOR']
eia923_generators['EIA_GENERATOR_ID'] = eia923_generators['EIA_GENERATOR_ID'].astype(str)

###### Emissions ##########

emissions = pd.read_csv("Data/CAMD/facilities_emissions.csv")
#only want year 2020
emissions = emissions.query('year==2020')

# PM25
pm25 = pd.read_excel("Data/eGRID2020 DRAFT PM Emissions.xlsx", sheet_name="2020 PM Unit-level Data", skiprows=1)

## Read in and format NEI ####

#nei data gives values for ammonia, vocs, and also pm2.5
#It also has so2 and nox output that mostly matches camd data
#I'll prioritise camd data, but fill in any missings with nei

#cems noncems just distinguish whether emissions were continuously monitored or imputed
#doesn't really matter for our purposes
nei_cems = pd.read_csv('Data/NEI/egucems_SmokeFlatFile_2020NEI_POINT_20230128_27mar2023_v1.csv', skiprows=16)
nei_noncems = pd.read_csv('Data/NEI/egunoncems_SmokeFlatFile_2020NEI_POINT_20230128_27mar2023_v0.csv', skiprows=15)
nei = pd.concat([nei_cems, nei_noncems])

#pull out the relevant pollutants
nei = nei.groupby(['oris_facility_code', 'oris_boiler_id', 'poll']).agg({'ann_value': 'sum'}).reset_index()
nei = nei[nei['poll'].isin(['CO', 'NH3', 'NOX', 'PM25-PRI', 'SO2', 'SO4', 'VOC'])]

#put weights in pounds
nei['poll']=nei['poll']+'_nei_tons'
nei['ann_value']=nei['ann_value']
nei = nei.pivot(index=['oris_facility_code', 'oris_boiler_id'], columns='poll', values='ann_value').reset_index()
nei = nei.rename(columns = {'oris_facility_code': 'CAMD_PLANT_ID', 'oris_boiler_id': 'CAMD_UNIT_ID'})

############################
## Format and clean CAMD ###
############################

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


#######################################
## Read In Existing Gen Units #########
#######################################
existing_gen_units = pd.DataFrame()
# get years and file input names
for filename, year in year_inputs.items():
    existing_gen_units_temp = pd.read_csv('Data/GenX inputs/' + scenario + '/' + scenario + '/Inputs/Inputs_' + filename + '/extra_outputs/existing_gen_units.csv')
    existing_gen_units_temp['planning_year'] = year
    existing_gen_units = pd.concat([existing_gen_units, existing_gen_units_temp], ignore_index=True)

#filter out by retirement year
existing_gen_units = existing_gen_units.query('retirement_year>=planning_year')


## Format columns ###

# existing_gen_units
existing_gen_units['plant_id_eia']=existing_gen_units['plant_id_eia'].astype(int)
existing_gen_units['generator_id']=existing_gen_units['generator_id'].astype(str)

existing_gen_units = existing_gen_units.rename(columns={'generator_id': 'EIA_GENERATOR_ID', 'plant_id_eia':'EIA_PLANT_ID'})

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


##################################
## Calculate Rates ###############
##################################
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


############
## Calculate weighted average emissions rates by technology-planning year

# Define a function to calculate weighted average handling NaN values

def weighted_average(df):
    weighted_avgs = {}
    for col in df.columns:
        if '_rate' in col:  # Consider columns containing '_rate'
            df_valid = df.dropna(subset=[col, 'NET_GEN_GENERATOR'])
            df_valid =df_valid[df_valid['NET_GEN_GENERATOR']!=0]
            if len(df_valid) == 0 or df_valid['NET_GEN_GENERATOR'].sum() == 0:
                weighted_avgs[col] = np.nan  # Return NaN if all weights in the group are zero
            else:
                weighted_avgs[col] = np.average(df_valid[col], weights=df_valid['NET_GEN_GENERATOR'])
    return pd.Series(weighted_avgs)

technology_rates = existing_gen_units.groupby(['technology', 'planning_year']).apply(weighted_average).reset_index()

#want one backup thats overall rates
technology_rates_overall = existing_gen_units.query('planning_year==2027').groupby(['technology']).apply(weighted_average).reset_index()
#Ok last thing to do is fill in missings

technology_rates = technology_rates[['technology', 'planning_year', 'nox_rate', 'pm25_rate', 'so2_rate', 'voc_rate', 'nh3_rate']]
technology_rates.columns = ['technology', 'planning_year', 'noxrate_imputed', 'pm25rate_imputed', 'so2rate_imputed', 'vocrate_imputed', 'nh3rate_imputed']

existing_gen_units = pd.merge(existing_gen_units, technology_rates, on=['technology', 'planning_year'], how='left')

existing_gen_units['noxrate_imputed'] = existing_gen_units['nox_rate'].combine_first(existing_gen_units['noxrate_imputed'])
existing_gen_units['so2rate_imputed'] = existing_gen_units['so2_rate'].combine_first(existing_gen_units['so2rate_imputed'])
existing_gen_units['pm25rate_imputed'] = existing_gen_units['pm25_rate'].combine_first(existing_gen_units['pm25rate_imputed'])
existing_gen_units['vocrate_imputed'] = existing_gen_units['voc_rate'].combine_first(existing_gen_units['vocrate_imputed'])
existing_gen_units['nh3rate_imputed'] = existing_gen_units['nh3_rate'].combine_first(existing_gen_units['nh3rate_imputed'])

###############
## Little detour here to calculate year 2020 emissions
##This will serve as a gut-check and I'll output it so that in the results you can see the decline from 2020 --> 2030
## First I'll just take nei and camd data and sum it.
## Then I'll take observed net gen and multiply it by my imputed emissions rates
## Hopefully emissions will be close

reported_emissions_2020 = pd.merge(emissions, nei, how='outer', on=['CAMD_UNIT_ID', 'CAMD_PLANT_ID']).reset_index()
reported_emissions_2020['nox_tons'] = reported_emissions_2020['nox_tons'].combine_first(existing_gen_units['NOX_nei_tons'])
reported_emissions_2020['pm25_tons'] = reported_emissions_2020['pm25_tons'].combine_first(existing_gen_units['PM25-PRI_nei_tons'])
reported_emissions_2020['so2_tons'] = reported_emissions_2020['so2_tons'].combine_first(existing_gen_units['SO2_nei_tons'])
print(reported_emissions_2020[['nox_tons', 'pm25_tons', 'so2_tons', 'NH3_nei_tons', 'VOC_nei_tons']].sum())

test_emissions_2020 = pd.merge(eia860[['EIA_GENERATOR_ID', 'EIA_PLANT_ID', 'Capacity', 'Technology']], eia923_generators, on=['EIA_GENERATOR_ID', 'EIA_PLANT_ID'], how='left')
test_emissions_2020 = pd.merge(test_emissions_2020, eia923_fuels, on=['EIA_PLANT_ID'])
pct_capacity_2020 = test_emissions_2020.groupby(['EIA_PLANT_ID']).agg({'Capacity':'sum'}).reset_index()
pct_capacity_2020 = pct_capacity_2020.rename(columns={'Capacity':'sum_plant_capacity'})
test_emissions_2020 = pd.merge(test_emissions_2020, pct_capacity_2020, how='left', on='EIA_PLANT_ID')
test_emissions_2020['pct_capacity'] = test_emissions_2020['Capacity']/test_emissions_2020['sum_plant_capacity']
test_emissions_2020['predicted_gen']=test_emissions_2020['pct_capacity']*test_emissions_2020['NET_GEN_PLANT']

test_emissions_2020 = test_emissions_2020.rename(columns={'Technology':'technology'})
test_emissions_2020 = pd.merge(test_emissions_2020, technology_rates[technology_rates['planning_year']==2030], how='left', on=['technology'])

#replace the few negative net gens with zero
test_emissions_2020.loc[test_emissions_2020['predicted_gen']<0, 'predicted_gen']=0
test_emissions_2020 = test_emissions_2020[test_emissions_2020['predicted_gen']>0]

test_emissions_2020['nox_predicted']=test_emissions_2020['predicted_gen']*test_emissions_2020['noxrate_imputed']
test_emissions_2020['so2_predicted']=test_emissions_2020['predicted_gen']*test_emissions_2020['so2rate_imputed']
test_emissions_2020['pm25_predicted']=test_emissions_2020['predicted_gen']*test_emissions_2020['pm25rate_imputed']
test_emissions_2020['voc_predicted']=test_emissions_2020['predicted_gen']*test_emissions_2020['vocrate_imputed']
test_emissions_2020['nh3_predicted']=test_emissions_2020['predicted_gen']*test_emissions_2020['nh3rate_imputed']


test_emissions_2020 = test_emissions_2020[(test_emissions_2020['nox_predicted'] != 0) | (test_emissions_2020['so2_predicted'] != 0) | (test_emissions_2020['pm25_predicted'] != 0) | (test_emissions_2020['voc_predicted'] != 0) | (test_emissions_2020['nh3_predicted'] != 0)]
#drop if all predicted emissions are 0
print(test_emissions_2020[['nox_predicted', 'so2_predicted', 'pm25_predicted', 'voc_predicted', 'nh3_predicted']].sum())

#looks pretty close to me
#test_emissions_2020 is actually what I'm going to bind into emissions and analyze in InMap

########################################################################################################
## 5. Calculate aggregate emissions by multiplying rates by model-output specified generation. 
#######################################################################################################

generation = pd.read_csv("MIP_results_comparison/"+scenario_name_2+"/"+model+"_results_summary/generation.csv")
generator_inputs = pd.read_csv("MIP_results_comparison/"+scenario_name_2+'/'+model+'_op_inputs/Inputs/Inputs_p1/Generators_data.csv')

#Also need capacity to allocate new generation/capacity to brownfield nat gas sites
capacity = pd.read_csv("MIP_results_comparison/"+scenario_name_2+"/"+model+"_results_summary/resource_capacity.csv")
capacity.columns = capacity.columns.map(lambda x: x.lower())
capacity = capacity[capacity['unit']=='MW']

capacity['tech_type'] = np.where(
    capacity['resource_name'].str.contains('naturalgas_hframe_cc'),
    'Natural Gas CC',
    capacity['tech_type']
)

capacity['tech_type'] = np.where(
    capacity['resource_name'].str.contains('naturalgas_fframe_ct'),
    'Natural Gas CT',
    capacity['tech_type']
)

capacity['tech_type'] = np.where(
    capacity['resource_name'].str.contains('naturalgas_hframe_cc_95_ccs'),
    'Natural Gas CCS',
    capacity['tech_type']
)
capacity = capacity.groupby(['zone', 'resource_name', 'tech_type', 'planning_year']).agg({'start_value': 'sum', 'end_value': 'sum'}).reset_index()


#want total sum of existing gen capacity or netgen by planning period to allocate generation
technology_year_total = existing_gen_units.groupby(['Resource', 'planning_year']).agg({'capacity_mw' : 'sum'}).reset_index()
technology_year_total.columns = ['Resource', 'planning_year', 'technology_total']

#merge in total capacity or total net gen
existing_gen_units = pd.merge(existing_gen_units, technology_year_total, on=['Resource', 'planning_year'], how='left')

#merge in model generation
generation = generation.rename(columns={'resource_name':'Resource'})
existing_gen_units = pd.merge(existing_gen_units, generation, on=['Resource', 'planning_year'], how='left')

#add in new gen
newgeneration = generation[generation['Resource'].str.contains('naturalgas', na=False)]

###################################################
## Throw an error if there's new coal/biomass #####
###################################################
def check_value(value):
    if value > 0:
        raise ValueError("New coal/biomass capacity added.  Newgeneration code is only valid for new nat gas.")

#check that new capacity goes down for coal/biomass
capacity.sort_values(by='planning_year', inplace=True)
capacity['lag_capacity'] = capacity.groupby('resource_name')['end_value'].shift()
max_capacity_change = capacity[capacity['tech_type'].isin(['Coal', 'Biomass'])]
max_capacity_change = max_capacity_change.dropna(subset=['lag_capacity'])
max_capacity_change['dif']=max_capacity_change['end_value']-max_capacity_change['lag_capacity']
max_capacity_change = max_capacity_change['dif'].max()

try:
    check_value(max_capacity_change)
except ValueError as e:
    print(f"Error: {e}")

#ok now save new capacity for natural gas -- really the only thing we care about
capacity = capacity[capacity['resource_name'].str.contains('_naturalgas')]
capacity.loc[capacity['resource_name'].str.contains('_ccavg'), 'technology']= 'Natural Gas Fired Combined Cycle'
capacity.loc[capacity['resource_name'].str.contains('_ctavg'), 'technology']= 'Natural Gas Fired Combustion Turbine'

existing_gen_units['pct_total']=existing_gen_units['capacity_mw']/existing_gen_units['technology_total']
existing_gen_units['predicted_gen']=existing_gen_units['value']*existing_gen_units['pct_total']

existing_gen_units['nox_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['noxrate_imputed']
existing_gen_units['so2_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['so2rate_imputed']
existing_gen_units['pm25_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['pm25rate_imputed']
existing_gen_units['voc_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['vocrate_imputed']
existing_gen_units['nh3_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['nh3rate_imputed']

#merge in plant locations
plants = pd.read_excel('Data/eia860/2___Plant_Y2017.xlsx', skiprows=1)
plants = plants[['Plant Code', 'Longitude', 'Latitude']]
plants.columns = ['EIA_PLANT_ID', 'Longitude', 'Latitude']

existing_gen_units = pd.merge(existing_gen_units, plants, on=['EIA_PLANT_ID'], how='left')
test_emissions_2020 = pd.merge(test_emissions_2020, plants, on=['EIA_PLANT_ID'])

##########
## New sources
existing_gen_units['operating_date']=pd.to_datetime(existing_gen_units['operating_date'])

## Calculate emissions rates for new sources
technology_rates_newsources = existing_gen_units[existing_gen_units['operating_date']>=pd.to_datetime('2016-01-01')].groupby(['technology', 'planning_year']).apply(weighted_average).reset_index()

#apply a penalty to ccs (set in settings file)
appendrows = technology_rates_newsources[technology_rates_newsources['technology']=='Natural Gas Fired Combined Cycle']
appendrows['technology'] = 'Natural Gas Fired Combined Cycle With CCS'
ratecolumns=['nox_rate', 'so2_rate', 'pm25_rate', 'nh3_rate', 'voc_rate']
appendrows[ratecolumns]=appendrows[ratecolumns].apply(lambda x: x * ccs_heatrate_penalty)
technology_rates_newsources = pd.concat([technology_rates_newsources, appendrows])

### Now deal with new generation
newgeneration['technology']=np.nan
newgeneration.loc[newgeneration['Resource'].str.contains('_ccavg'), 'technology']= 'Natural Gas Fired Combined Cycle'
newgeneration.loc[newgeneration['Resource'].str.contains('_ctavg'), 'technology']= 'Natural Gas Fired Combustion Turbine'
newgeneration.loc[newgeneration['Resource'].str.contains('_ccccsavg'), 'technology']= 'Natural Gas Fired Combined Cycle With CCS'

#Isolate retired sites -- dates and locations
retired_sites = existing_gen_units.groupby(['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'region', 'technology'])['planning_year'].max().reset_index()
retired_sites['planning_year']=retired_sites['planning_year']+10
retired_sites = pd.merge(eia860, retired_sites, how='left', on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID']).reset_index()
retired_sites = pd.merge(retired_sites, plants, how='left', on=['EIA_PLANT_ID'])

#get retirement date from eia860, then round up to nearest 10
retired_sites['RetirementPeriod860']=pd.to_numeric(retired_sites['RetirementYear'], errors='coerce', downcast='float')
retired_sites['RetirementPeriod860']=retired_sites['RetirementPeriod860']/10
retired_sites['RetirementPeriod860']=retired_sites['RetirementPeriod860'].apply(np.ceil)*10

retired_sites['RetirementPeriod'] = retired_sites['planning_year'].combine_first(retired_sites['RetirementPeriod860'])
ipm_regions = gpd.read_file('Data/IPM_Regions/national_emm_boundaries.shp')

#make retired sites a geopandas
geometry = [Point(lon, lat) for lon, lat in zip(retired_sites['Longitude'], retired_sites['Latitude'])]
retired_sites_geo = gpd.GeoDataFrame(retired_sites, geometry=geometry, crs='EPSG:4326')

#ipm_regions['region'] = ipm_regions['IPM_Region'].map({region: val for val, regions in cost_multiplier_region_map.items() for region in regions})
ipm_regions = ipm_regions.to_crs('EPSG:4326')

retired_sites_geo = gpd.sjoin(retired_sites_geo, ipm_regions, how="left", op="intersects")

# print(ipm_regions.head)
# ipm_regions[ipm_regions['model_regi'].isin(['PJMW', 'PJME'])].plot(column='model_regi',edgecolor='black', linewidth=1, legend=True, alpha=0.3)
# plt.show()

## There's some overlapping between regions which leads to multiple matches for some retired units which messes things up

retired_sites_df = pd.DataFrame(retired_sites_geo[['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'region_left', 'model_regi','Technology', 'Longitude', 'Latitude', 'planning_year', 'RetirementPeriod860','RetirementPeriod', 'Capacity']])
retired_sites_df = retired_sites_df.dropna(subset=['RetirementPeriod','model_regi'])
retired_sites_df = retired_sites_df[retired_sites_df['Technology'].str.contains('Natural Gas')]

# look for plants matched with multiple model regions
rowcount = retired_sites_df.groupby(['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'RetirementPeriod']).size().reset_index()
rowcount.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'RetirementPeriod', 'rowcount']
retired_sites_df = pd.merge(retired_sites_df, rowcount, how='left', on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'RetirementPeriod'])
#drop ones where model_regi!=zone
cond1 = (retired_sites_df['model_regi']!=retired_sites_df['region_left'])
cond2 = (retired_sites_df['rowcount']>1)
retired_sites_df = retired_sites_df[~(cond1 & cond2)]


#make a panel of retired sites
#make a panel of retired sites
dataframes = []
for key, year in year_inputs.items():
    df = retired_sites_df[retired_sites_df['RetirementPeriod'] <= year]
    df['planning_year']=year
    dataframes.append(df)

retired_sites_df = pd.concat(dataframes).reset_index(drop=True)

#want to distribute new capacity evenly to retired sites
#be agnostic about type of natural gas plant -- eg new cc capacity can go at an old ct site
retired_sites_tech_total= retired_sites_df.groupby(['model_regi', 'planning_year']).agg({'Capacity':'sum'}).reset_index()
retired_sites_tech_total.columns = ['model_regi','planning_year', 'Tech_Tot_Retired_Capacity']

retired_sites_df = pd.merge(retired_sites_df, retired_sites_tech_total, how='left', on=['planning_year', 'model_regi'])
retired_sites_df['Pct_retired_capacity']=retired_sites_df['Capacity']/retired_sites_df['Tech_Tot_Retired_Capacity']
retired_sites_df = retired_sites_df.rename(columns={'model_regi': 'zone'})
#save remaining capacity will get updated iteratively
retired_sites_df['RemainingCapacity']=retired_sites_df['Capacity']
print(retired_sites_df.shape[0])


techlist = ['cc_moderate_0', 'ct_moderate_0', 'cc_95_ccs']
newgen = pd.DataFrame()
excess = pd.DataFrame()

for tech in techlist:
    capacity_temp = capacity[capacity['resource_name'].str.contains(tech)]
    retired_sites_temp = pd.merge(retired_sites_df, capacity_temp, how='outer', on=['zone', 'planning_year'])  #outer catches all of the region-years with new capacity but no retired plants
    retired_sites_temp['newcapacity'] = retired_sites_temp['Pct_retired_capacity']*retired_sites_temp['end_value']

    #save excess to be distributed to existing plants as a column value
    retired_sites_temp['excess_capacity'] = retired_sites_temp['RemainingCapacity']-retired_sites_temp['newcapacity']
    retired_sites_temp['excess_capacity'][retired_sites_temp['excess_capacity'].isna()]=-1*retired_sites_temp['end_value'][retired_sites_temp['excess_capacity'].isna()]

    #limit new capacity to be no greater than retired capacity
    retired_sites_temp['newcapacity']=retired_sites_temp[['RemainingCapacity', 'newcapacity']].min(axis=1)

    #save excess
    excess_temp = retired_sites_temp[retired_sites_temp['excess_capacity']<0]
    excess_temp = excess_temp.groupby(['planning_year', 'resource_name', 'zone']).agg({'excess_capacity':'sum'}).reset_index()
    excess = pd.concat([excess, excess_temp], ignore_index=True)

    #save new capacity
    retired_sites_newgen = retired_sites_temp.dropna(subset=['Capacity'])
    retired_sites_newgen = retired_sites_newgen[['newcapacity', 'resource_name','planning_year', 'Longitude', 'Latitude']]
    newgen = pd.concat([newgen, retired_sites_newgen], ignore_index=True)

    #update remaining capacity
    retired_sites_temp = retired_sites_temp.dropna(subset=['Capacity'])
    retired_sites_temp['RemainingCapacity']=retired_sites_temp['Capacity']-retired_sites_temp['newcapacity']
    retired_sites_temp = retired_sites_temp[['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'RemainingCapacity', 'planning_year']]
    retired_sites_df = pd.merge(retired_sites_df, retired_sites_temp, how='left', on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'planning_year'])
    retired_sites_df['RemainingCapacity']=retired_sites_df['RemainingCapacity_y']
    retired_sites_df.drop(['RemainingCapacity_x', 'RemainingCapacity_y'], axis=1, inplace=True)
    print(retired_sites_df.shape[0])


##########
## Now distribute excess gen to existing plants
newgen_existingunits = existing_gen_units.copy()
newgen_existingunits = newgen_existingunits[newgen_existingunits['technology'].str.contains('Natural Gas')]
#merge in total capacity or total net gen
excess.columns = ['planning_year', 'resource_name', 'region', 'excess_capacity']
newgen_existingunits = pd.merge(newgen_existingunits, excess, on=['planning_year', 'region'], how='left')

technology_year_total = newgen_existingunits.groupby(['resource_name', 'planning_year', 'region']).agg({'capacity_mw' : 'sum'}).reset_index()
technology_year_total.columns = ['resource_name', 'planning_year', 'region', 'technology_total']
newgen_existingunits = pd.merge(newgen_existingunits, technology_year_total, how='left', on=['resource_name', 'planning_year', 'region'])

newgen_existingunits['pct_total']=newgen_existingunits['capacity_mw']/newgen_existingunits['technology_total_y']
test = newgen_existingunits.groupby(['resource_name', 'planning_year', 'region']).agg({'pct_total':'sum'}).reset_index()
newgen_existingunits['newcapacity']=newgen_existingunits['excess_capacity']*newgen_existingunits['pct_total']*-1

newgen_existingunits = newgen_existingunits[['newcapacity', 'region', 'planning_year', 'resource_name', 'Longitude', 'Latitude', 'EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'pct_total']]

newgen = pd.concat([newgen, newgen_existingunits], ignore_index=True)
newgen['retiredsite']=newgen['EIA_PLANT_ID'].isna()

######
# Test to see if you allocated the correct amount of new capacity
test = newgen_existingunits.groupby(['resource_name', 'planning_year', 'region']).agg({'pct_total':'sum'}).reset_index()
test = newgen.groupby(['resource_name', 'planning_year', 'retiredsite']).agg({'newcapacity':'sum', 'pct_total':'sum'}).reset_index()
test = newgen.groupby(['resource_name', 'planning_year']).agg({'newcapacity':'sum', 'pct_total':'sum'})
test = pd.merge(test, capacity, how='left', on=['resource_name', 'planning_year'])
test['dif'] = test['end_value']-test['newcapacity']
test['dif'] = test['dif'].abs()
maxdif = test['dif'].max()
def check_value(value):
    if value > 0.001:  #gives a little bit of wiggle room
        raise ValueError("New capacity was not allocated correctly. Check code.")

try:
    check_value(maxdif)
except ValueError as e:
    print(f"Error: {e}")

#################
## Distribute newgeneration to newgen (capacities) weighted by capacity

newgen = newgen.rename(columns={'resource_name': 'Resource'})
newgen = pd.merge(newgen, newgeneration, on=['Resource', 'planning_year'], how='left')
newgen = pd.merge(newgen, technology_rates_newsources, on=['technology', 'planning_year'])
#############
## Same schtick as before - determine a source's share of cluster-level capacity, then allocate generation based on that percentage

newgen_cap_totals = newgen.groupby(['Resource', 'planning_year']).agg({'newcapacity':'sum'}).reset_index()
newgen_cap_totals.columns = ['Resource', 'planning_year', 'sum_tot_cap']

newgen = pd.merge(newgen, newgen_cap_totals, how='left', on=['Resource', 'planning_year'])

newgen['pct_cap']=newgen['newcapacity']/newgen['sum_tot_cap']
newgen['predicted_gen']=newgen['value']*newgen['pct_cap']

newgen['nox_predicted']=newgen['predicted_gen']*newgen['nox_rate']
newgen['so2_predicted']=newgen['predicted_gen']*newgen['so2_rate']
newgen['pm25_predicted']=newgen['predicted_gen']*newgen['pm25_rate']
newgen['voc_predicted']=newgen['predicted_gen']*newgen['voc_rate']
newgen['nh3_predicted']=newgen['predicted_gen']*newgen['nh3_rate']

#bind all emissions sources together
emissions=pd.concat([existing_gen_units, newgen], ignore_index=True)
test_emissions_2020['planning_year']=2020
emissions = pd.concat([emissions, test_emissions_2020], ignore_index=True)

#make output folders

#folder for emissions output
if not os.path.exists('InMap/MIP_Emissions/'+scenario+'/'+model):
    os.makedirs('InMap/MIP_Emissions/'+scenario+'/'+model+'/')

#folder for inmap output
if not os.path.exists('InMap/MIP_InMap_Output/'+scenario+'/'+model):
    os.makedirs('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/')

for key, year in year_inputs.items():
    # Subset the dataframe for the specific planning year
    emissions_temp = emissions.query(f'planning_year == {year}')

    # Select and rename the necessary columns
    emissions_temp = emissions_temp[['Longitude', 'Latitude', 'nox_predicted', 'so2_predicted', 'pm25_predicted', 'voc_predicted', 'nh3_predicted']]
    emissions_temp.columns = ['Longitude', 'Latitude', 'NOx', 'SOx', 'PM2_5', 'VOC', 'NH3']

    # Convert to GeoDataFrame
    emissions_temp = gpd.GeoDataFrame(
        emissions_temp, 
        geometry=gpd.points_from_xy(emissions_temp.Longitude, emissions_temp.Latitude), 
        crs='EPSG:4326'
    )

    # Drop rows with missing values and reset index
    emissions_temp = emissions_temp.dropna().reset_index(drop=True)

    # Save to file
    emissions_temp.to_file(filename=f'InMap/MIP_Emissions/{scenario}/{model}/emissions_{year}.shp')

### Write total emissions to a csv

tot_emissions = emissions.groupby(['planning_year']).agg({'nox_predicted':'sum', 'so2_predicted':'sum', 'pm25_predicted':'sum', 'voc_predicted':'sum', 'nh3_predicted':'sum'}).reset_index()
tot_emissions['model']=model
tot_emissions['scenario']=scenario
tot_emissions['date_stamp']=pd.to_datetime('today').date()

print(tot_emissions)

tot_emissions.to_csv('MIP_AirPollution/emis.csv', mode='a', index=False, header=False)

#Now do by technology
tot_emissions = emissions.groupby(['planning_year', 'technology']).agg({'nox_predicted':'sum', 'so2_predicted':'sum', 'pm25_predicted':'sum', 'voc_predicted':'sum', 'nh3_predicted':'sum'}).reset_index()
tot_emissions['model']=model
tot_emissions['scenario']=scenario
tot_emissions['date_stamp']=pd.to_datetime('today').date()

print(tot_emissions)

tot_emissions.to_csv('MIP_AirPollution/emis_detail.csv', mode='a', index=False, header=False)

