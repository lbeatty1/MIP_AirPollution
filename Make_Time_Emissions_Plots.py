import pandas as pd
import matplotlib.pyplot as plt
import os

####################
# Read in Data #####
####################

crosswalk = pd.read_csv("Data/epa_eia_crosswalk.csv")
emissions = pd.read_csv("Data/CAMD/facilities_emissions.csv")

# PM25
pm25 = pd.DataFrame()
for y in range(2018, 2021):
    sheetname = f"{y} PM Unit-level Data"
    pm25_temp = pd.read_excel("Data/eGRID2020 DRAFT PM Emissions.xlsx", sheet_name=sheetname, skiprows=1)
    pm25 = pd.concat([pm25, pm25_temp])

pm25['UNITID'] = pm25['UNITID'].astype(str)
pm25 = pm25.groupby(['YEAR', 'ORISPL', 'UNITID']).agg({'PM25AN': 'sum'}).reset_index()
pm25.columns = ['YEAR', 'ORISPL', 'UNITID', 'pm25']


# EIA 923 For Annual Generation
eia923 = pd.DataFrame()
files923 = [f for f in os.listdir("Data/eia923/") if os.path.isfile(os.path.join("Data/eia923/", f)) and "2_3_4" in f]
for j in files923:
    tempdat = pd.read_excel("Data/eia923/"+j, sheet_name='Page 4 Generator Data', skiprows=5)
    eia923 = pd.concat([eia923, tempdat])
    print(j)

eia923 = eia923[['Plant Id', 'Generator Id', 'Plant Name', 'Plant State', 'Net Generation\nYear To Date', 'YEAR']]
eia923.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'EIA_PLANT_NAME', 'EIA_STATE', 'NET_GEN', 'YEAR']

# EIA 860 for Generator Info
eia860 = pd.DataFrame()
files860 = [f for f in os.listdir("Data/eia860/") if os.path.isfile(os.path.join("Data/eia860/", f)) and "Generator" in f]
for j in files860:
    tempdat = pd.read_excel("Data/eia860/"+j, skiprows=1)
    tempdat['year'] = j[15:19]
    eia860 = pd.concat([eia860, tempdat])
    print(j)

eia860 = eia860[['Plant Code', 'Generator ID', 'Nameplate Capacity (MW)', 'Planned Retirement Year', 'Planned Retirement Month', 'Synchronized to Transmission Grid', 'year']]
eia860.columns = ['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'Capacity', 'RetirementYear', 'RetirementMonth', 'SynchronizedToGrid', 'YEAR']
eia860['YEAR'] = eia860['YEAR'].astype('int')
eia923['YEAR'] = eia923['YEAR'].astype('int')

# Join EIA together
eia_joined = pd.merge(eia923, eia860, on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'YEAR'], how='left')

# Merge crosswalk into eia
crosswalk = crosswalk[['CAMD_PLANT_ID', 'CAMD_UNIT_ID', 'CAMD_GENERATOR_ID', 'EIA_PLANT_ID', 'EIA_GENERATOR_ID', 'EIA_UNIT_TYPE']]
eia_joined = pd.merge(eia_joined, crosswalk, on=['EIA_PLANT_ID', 'EIA_GENERATOR_ID'], how='left')

eia_collapsed = eia_joined.groupby(['CAMD_PLANT_ID', 'CAMD_UNIT_ID', 'YEAR']).agg({'NET_GEN': 'sum', 'Capacity': 'sum'}).reset_index()

# Join CAMD with PM25
emissions = pd.merge(emissions, pm25, left_on=['facilityId', 'unitId', 'year'], right_on=['ORISPL', 'UNITID', 'YEAR'], how='left')

# Join with CAMD
camd_eia_data = pd.merge(emissions, eia_collapsed, left_on=['facilityId', 'unitId', 'year'], right_on=['CAMD_PLANT_ID', 'CAMD_UNIT_ID', 'YEAR'], how='left')

### Calculate tons
# Calculate values based on existing columns
camd_eia_data['nox_lbs'] = camd_eia_data['noxMass'] * 2000
camd_eia_data['NOX_RATE'] = camd_eia_data['nox_lbs'] / camd_eia_data['NET_GEN']
camd_eia_data['so2_lbs'] = camd_eia_data['so2Mass'] * 2000
camd_eia_data['so2_rate'] = camd_eia_data['so2_lbs'] / camd_eia_data['NET_GEN']
camd_eia_data['pm25_lbs'] = camd_eia_data['pm25'] * 2000
camd_eia_data['pm25_rate'] = camd_eia_data['pm25_lbs'] / camd_eia_data['NET_GEN']

# Examine Coal
camd_eia_data_coal = camd_eia_data[camd_eia_data['primaryFuelInfo'].str.contains("Coal") & (camd_eia_data['facilityId'] < 880000)]

# Plotting NOx Rate vs. Annual Net Generation for Coal
plt.scatter(camd_eia_data_coal['NET_GEN'], camd_eia_data_coal['NOX_RATE'], c=camd_eia_data_coal['year'])
plt.ylim(0, 19)
plt.xlabel('Annual Net Generation (MWh)')
plt.ylabel('NOx Rate (lbs/MWh)')
plt.colorbar(label='Year')
plt.title('NOx Rate vs. Annual Net Generation: Coal Plants')
plt.savefig("MIP_AirPollution/Figures/NoxRate_AnnualGen_coal.jpg", dpi=300)
plt.show()

# Plotting SO2 Rate vs. Annual Net Generation for Coal
plt.scatter(camd_eia_data_coal['NET_GEN'], camd_eia_data_coal['so2_rate'], c=camd_eia_data_coal['year'])
plt.ylim(0, 19)
plt.xlabel('Annual Net Generation (MWh)')
plt.ylabel('SO2 Rate (lbs/MWh)')
plt.colorbar(label='Year')
plt.title('SO2 Rate vs. Annual Net Generation: Coal Plants')
plt.savefig("MIP_AirPollution/Figures/SO2Rate_AnnualGen_coal.jpg", dpi=300)
plt.show()

# Plotting PM2.5 Rate vs. Annual Net Generation for Coal
plt.scatter(camd_eia_data_coal['NET_GEN'], camd_eia_data_coal['pm25_rate'], c=camd_eia_data_coal['year'])
plt.ylim(0, 19)
plt.xlabel('Annual Net Generation (MWh)')
plt.ylabel('PM2.5 Rate (lbs/MWh)')
plt.colorbar(label='Year')
plt.title('PM2.5 Rate vs. Annual Net Generation: Coal Plants')
plt.savefig("MIP_AirPollution/Figures/PM25Rate_AnnualGen_coal.jpg", dpi=300)
plt.show()

# Plotting NOx Rate vs. Annual Net Generation for Coal
plt.scatter(camd_eia_data_coal['Capacity'], camd_eia_data_coal['NOX_RATE'], c=camd_eia_data_coal['year'])
plt.ylim(0, 19)
plt.xlabel('Capacity(MW)')
plt.ylabel('NOx Rate (lbs/MWh)')
plt.colorbar(label='Year')
plt.title('NOx Rate vs. Capacity: Coal Plants')
plt.savefig("MIP_AirPollution/Figures/NoxRate_Capacity_coal.jpg", dpi=300)
plt.show()

# Plotting SO2 Rate vs. Annual Net Generation for Coal
plt.scatter(camd_eia_data_coal['Capacity'], camd_eia_data_coal['so2_rate'], c=camd_eia_data_coal['year'])
plt.ylim(0, 19)
plt.xlabel('Capacity (MW)')
plt.ylabel('SO2 Rate (lbs/MWh)')
plt.colorbar(label='Year')
plt.title('SO2 Rate vs. Capacity: Coal Plants')
plt.savefig("MIP_AirPollution/Figures/SO2Rate_Capacity_coal.jpg", dpi=300)
plt.show()

# Plotting PM2.5 Rate vs. Annual Net Generation for Coal
plt.scatter(camd_eia_data_coal['Capacity'], camd_eia_data_coal['pm25_rate'], c=camd_eia_data_coal['year'])
plt.ylim(0, 19)
plt.xlabel('Capacity (MW)')
plt.ylabel('PM2.5 Rate (lbs/MWh)')
plt.colorbar(label='Year')
plt.title('PM2.5 Rate vs. Capacity: Coal Plants')
plt.savefig("MIP_AirPollution/Figures/PM25Rate_Capacity_coal.jpg", dpi=300)
plt.show()

#Produce timeseries
yearly_coal_emissions = camd_eia_data_coal.groupby('year').apply(lambda x: pd.Series({
    'NoxRate_weighted': (x['NOX_RATE'] * x['NET_GEN']).sum(),
    'So2Rate_weighted': (x['so2_rate'] * x['NET_GEN']).sum(),
    'NET_GEN': x['NET_GEN'].sum()
})).reset_index()

yearly_coal_emissions['NoxRate_weighted'] /= yearly_coal_emissions['NET_GEN']
yearly_coal_emissions['So2Rate_weighted'] /= yearly_coal_emissions['NET_GEN']

#Plot Nox Emissions Rate over time
plt.figure(figsize=(8, 5))
plt.plot(yearly_coal_emissions['year'], yearly_coal_emissions['NoxRate_weighted'])
plt.xlabel('Year')
plt.ylabel('Generation-weighted average Nox Rate (lbs/MWh)')
plt.title('NOx Emissions Rate: Coal Plants')
plt.grid(True)
plt.savefig("MIP_AirPollution/Figures/NoxRate_timeseries_coal.jpg", dpi=300)
plt.show()

# Plotting SO2 Emissions Rate over time for Coal Plants
plt.figure(figsize=(8, 5))
plt.plot(yearly_coal_emissions['year'], yearly_coal_emissions['So2Rate_weighted'])
plt.xlabel('Year')
plt.ylabel('Generation-weighted average SO2 Rate (lbs/MWh)')
plt.title('SO2 Emissions Rate: Coal Plants')
plt.grid(True)
plt.savefig("MIP_AirPollution/Figures/So2Rate_timeseries_coal.jpg", dpi=300)
plt.show()

