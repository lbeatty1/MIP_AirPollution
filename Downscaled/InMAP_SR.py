from __future__ import (absolute_import, division, print_function, unicode_literals)
from builtins import * 
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile
import urllib.request
import csv
from shapely.geometry import Point
import geopandas as gpd

import time
import numpy as np
import zarr
from shapely.geometry import Polygon, Point
import pandas as pd
import geopandas as gpd
import s3fs
import os
import sys


os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')
sys.path.append(os.path.abspath('C:/Users/laure/Documents/Switch-USA-PG/'))

#pull in settings from settings file
from MIP_AirPollution.Downscaled.settings import *
models=['USENSYS']

popgrowth = pd.read_excel('Data/np2023-t4.xlsx', sheet_name='Sheet1')

def rect(i, w, s, e, n):
    x = [w[i], e[i], e[i], w[i], w[i]]
    y = [s[i], s[i], n[i], n[i], s[i]]
    return x, y

def poly(sr):
    ret = []
    w = sr["W"][:]
    s = sr["S"][:]
    e = sr["E"][:]
    n = sr["N"][:]
    for i in range(52411):
        x, y = rect(i, w, s, e, n)
        ret.append(Polygon([[x[0],y[0]],[x[1],y[1]],[x[2],y[2]],
                            [x[3],y[3]],[x[4],y[4]]]))
    return ret

def run_sr(emis, model, year, emis_units="tons/year"):
    start = time.time()
    url = 's3://inmap-model/isrm_v1.2.1.zarr/'
    fs = s3fs.S3FileSystem(anon=True, client_kwargs=dict(region_name='us-east-2'))
    sr = zarr.open(s3fs.S3Map(url, s3=fs, check=False), mode="r")
#     the following line is used when we access the SR matrix from local files
#     sr = zarr.open("isrm_v1.2.1.zarr", mode="r")

    # build the geometry
    p = poly(sr)
    print("Making polygons as geometry.")

    # took the emis geopandas dataframe
    df = pd.DataFrame({'Location': range(52411)})
    gdf = gpd.GeoDataFrame(df, geometry=p)

    # join the emis dataframe into the grid dataframe
    emis.crs = "+proj=longlat"
    gdf.crs = "+proj=lcc +lat_1=33.000000 +lat_2=45.000000 +lat_0=40.000000 +lon_0=-97.000000 +x_0=0 +y_0=0 +a=6370997.000000 +b=6370997.000000 +to_meter=1"
    emis = emis.to_crs(gdf.crs)
    join_right_df = gdf.sjoin(emis, how="right")
    print("Finished joining the dataframes.")
    
    index = join_right_df.Location.tolist()

    ppl = np.unique(join_right_df.Location.tolist())

    num = range(0,len(ppl))

    dictionary = dict(zip(ppl, num))
        
    SOA = sr['SOA'].get_orthogonal_selection(([0], ppl, slice(None)))
    print("SOA data is allocated.")
    pNO3 = sr['pNO3'].get_orthogonal_selection(([0], ppl, slice(None)))
    print("pNO3 data is allocated.")
    pNH4 = sr['pNH4'].get_orthogonal_selection(([0], ppl, slice(None)))
    print("pNH4 data is allocated.")
    pSO4 = sr['pSO4'].get_orthogonal_selection(([0], ppl, slice(None)))
    print("pSO4 data is allocated.")
    PM25 = sr['PrimaryPM25'].get_orthogonal_selection(([0], ppl, slice(None)))
    print("PrimaryPM25 data is allocated.")
    
    SOA_data, pNO3_data, pNH4_data, pSO4_data, PM25_data = 0.0, 0.0, 0.0, 0.0, 0.0
    for i in range(len(index)):
        SOA_data += SOA[0, dictionary[index[i]], :]*emis.VOC[i]
        pNO3_data += pNO3[0, dictionary[index[i]], :]*emis.NOx[i]
        pNH4_data += pNH4[0, dictionary[index[i]], :]*emis.NH3[i]
        pSO4_data += pSO4[0, dictionary[index[i]], :]*emis.SOx[i]
        PM25_data += PM25[0, dictionary[index[i]], :]*emis.PM2_5[i]
    data = SOA_data + pNO3_data + pNH4_data + pSO4_data + PM25_data

    print("Accessing the data.")
    if emis_units=="tons/year":
        fact = 28766.639

    TotalPM25 = fact * data
    TotalPop = sr['TotalPop'][0:52411]
    MortalityRate = sr['MortalityRate'][0:52411]
    Asian = sr['Asian'][0:52411]
    Black = sr['Black'][0:52411]
    Native = sr['Native'][0:52411]
    Latino = sr['Latino'][0:52411]
    WhiteNoLat = sr['WhiteNoLat'][0:52411]

    pop_growth_value = popgrowth.loc[popgrowth['Race'] == 'Total', year].values[0]
    pop_growth_base = popgrowth.loc[popgrowth['Race'] == 'Total', 2010].values[0]
    deathsK = (np.exp(np.log(1.06)/10 * TotalPM25) - 1) * TotalPop * pop_growth_value/pop_growth_base * MortalityRate / 100000
    deathsL = (np.exp(np.log(1.14)/10 * TotalPM25) - 1) * TotalPop * pop_growth_value/pop_growth_base * MortalityRate / 100000
    TotalPop = TotalPop * pop_growth_value/pop_growth_base 

    pop_growth_value = popgrowth.loc[popgrowth['Race'] == 'Asian', year].values[0]
    pop_growth_base = popgrowth.loc[popgrowth['Race'] == 'Asian', 2010].values[0]
    AsiandeathsK = (np.exp(np.log(1.06)/10 * TotalPM25) - 1) * Asian * pop_growth_value/pop_growth_base * MortalityRate / 100000
    AsiandeathsL = (np.exp(np.log(1.14)/10 * TotalPM25) - 1) * Asian * pop_growth_value/pop_growth_base * MortalityRate / 100000
    Asian = Asian * pop_growth_value/pop_growth_base 

    pop_growth_value = popgrowth.loc[popgrowth['Race'] == 'Black', year].values[0]
    pop_growth_base = popgrowth.loc[popgrowth['Race'] == 'Black', 2010].values[0]
    BlackdeathsK = (np.exp(np.log(1.06)/10 * TotalPM25) - 1) * Black * pop_growth_value/pop_growth_base * MortalityRate / 100000
    BlackdeathsL = (np.exp(np.log(1.14)/10 * TotalPM25) - 1) * Black * pop_growth_value/pop_growth_base * MortalityRate / 100000
    Black = Black * pop_growth_value/pop_growth_base 

    pop_growth_value = popgrowth.loc[popgrowth['Race'] == 'AmericanIndian', year].values[0]
    pop_growth_base = popgrowth.loc[popgrowth['Race'] == 'AmericanIndian', 2010].values[0]
    NativedeathsK = (np.exp(np.log(1.06)/10 * TotalPM25) - 1) * Native * pop_growth_value/pop_growth_base * MortalityRate / 100000
    NativedeathsL = (np.exp(np.log(1.14)/10 * TotalPM25) - 1) * Native * pop_growth_value/pop_growth_base * MortalityRate / 100000
    Native = Native * pop_growth_value/pop_growth_base 

    pop_growth_value = popgrowth.loc[popgrowth['Race'] == 'Hispanic', year].values[0]
    pop_growth_base = popgrowth.loc[popgrowth['Race'] == 'Hispanic', 2010].values[0]
    LatinodeathsK = (np.exp(np.log(1.06)/10 * TotalPM25) - 1) * Latino * pop_growth_value/pop_growth_base * MortalityRate / 100000
    LatinodeathsL = (np.exp(np.log(1.14)/10 * TotalPM25) - 1) * Latino * pop_growth_value/pop_growth_base * MortalityRate / 100000
    Latino = Latino * pop_growth_value/pop_growth_base 
    
    pop_growth_value = popgrowth.loc[popgrowth['Race'] == 'NonHispanicWhite', year].values[0]
    pop_growth_base = popgrowth.loc[popgrowth['Race'] == 'NonHispanicWhite', 2010].values[0]
    WhiteNoLatdeathsK = (np.exp(np.log(1.06)/10 * TotalPM25) - 1) * WhiteNoLat * pop_growth_value/pop_growth_base * MortalityRate / 100000
    WhiteNoLatdeathsL = (np.exp(np.log(1.14)/10 * TotalPM25) - 1) * WhiteNoLat * pop_growth_value/pop_growth_base * MortalityRate / 100000
    WhiteNoLat = WhiteNoLat * pop_growth_value/pop_growth_base 

    #pop_growth_value/pop_growth_base is the ratio of year y population to 2010 population (in the model)
    ret = gpd.GeoDataFrame(pd.DataFrame({'SOA': fact * SOA_data,
                                         'pNO3': fact * pNO3_data,
                                         'pNH4': fact * pNH4_data,
                                         'pSO4': fact * pSO4_data,
                                         'PrimaryPM25': fact * PM25_data,
                                         'TotalPM25': TotalPM25,
                                         'deathsK': deathsK,
                                         'deathsL': deathsL,
                                         'Black' : Black,
                                         'Asian' : Asian,
                                         'WhiteNoLat' : WhiteNoLat,
                                         'Native' : Native,
                                         'Latino' : Latino,
                                         'AsiandeathsK' : AsiandeathsK,
                                         'AsiandeathsL' : AsiandeathsL,
                                         'BlackdeathsK' : BlackdeathsK,
                                         'BlackdeathsL' : BlackdeathsL,
                                         'LatinodeathsK' : LatinodeathsK,
                                         'LatinodeathsL' : LatinodeathsL,
                                         'NativedeathsK' : NativedeathsK,
                                         'NativedeathsL' : NativedeathsL,
                                         'WhiteNoLatdeathsK' : WhiteNoLatdeathsK,
                                         'WhiteNoLatdeathsL' : WhiteNoLatdeathsL}), geometry=p[0:52411])

    print("Finished (%.0f seconds)               "%(time.time()-start))
    return ret

for model in models:
    for scenario in scenario_dictionary:
        for file, year in year_inputs.items():
            if not os.path.exists('InMap/MIP_Emissions/'+scenario+'/'+model+'/emissions_'+f"{year}"+'.shp'):
                print(f"'{scenario}' emissions output doesn't exist... skipping...")
                continue

            emis = gpd.read_file('InMap/MIP_Emissions/'+scenario+'/'+model+'/emissions_'+f"{year}"+'.shp')
            print(emis.sum())
            if emis['Longitude'].sum()==0:
                print('something wrong with emissions for this scenario.. skipping...')
                continue
            resultsISRM = run_sr(emis, model="isrm", year=year)
            resultsISRM = resultsISRM.set_crs('PROJCS["Lambert_Conformal_Conic",GEOGCS["GCS_unnamed ellipse",DATUM["D_unknown",SPHEROID["Unknown",6370997,0]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["latitude_of_origin",40],PARAMETER["central_meridian",-97],PARAMETER["standard_parallel_1",33],PARAMETER["standard_parallel_2",45],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]')

            resultsISRM.to_file(filename='InMap/MIP_InMap_Output/'+scenario+'/'+model+'/ISRM_result_'+f"{year}"+'.shp', driver='ESRI Shapefile')
            