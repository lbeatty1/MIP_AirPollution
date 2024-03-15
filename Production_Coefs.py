globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from datetime import datetime

os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')

### define model/scenario
model = 'GenX'
scenario = '26z-short-base-50'

job_coefs = pd.read_csv('MIP_AirPollution/Job_Coefficients.csv')


#################
## Read and format mip outputs
generation = pd.read_csv("MIP_results_comparison/"+scenario+"/"+model+"_results_summary/generation.csv")

capacity = pd.read_csv("MIP_results_comparison/"+scenario+"/"+model+"_results_summary/resource_capacity.csv")
capacity.columns = capacity.columns.map(lambda x: x.lower())
capacity = capacity[capacity['unit']=='MW']

capacity = capacity.groupby(['zone', 'resource_name', 'tech_type', 'planning_year']).agg({'start_value': 'sum', 'end_value': 'sum'}).reset_index()

##############
## Read in oil and gas production by basin

oil_gas_prod = pd.DataFrame()
excel_file = pd.ExcelFile('Data/Jobs_Data/dpr-data.xlsx')
for i in range(0,6):
    basinname = excel_file.sheet_names[i]
    tempdat = pd.read_excel(excel_file, sheet_name=basinname, skiprows=1)
    tempdat.columns = ['Month', 'Rigcount', 'ProductionPerRig_bbld', 'ProductionChange_bbld', 'TotalProduction_bbld', 'ProductionPerRig_mcfd', 'ProductionChange_mcfd', 'TotalProduction_mcfd']
    tempdat['Basin'] = basinname
    oil_gas_prod = pd.concat([oil_gas_prod, tempdat])
oil_gas_prod['Year'] = oil_gas_prod['Month'].apply(lambda x: pd.to_datetime(x).year)

#Read in oil and gas production by state    
#gas prod in million cubic feet per year
gasprod_state = pd.DataFrame()
excel_file = pd.ExcelFile('Data/Jobs_Data/NG_PROD_SUM_A_EPG0_FPD_MMCF_A.xls')
for i in range(1,2):
    sheetname = excel_file.sheet_names[i]
    tempdat = pd.read_excel(excel_file, sheet_name=sheetname, skiprows=2)
    tempdat = pd.melt(tempdat, id_vars=['Date'], var_name='Variable', value_name='Value')
    gasprod_state = pd.concat([gasprod_state, tempdat])
gasprod_state['Year'] = gasprod_state['Date'].apply(lambda x: pd.to_datetime(x).year)

#oil prod in thousand bbbl per month
excel_file=pd.ExcelFile('Data/Jobs_Data/PET_CRD_CRPDN_ADC_MBBL_M.xls')
oilprod_state = pd.read_excel(excel_file, sheet_name=1, skiprows=2)
oilprod_state = pd.melt(oilprod_state, id_vars=['Date'], var_name='Variable', value_name='Value')
oilprod_state['Year'] = oilprod_state['Date'].apply(lambda x: pd.to_datetime(x).year)

#construct NatGas as Niobrar, Appalachian, Bakken, New Mexico, Texas, Other
gasprod_state = gasprod_state[~gasprod_state['Variable'].str.contains('Offshore|Onshore|U.S.')]
#convert to mcf
gasprod_state['mcf_annual']=gasprod_state['Value']*1000

gas_prod_basins = oil_gas_prod
gas_prod_basins['mcf_annual']=gas_prod_basins['TotalProduction_mcfd']*30.4
gas_prod_basins = gas_prod_basins.groupby(['Year', 'Basin']).agg({'mcf_annual':'sum'}).reset_index()

#keep basis in Mayfield
gas_prod_basins = gas_prod_basins[gas_prod_basins['Basin'].isin(['Niobrara Region', 'Appalachia Region', 'Bakken Region'])]
#drop states that contain comprise Niobrara Appalachia and Bakken
gasprod_state = gasprod_state[~gasprod_state['Variable'].str.contains('Nebraska|Colorado|Kansas|Wyoming|New York|Ohio|Maryland|Pennsylvania|West Virginia|North Dakota|Montana')]
gasprod_state['Variable'] = gasprod_state['Variable'].apply(lambda x: 'Other' if 'Texas' not in x and 'New Mexico' not in x else x)
gasprod_state['Basin']=gasprod_state['Variable']
gasprod_state = gasprod_state.groupby(['Basin', 'Year']).agg({'mcf_annual':'sum'}).reset_index()
gasprod = pd.concat([gas_prod_basins, gasprod_state])

#don't have 2023 onwards yet so lets take average from 18-22?  Why not?
gasprod = gasprod[(gasprod['Year']<2023) & (gasprod['Year']>2017) & gasprod['Year'].notnull()]
gasprod = gasprod.groupby(['Basin']).agg({'mcf_annual':'sum'}).reset_index()


#god these mayfield paper is so shoddy
#Andarko basin is in fucking texas what the hell

oilprod_state = oilprod_state[~oilprod_state['Variable'].str.contains('Alaska South|Alaska North|U.S.|PADD')]
#convert to bbl
oilprod_state['bbl_annual']=oilprod_state['Value']*1000

oil_prod_basins = oil_gas_prod
oil_prod_basins['bbl_annual']=oil_prod_basins['TotalProduction_bbld']*30.4
oil_prod_basins = oil_prod_basins.groupby(['Year', 'Basin']).agg({'bbl_annual':'sum'}).reset_index()

#keep basins in analysis
oil_prod_basins = oil_prod_basins[oil_prod_basins['Basin'].isin(['Niobrara Region', 'Appalachia Region', 'Bakken Region', 'Andarko Region'])]
#drop states that contain comprise Niobrara Appalachia and Bakken and Andarko
oilprod_state = oilprod_state[~oilprod_state['Variable'].str.contains('Nebraska|Colorado|Kansas|Wyoming|New York|Ohio|Maryland|Pennsylvania|West Virginia|North Dakota|Montana|Oklahoma')]
oilprod_state['Variable'] = oilprod_state['Variable'].apply(lambda x: 'Other' if 'Texas' not in x and 'New Mexico' not in x else x)
oilprod_state['Basin']=oilprod_state['Variable']
oilprod_state = oilprod_state.groupby(['Basin', 'Year']).agg({'bbl_annual':'sum'}).reset_index()
oilprod = pd.concat([oil_prod_basins, oilprod_state])

#don't have 2023 onwards yet so lets take average from 18-22?  Why not?
oilprod = oilprod[(oilprod['Year']<2023) & (oilprod['Year']>2017) & oilprod['Year'].notnull()]
oilprod = oilprod.groupby(['Basin']).agg({'bbl_annual':'sum'}).reset_index()


########################
## Ok now do Coal ######
########################


underground = pd.read_excel('Data/Jobs_Data/table3.xls', skiprows=2)
surface = pd.read_excel('Data/Jobs_Data/table3_1.xls', skiprows=2)
#only care about totals
coal = pd.merge(surface, underground, how='outer', on='Coal-Producing State and Region1').reset_index()
#drop all of the sub-columns

coal = coal[['Coal-Producing State and Region1', 'Total_x', 'Total_y']]
coal.columns = ['State', 'Surface_thousandtons', 'Underground_thousandtons']

coal = coal.dropna(subset=['State'])
coal = coal[~coal['State'].str.contains('\(Anthracite\)|\(East\)|\(West\)|\(Bituminous\)|\(Northern\)|\(Southern\)|River|Basin')]

#thankyou chatgpt
states = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
    'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
    'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
    'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
    'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
    'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
    'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
    'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
    'West Virginia', 'Wisconsin', 'Wyoming'
]

coal = coal[coal['State'].str.contains('|'.join(states))]
coal.fillna(0, inplace=True)

coal['Underground_pct']=coal['Underground_thousandtons']/sum(coal['Underground_thousandtons'])
coal['Surface_pct'] = coal['Surface_thousandtons']/sum(coal['Surface_thousandtons'])

