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

#################################################
### Get coal/oil/ng production by state #########
#################################################


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

gasprod_state = gasprod_state[~gasprod_state['Variable'].str.contains('Offshore|Onshore|U.S.')]
gasprod_state['mcf_annual']=gasprod_state['Value']*1000

#don't have 2023 onwards yet so lets take average from 18-22?  Why not?
gasprod_state = gasprod_state[(gasprod_state['Year']<2023) & (gasprod_state['Year']>2017) & gasprod_state['Year'].notnull()]
gasprod_state = gasprod_state.groupby(['Variable']).agg({'mcf_annual':'sum'}).reset_index()
gasprod_state['State']= gasprod_state['Variable'].str.replace(' Dry Natural Gas Production \(Million Cubic Feet\)', '')

gasprod_state['Pct_total'] = gasprod_state['mcf_annual']/sum(gasprod_state['mcf_annual'])

oilprod_state = oilprod_state[~oilprod_state['Variable'].str.contains('Alaska South|Alaska North|U.S.|PADD')]
#convert to bbl
oilprod_state['bbl_annual']=oilprod_state['Value']*1000

#don't have 2023 onwards yet so lets take average from 18-22?  Why not?
oilprod_state = oilprod_state[(oilprod_state['Year']<2023) & (oilprod_state['Year']>2017) & oilprod_state['Year'].notnull()]
oilprod_state = oilprod_state.groupby(['Variable']).agg({'bbl_annual':'sum'}).reset_index()
oilprod_state['State'] = oilprod_state['Variable'].str.replace(' Field Production of Crude Oil \(Thousand Barrels\)', '')
oilprod_state['Pct_total'] = oilprod_state['bbl_annual']/sum(oilprod_state['bbl_annual'])
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
coal = coal[~coal['State'].str.contains('\(Anthracite\)|\(East\)|\(West\)|\(Bituminous\)|\(Northern\)|\(Southern\)|River|Basin|Region Total|U.S.|Other|Appalachia')]
coal['State'] = coal['State'].str.replace('Total', '')

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

pct_surface = sum(coal['Surface_thousandtons'])/(sum(coal['Surface_thousandtons'])+sum(coal['Underground_thousandtons']))

##############################
## divy up population by 26z region
##############################

counties = pd.read_excel('Data/Jobs_Data/co-est2022-pop.xlsx', skiprows=3)
counties.columns = ['Location', '2020Base','2020', '2021', 'Pop']
counties = counties[counties['Location'].str.startswith('.')]
counties[['NAMELSAD', 'State']] = counties['Location'].str.split(', ', expand=True)
counties['NAMELSAD'] = counties['NAMELSAD'].str[1:]
counties = counties[['NAMELSAD', 'State', 'Pop']]

statepop = counties.groupby('State').agg({'Pop':'sum'}).rename(columns={'Pop':'StatePop'})
counties = pd.merge(counties, statepop, on='State', how='left')
counties['pct_statepop'] = counties['Pop']/counties['StatePop']

ipm_regions = gpd.read_file('Data/IPM_Regions/national_emm_boundaries.shp')
counties_shape = gpd.read_file('Data/Jobs_Data/tl_2022_us_county.shp')

ipm_regions = ipm_regions.to_crs(counties_shape.crs)

intersection = gpd.overlay(ipm_regions, counties_shape, how='intersection')

# Calculate the area of overlap for each intersecting polygon
intersection['overlap_area'] = intersection.geometry.area
#looks to me like ipm regions are supposed to be counties and slightly different resolutions causes more intersections than there should be
intersection = intersection[intersection['overlap_area'] == intersection.groupby(['STATEFP', 'NAME'])['overlap_area'].transform('max')]

state_fips_to_name = {
    1: 'Alabama', 2: 'Alaska', 4: 'Arizona', 5: 'Arkansas', 6: 'California',
    8: 'Colorado', 9: 'Connecticut', 10: 'Delaware', 11: 'District of Columbia',
    12: 'Florida', 13: 'Georgia', 15: 'Hawaii', 16: 'Idaho', 17: 'Illinois',
    18: 'Indiana', 19: 'Iowa', 20: 'Kansas', 21: 'Kentucky', 22: 'Louisiana',
    23: 'Maine', 24: 'Maryland', 25: 'Massachusetts', 26: 'Michigan',
    27: 'Minnesota', 28: 'Mississippi', 29: 'Missouri', 30: 'Montana',
    31: 'Nebraska', 32: 'Nevada', 33: 'New Hampshire', 34: 'New Jersey',
    35: 'New Mexico', 36: 'New York', 37: 'North Carolina', 38: 'North Dakota',
    39: 'Ohio', 40: 'Oklahoma', 41: 'Oregon', 42: 'Pennsylvania',
    44: 'Rhode Island', 45: 'South Carolina', 46: 'South Dakota',
    47: 'Tennessee', 48: 'Texas', 49: 'Utah', 50: 'Vermont', 51: 'Virginia',
    53: 'Washington', 54: 'West Virginia', 55: 'Wisconsin', 56: 'Wyoming'
}

# Map state FIPS codes to state names and create a new column
intersection['STATEFP']=intersection['STATEFP'].astype(int)
intersection['State'] = intersection['STATEFP'].map(state_fips_to_name)

intersection = pd.merge(intersection, counties, how='left', on=['NAMELSAD', 'State'])

pop_ipm = intersection.drop(columns='geometry').groupby('model_regi').agg({'Pop':'sum'}).reset_index().rename(columns={'Pop':'model_regi_pop'})
intersection = pd.merge(intersection, pop_ipm, how='left', on='model_regi')
intersection['pct_model_regi_pop'] = intersection['Pop']/intersection['model_regi_pop']

county_modelregi = intersection[['model_regi', 'NAME', 'State', 'Pop', 'StatePop', 'model_regi_pop', 'pct_statepop', 'pct_model_regi_pop']]