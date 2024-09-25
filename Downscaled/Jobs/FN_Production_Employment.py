# -*- coding: utf-8 -*-
"""
Created on Wed Sep 25 16:12:01 2024

@author: lfernandezintriago
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from datetime import datetime



def calculate_employment_production(model, scenario):


    job_coefs = pd.read_csv('MIP_AirPollution/Downscaled/Jobs/Job_Coefficients.csv')
    generation = pd.read_csv("MIP_results_comparison/"+scenario+"/"+model+"_results_summary/generation.csv")
    generator_inputs = pd.read_csv("MIP_results_comparison/"+scenario+'/'+model+'_op_inputs/Inputs/Inputs_p1/Generators_data.csv')
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
    gasprod_state['State']= gasprod_state['Variable'].str.replace(r' Dry Natural Gas Production \(Million Cubic Feet\)', '')
    
    gasprod_state['Pct_total'] = gasprod_state['mcf_annual']/sum(gasprod_state['mcf_annual'])
    
    oilprod_state = oilprod_state[~oilprod_state['Variable'].str.contains('Alaska South|Alaska North|U.S.|PADD')]
    #convert to bbl
    oilprod_state['bbl_annual']=oilprod_state['Value']*1000
    
    #don't have 2023 onwards yet so lets take average from 18-22?  Why not?
    oilprod_state = oilprod_state[(oilprod_state['Year']<2023) & (oilprod_state['Year']>2017) & oilprod_state['Year'].notnull()]
    oilprod_state = oilprod_state.groupby(['Variable']).agg({'bbl_annual':'sum'}).reset_index()
    oilprod_state['State'] = oilprod_state['Variable'].str.replace(r' Field Production of Crude Oil \(Thousand Barrels\)', '')
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
    coal = coal[~coal['State'].str.contains(r'\(Anthracite\)|\(East\)|\(West\)|\(Bituminous\)|\(Northern\)|\(Southern\)|River|Basin|Region Total|U.S.|Other|Appalachia')]
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
    
    
    ###################################################
    ## Get Coal/NG consumption from model outputs #####
    ##################################################
    generation = generation.rename(columns={'resource_name':'Resource'})
    generation = pd.merge(generation, generator_inputs, how='left', on='Resource').reset_index()
    
    generation['fuel_consumption_mmbtu'] = generation['value']*generation['Heat_Rate_MMBTU_per_MWh']
    generation = generation.groupby(['planning_year', 'tech_type']).agg({'fuel_consumption_mmbtu':'sum'}).reset_index()
    generation['fuel_consumption_mcf'] = generation['fuel_consumption_mmbtu']/1.038
    generation['fuel_consumption_mmcf'] = generation['fuel_consumption_mcf']/1000
    ######################################################
    ## Distribute consumption to extraction from states ##
    ######################################################
    
    #natgas
    natgas_consumption = generation[(generation['tech_type']=='Natural Gas')|(generation['tech_type']=="CCS")]
    natgas_consumption = natgas_consumption.groupby('planning_year').agg({'fuel_consumption_mmcf':'sum'}).reset_index()
    
    prod = pd.merge(natgas_consumption.assign(key=1), gasprod_state.assign(key=1), on='key').drop('key', axis=1).reset_index()
    prod['State_level_production_mmcf'] = prod['fuel_consumption_mmcf']*prod['Pct_total']
    
    ######################################################
    ## Predict jobs from state-level production
    #####################################################
    def map_state_to_region(state):
        appalachian_states = ['Ohio', 'New York', 'Maryland', 'Pennsylvania', 'West Virginia']
        bakken_states = ['Montana', 'North Dakota']
        niobrara_states = ['Colorado', 'Kansas', 'Nebraska', 'Wyoming']
        
        if state in appalachian_states:
            return 'Appalachian'
        elif state in bakken_states:
            return 'Bakken'
        elif state in niobrara_states:
            return 'Niobrara'
        elif state=='Texas':
            return 'Texas'
        elif state=='New Mexico':
            return 'New Mexico'
        else:
            return 'Other'
    
    # Apply the function to create the 'region' column
    prod['region'] = prod['State'].apply(map_state_to_region)
    prod = pd.merge(prod, job_coefs[job_coefs['Resource']=='Natural gas'].rename(columns={'Subresource':'region'}), how='left', on='region')
    
    prod['jobs'] = prod['State_level_production_mmcf']*prod['Parameter Value']
    prod['employment'] = 'Natural Gas Production'
    employment_production = prod[['planning_year', 'State', 'jobs', 'employment']]
    
    #################################################
    ### COAL ########################################
    #################################################
    #ignores imports -- probably ok
    #20.1mmBTu per short ton
    
    coal_consumption = generation[(generation['tech_type']=='Coal')]
    coal_consumption = coal_consumption.groupby('planning_year').agg({'fuel_consumption_mmbtu':'sum'}).reset_index()
    
    prod = pd.merge(coal_consumption.assign(key=1), coal.assign(key=1), on='key').drop('key', axis=1).reset_index()
    prod['fuel_consumption_thousandtons'] = prod['fuel_consumption_mmbtu']/(20.1*1000)
    prod['State_level_surface_production_thousandtons'] = prod['fuel_consumption_thousandtons']*prod['Surface_pct']*pct_surface
    prod['State_level_underground_production_thousandtons'] = prod['fuel_consumption_thousandtons']*prod['Underground_pct']*pct_surface
    
    #coefs are 0.15/thousand short tons underground and 0.0191/thousand short tons surface
    prod['jobs'] = prod['State_level_surface_production_thousandtons']*0.0191+prod['State_level_underground_production_thousandtons']*0.151
    prod['employment'] = 'Coal Production'
    employment_production = pd.concat([employment_production, prod[['planning_year', 'State', 'jobs', 'employment']]])
    employment_production['state'] = employment_production['state'].str.replace(' Dry Natural Gas Production \(Million Cubic Feet\)', '', regex=True)

    return employment_production
