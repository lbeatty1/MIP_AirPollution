# %% [markdown]
# # Code to impute emissions rates, then take model output and generate total emissions by year
# The first challenge will be to get emissions rates (lb/mwh).  To do this I'll be taking EIA data on net generation and EPA data on emissions to calculate rates.  There will be many missings that I will fill in by taking generation-weighted technology-planning_year means.
# 
# Once I have emissions rates, the goal will be to output a series of shapefiles of location-specific aggregate emissions by year. A challenge here is taking production from the scenario outputs and assigning it to specific plants.  There are two reasonable ways of doing this -- either with net generation or capacity.  I let the user select which variable they want to use.
# 
# ### Brief Code Overview
# 1. Data cleaning (formatting columns, names, etc)
# 2. Merge EIA and EPA data into existing_gen_units using the EPA-EIA crosswalk
# 3. Impute generation for generators with missing generation.  To do this, I take plant-level generation and distribute that generation to generators based on each generator's capacity.
# 4. Calculate generation-weighted average emissions rates, then use those to fill in generators with missing emissions rates (missings get filled in with a technology-planningyear weighted mean).
# 5. Calculate aggregate emissions by multiplying rates by model-output specified generation.  As mentioned earlier, I calculate generator level generation either by calculating a generator's share of total capacity or net generation for that cluster-planningyear.
# 6. Split the emissions output by planning year and write to shapefiles.
# 

# %% [markdown]
# ## 1. Data cleaning

# %%
globals().clear()

import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
import geopandas
import fiona

# %%
os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')


#PG existing gen units output
existing_gen_units_2030 = pd.read_csv('MIP_results_comparison/case_settings/26-zone/usensys_inputs_10_weeks/2030/existing_gen_units.csv')
existing_gen_units_2040 = pd.read_csv('MIP_results_comparison/case_settings/26-zone/usensys_inputs_10_weeks/2040/existing_gen_units.csv')
existing_gen_units_2050 = pd.read_csv('MIP_results_comparison/case_settings/26-zone/usensys_inputs_10_weeks/2050/existing_gen_units.csv')

#EIA-EPA Crosswalk
crosswalk = pd.read_csv("Data/epa_eia_crosswalk.csv")

# EIA 860 for Generator Info
eia860 = pd.read_excel("Data/eia860/3_1_Generator_Y2020.xlsx", skiprows=1)

# EIA923 for Generation Info
eia923_fuels = pd.read_excel("Data/eia923/EIA923_Schedules_2_3_4_5_M_12_2020_Final_Revision.xlsx", sheet_name='Page 1 Generation and Fuel Data', skiprows=5)
eia923_generators = pd.read_excel("Data/eia923/EIA923_Schedules_2_3_4_5_M_12_2020_Final_Revision.xlsx", sheet_name='Page 4 Generator Data', skiprows=5)

#Emissions
emissions = pd.read_csv("Data/CAMD/facilities_emissions.csv")
#only want year 2020
emissions = emissions.query('year==2020')

# PM25
pm25 = pd.read_excel("Data/eGRID2020 DRAFT PM Emissions.xlsx", sheet_name="2020 PM Unit-level Data", skiprows=1)

# %%
#####################
## Format columns ###
#####################

# existing_gen_units
existing_gen_units_2030['plant_id_eia']=existing_gen_units_2030['plant_id_eia'].astype(int)
existing_gen_units_2040['plant_id_eia']=existing_gen_units_2040['plant_id_eia'].astype(int)
existing_gen_units_2050['plant_id_eia']=existing_gen_units_2050['plant_id_eia'].astype(int)

existing_gen_units_2030['generator_id']=existing_gen_units_2030['generator_id'].astype(str)
existing_gen_units_2040['generator_id']=existing_gen_units_2040['generator_id'].astype(str)
existing_gen_units_2050['generator_id']=existing_gen_units_2050['generator_id'].astype(str)

existing_gen_units_2030['planning_year']=2030
existing_gen_units_2040['planning_year']=2040
existing_gen_units_2050['planning_year']=2050

#bind all into one
existing_gen_units = pd.concat([existing_gen_units_2030, existing_gen_units_2040, existing_gen_units_2050])
existing_gen_units = existing_gen_units.rename(columns={'generator_id': 'EIA_GENERATOR_ID', 'plant_id_eia':'EIA_PLANT_ID'})


## EPA-EIA crosswalk
crosswalk = crosswalk[['CAMD_PLANT_ID', 'CAMD_UNIT_ID', 'CAMD_GENERATOR_ID', 'EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'EIA_UNIT_TYPE']]
crosswalk['EIA_GENERATOR_ID'] = crosswalk['EIA_GENERATOR_ID'].astype(str)


## EIA Data
eia860 = eia860[['Plant Code', 'Generator ID', 'Nameplate Capacity (MW)', 'Planned Retirement Year', 'Planned Retirement Month', 'Synchronized to Transmission Grid', 'Technology']]
eia860.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'Capacity', 'RetirementYear', 'RetirementMonth', 'SynchronizedToGrid', 'Technology']
eia860['EIA_GENERATOR_ID']=eia860['EIA_GENERATOR_ID'].astype(str)

eia923_fuels = eia923_fuels[['Plant Id', 'Plant Name', 'Plant State', 'Net Generation\n(Megawatthours)']]
eia923_fuels.columns = ['EIA_PLANT_ID', 'EIA_PLANT_NAME', 'EIA_STATE', 'NET_GEN_PLANT']
eia923_fuels = eia923_fuels.groupby('EIA_PLANT_ID').agg({'NET_GEN_PLANT': 'sum'}).reset_index()

eia923_generators = eia923_generators[['Plant Id', 'Generator Id', 'Net Generation\nYear To Date']]
eia923_generators.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'NET_GEN_GENERATOR']
eia923_generators['EIA_GENERATOR_ID'] = eia923_generators['EIA_GENERATOR_ID'].astype(str)

pm25['UNITID'] = pm25['UNITID'].astype(str)
pm25 = pm25.groupby(['ORISPL', 'UNITID']).agg({'PM25AN': 'sum'}).reset_index()
pm25.columns = ['facilityId', 'unitId', 'pm25']
pm25['unitId']=pm25['unitId'].astype(str)
pm25['facilityId']=pm25['facilityId'].astype(int)

emissions['unitId']=emissions['unitId'].astype(str)
emissions['facilityId']=emissions['facilityId'].astype(int)

#Get emissions in pounds
emissions = pd.merge(emissions, pm25, on=['facilityId', 'unitId'], how='left')
emissions['nox_lbs'] = emissions['noxMass'] * 2000
emissions['so2_lbs'] = emissions['so2Mass'] * 2000
emissions['pm25_lbs'] = emissions['pm25'] * 2000

#rename columns
emissions = emissions.rename(columns = {'facilityId': 'CAMD_PLANT_ID', 'unitId': 'CAMD_UNIT_ID'})

# %% [markdown]
# ## 2. Merge EIA and EPA data into existing_gen_units using the EPA-EIA crosswalk

# %%
#join existing_gen_units with crosswalk
existing_gen_units = pd.merge(existing_gen_units, crosswalk, on=['EIA_GENERATOR_ID', 'EIA_PLANT_ID'],how='left')

#in existing_gen_units, there's a fair amount of missing capacities that are available from eia data so I'm going to join in 
#eia860 and then fill in nans
existing_gen_units = pd.merge(existing_gen_units, eia860[['EIA_GENERATOR_ID', 'EIA_PLANT_ID', 'Capacity']], on=['EIA_GENERATOR_ID', 'EIA_PLANT_ID'], how='left')

#need net gen
existing_gen_units = pd.merge(existing_gen_units, eia923_fuels, on=['EIA_PLANT_ID'], how='left')
existing_gen_units = pd.merge(existing_gen_units, eia923_generators, on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID'], how='left')

#lastly, need emissions
existing_gen_units = pd.merge(existing_gen_units, emissions, on=['CAMD_PLANT_ID', 'CAMD_UNIT_ID'])


# %%
#fill in missing capacities
existing_gen_units['capacity_mw']=existing_gen_units['capacity_mw'].combine_first(existing_gen_units['Capacity'])

# %% [markdown]
# ## 3. Impute generation for generators with missing generation.  To do this, I take plant-level generation and distribute that generation to generators based on each generator's capacity.
# 
# I'm going to calculate plant-level 'missing generation'
# Then divy up the missing generation to generators according to capacity in MW

# %%
summed_plant_gen = existing_gen_units.groupby(['EIA_PLANT_ID', 'planning_year']).agg({'NET_GEN_GENERATOR': 'sum'}).reset_index()
summed_plant_gen.columns=['EIA_PLANT_ID', 'planning_year', 'sum_generator_gen']

existing_gen_units = pd.merge(existing_gen_units, summed_plant_gen, on=['EIA_PLANT_ID', 'planning_year'], how='left')

existing_gen_units['missing_generator_generation']=existing_gen_units['NET_GEN_GENERATOR'].isna().astype(int)
existing_gen_units['missing_generation'] = existing_gen_units['NET_GEN_PLANT'] - existing_gen_units['sum_generator_gen']


# %%
missing_generators = existing_gen_units.query('missing_generator_generation==1').\
    groupby(['EIA_PLANT_ID', 'planning_year']).\
    agg({'capacity_mw': 'sum'}).\
    reset_index()
missing_generators.columns=['EIA_PLANT_ID', 'planning_year', 'missing_generator_capacity']

existing_gen_units = pd.merge(existing_gen_units, missing_generators, on=['EIA_PLANT_ID', 'planning_year'], how='left')

# %%
## Make imputation

existing_gen_units['pct_missing_capacity'] = (existing_gen_units['capacity_mw']/existing_gen_units['missing_generator_capacity'])*existing_gen_units['missing_generator_generation']
existing_gen_units['imputed_net_gen'] = existing_gen_units['pct_missing_capacity']*existing_gen_units['missing_generation']


#replace missings with imputed
existing_gen_units['NET_GEN_GENERATOR'] = existing_gen_units['NET_GEN_GENERATOR'].combine_first(existing_gen_units['imputed_net_gen'])

# %% [markdown]
# ## 4. Calculate generation-weighted average emissions rates, then use those to fill in generators with missing emissions rates.
# 

# %%
#get rates
existing_gen_units['nox_rate'] = existing_gen_units['nox_lbs']/existing_gen_units['NET_GEN_GENERATOR']
existing_gen_units['so2_rate'] = existing_gen_units['so2_lbs']/existing_gen_units['NET_GEN_GENERATOR']
existing_gen_units['pm25_rate'] = existing_gen_units['pm25_lbs']/existing_gen_units['NET_GEN_GENERATOR']

#for now I'm going to omit units with negative net_gen since it doesn't make sense for them to have negative 'rates'
#I'll replace the rates with sample weighted-means
existing_gen_units.loc[existing_gen_units['nox_rate']<0, 'nox_rate']=np.nan
existing_gen_units.loc[existing_gen_units['pm25_rate']<0, 'pm25_rate']=np.nan
existing_gen_units.loc[existing_gen_units['so2_rate']<0, 'so2_rate']=np.nan

existing_gen_units.loc[existing_gen_units['nox_rate'].isin([np.inf]), 'nox_rate']=np.nan
existing_gen_units.loc[existing_gen_units['pm25_rate'].isin([np.inf]), 'pm25_rate']=np.nan
existing_gen_units.loc[existing_gen_units['so2_rate'].isin([np.inf]), 'so2_rate']=np.nan

# %%
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


# %%
#Ok last thing to do is fill in missings

technology_rates = technology_rates[['technology', 'planning_year', 'nox_rate', 'pm25_rate', 'so2_rate']]
technology_rates.columns = ['technology', 'planning_year', 'noxrate_imputed', 'pm25rate_imputed', 'so2rate_imputed']

existing_gen_units = pd.merge(existing_gen_units, technology_rates, on=['technology', 'planning_year'], how='left')

# %%
existing_gen_units['noxrate_imputed'] = existing_gen_units['nox_rate'].combine_first(existing_gen_units['noxrate_imputed'])
existing_gen_units['so2rate_imputed'] = existing_gen_units['so2_rate'].combine_first(existing_gen_units['so2rate_imputed'])
existing_gen_units['pm25rate_imputed'] = existing_gen_units['pm25_rate'].combine_first(existing_gen_units['pm25rate_imputed'])

# %% [markdown]
# ## 5. Calculate aggregate emissions by multiplying rates by model-output specified generation.  As mentioned earlier, I calculate generator level generation either by calculating a generator's share of total capacity or net generation for that cluster-planningyear.
# 
# Start by specifying which model, scenario, and column you want outputs for.

# %%
model = 'SWITCH'
# model = 'TEMOA'
# model = 'GenX'
# model = 'UNENSYS


scenario = '26z-thin-debug'
# scenario = '26z-debug-noCO2Cap'

# column = 'NET_GEN_GENERATOR'
column = 'capacity_mw'


# %%
generation = pd.read_csv("MIP_results_comparison/"+scenario+"/"+model+" results summary/generation.csv")

technology_year_total = existing_gen_units.groupby(['Resource', 'planning_year']).agg({column : 'sum'}).reset_index()
technology_year_total.columns = ['Resource', 'planning_year', 'technology_total']

#merge in total capacity or total net gen
existing_gen_units = pd.merge(existing_gen_units, technology_year_total, on=['Resource', 'planning_year'], how='left')

#merge in model generation
generation = generation.rename(columns={'resource_name':'Resource'})
existing_gen_units = pd.merge(existing_gen_units, generation, on=['Resource', 'planning_year'], how='left')


# %%
existing_gen_units['pct_total']=existing_gen_units[column]/existing_gen_units['technology_total']
existing_gen_units['predicted_gen']=existing_gen_units['value']*existing_gen_units['pct_total']

existing_gen_units['nox_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['noxrate_imputed']
existing_gen_units['so2_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['so2rate_imputed']
existing_gen_units['pm25_predicted']=existing_gen_units['predicted_gen']*existing_gen_units['pm25rate_imputed']

# %%
#merge in plant locations
plants = pd.read_excel('Data/eia860/2___Plant_Y2017.xlsx', skiprows=1)
plants = plants[['Plant Code', 'Longitude', 'Latitude']]
plants.columns = ['EIA_PLANT_ID', 'Longitude', 'Latitude']

existing_gen_units = pd.merge(existing_gen_units, plants, on=['EIA_PLANT_ID'], how='left')

# %%
existing_gen_units = existing_gen_units[['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'Resource','planning_year', 'capacity_mw', 'Longitude', 'Latitude', 'predicted_gen', 'nox_predicted', 'so2_predicted', 'pm25_predicted', 'noxrate_imputed', 'so2rate_imputed', 'pm25rate_imputed']]
filename = 'InMap/MIP_Emissions/'+scenario+'/'+model+'/predicted_emissions.csv'
existing_gen_units.to_csv(filename)



# %% [markdown]
# ## 6. Split the emissions output by planning year and write to shapefiles.

# %%
#####
## 2030
#####

emissions_2030 = existing_gen_units.query('planning_year==2030')

emissions_2030 = emissions_2030[['Longitude', 'Latitude', 'nox_predicted', 'so2_predicted', 'pm25_predicted']]
emissions_2030.columns = ['Longitude', 'Latitude', 'NOx', 'SOx', 'PM2_5']

emissions_2030 = geopandas.GeoDataFrame(
    emissions_2030, geometry = geopandas.points_from_xy(emissions_2030.Longitude, emissions_2030.Latitude), crs='EPSG:4326')

emissions_2030.to_file(filename='InMap/MIP_Emissions/'+scenario+'/'+model+'/emissions_2030.shp')

#####
## 2040
#####

emissions_2040 = existing_gen_units.query('planning_year==2040')

emissions_2040 = emissions_2040[['Longitude', 'Latitude', 'nox_predicted', 'so2_predicted', 'pm25_predicted']]
emissions_2040.columns = ['Longitude', 'Latitude', 'NOx', 'SOx', 'PM2_5']

emissions_2040 = geopandas.GeoDataFrame(
    emissions_2040, geometry = geopandas.points_from_xy(emissions_2040.Longitude, emissions_2040.Latitude), crs='EPSG:4326')

emissions_2040.to_file(filename='InMap/MIP_Emissions/'+scenario+'/'+model+'/emissions_2040.shp')



# %% [markdown]
# ## List of open questions
# 
# 1. What do I do about generators with negative net gen?  This makes emissions rates negative but if I just call them zero I'd be biasing plant-level emissions upwards.
# 


