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

## Code lifted (almost) directly from https://www.inmap.run/blog/2022/12/15/tutorial/

os.chdir('C:/Users/laure/Documents/Switch-USA-PG/')

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

rl = 's3://inmap-model/isrm_v1.2.1.zarr/'
url = 's3://inmap-model/isrm_v1.2.1.zarr/'

fs = s3fs.S3FileSystem(anon=True, client_kwargs=dict(region_name='us-east-2'))
sr = zarr.open(s3fs.S3Map(url, s3=fs, check=False), mode="r")

p = poly(sr)

years = ['2027', '2030', '2035', '2040']
scenario = 'base_short'
simplified=True

for year in years:
    filename='MIP_Air_OutData/MIP_Emissions/'+ scenario+ '_marginal_emissions_'+str(year)+'.shp'
    if simplified==True:
             filename='MIP_Air_OutData/MIP_Emissions/'+ scenario+ '_marginal_emissions_'+str(year)+'_simplified.shp'

    emis = gpd.read_file(filename)
    fact = 28766.639

    df = pd.DataFrame({'Location': range(52411)})
    p = poly(sr)
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


    #pull out relevant matrix elements
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

    exposure_data = pd.DataFrame()
    BlackPop = sr['Black'][0:52411]
    AsianPop = sr['Asian'][0:52411]
    NativePop = sr['Native'][0:52411]
    LatinoPop = sr['Latino'][0:52411]
    WhiteNoLatPop = sr['WhiteNoLat'][0:52411]

    pollution_dict = dict(zip(['VOC', 'NOx', 'NH3', 'SOx', 'PM2_5'], [SOA, pNO3, pNH4, pSO4, PM25]))
        
    for pollutant in ['VOC', 'NOx', 'NH3', 'SOx', 'PM2_5']:
            for i in range(len(index)):
                exposure = pollution_dict[pollutant][0, dictionary[index[i]], :]*emis[pollutant][i]*fact
                group=1
                for column in [BlackPop, AsianPop, NativePop, LatinoPop, WhiteNoLatPop]:
                    sumpop = sum(column)
                    weighted_exposure = sum(exposure*column)/sumpop

                    data = {'Group':[group], 'Pollutant':pollutant, 'Exposure': [weighted_exposure], 'Cluster': [emis.Resource[i]]}
                    df = pd.DataFrame(data)
                    exposure_data = pd.concat([exposure_data, df])
                    if i % 5000 == 0:
                        print("Iteration:", i)
                        print(pollutant)
                    group=group+1
    
    # collapse output
    exposure_data.loc[exposure_data['Group'] == 1, 'Race'] = 'Black'
    exposure_data.loc[exposure_data['Group'] == 2, 'Race'] = 'Asian'
    exposure_data.loc[exposure_data['Group'] == 3, 'Race'] = 'Native'
    exposure_data.loc[exposure_data['Group'] == 4, 'Race'] = 'Latino'
    exposure_data.loc[exposure_data['Group'] == 5, 'Race'] = 'WhiteNoLat'

    exposure_data_collapsed = exposure_data.groupby(['Race', 'Cluster','Pollutant']).agg({'Exposure':'sum'}).reset_index()
    exposure_data_collapsed['year']=year

    if simplified==False:
        exposure_data_collapsed.to_csv('MIP_Air_OutData/Marginal_Coefficients/' + scenario+'_marginal_exposure_coefs_'+year+'.csv')
    if simplified==True:
        exposure_data_collapsed.to_csv('MIP_Air_OutData/Marginal_Coefficients/' + scenario+'_marginal_exposure_coefs_'+year+'_simplified.csv')



