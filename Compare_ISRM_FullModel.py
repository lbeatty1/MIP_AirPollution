#%%
globals().clear()

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
import math
from matplotlib.colors import LinearSegmentedColormap



os.chdir('C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/')


models=['GenX']
scenarios = ['26z-short-base-50']
years = ['2030', '2040', '2050']

for model in models:
    for scenario in scenarios:
        for year in years:
            quant_dict={}
            emissions_full = gpd.read_file('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/emissions'+year+'_out.shp')
            emissions_ISRM = gpd.read_file('InMap/MIP_InMap_Output/'+scenario+'/'+model+'/ISRM_result_'+year+'.shp')


            states = gpd.read_file('tl_2022_us_state/tl_2022_us_state.shp')
            states = states[~states['STUSPS'].isin(['AS', 'AK', 'GU', 'MP', 'VI', 'HI', 'PR'])]

            print('finding intersection with land')
            ## Make all crs equal and throw out grid cells outside of U.S.
            states = states.to_crs(emissions_full.crs)
            intersects = emissions_full.geometry.intersects(states.unary_union)
            emissions_full['intersects'] = intersects
            emissions_full = emissions_full[emissions_full['intersects']==True]

            ## Make all crs equal and throw out grid cells outside of U.S.
            intersects = emissions_ISRM.geometry.intersects(states.unary_union)
            emissions_ISRM['intersects'] = intersects
            emissions_ISRM = emissions_ISRM[emissions_ISRM['intersects']==True]

            #want scales to be the same for each plot

            q = 0.99  # Truncate results at the 99th percentile for better visualization
            cut = np.quantile(emissions_full['TotalPM25'], q)
            cut2 = np.quantile(emissions_ISRM['TotalPM25'],q)
            cut = max(cut, cut2)
            quant_dict['TotalPM25']=cut

            fig, (ax1,ax2) = plt.subplots(nrows=1, ncols=2, figsize=(20, 16))
            ax1 = emissions_full.plot(vmin=0, vmax=cut, cmap="OrRd", column='TotalPM25', ax=ax1)
            ax2 = emissions_ISRM.plot(vmin=0, vmax=cut, cmap="OrRd", column='TotalPM25', ax=ax2)
            # Plot data with color scale truncated at the specified quantile
            states.boundary.plot(ax=ax1, color='black', linewidth=0.2)
            states.boundary.plot(ax=ax2, color='black', linewidth=0.2)


            #set titles
            # Set titles
            ax1.set_title("Full InMAP Model")
            ax2.set_title("ISRM")

            # Remove x and y ticks
            ax1.set_xticks([])
            ax1.set_yticks([])
            ax2.set_xticks([])
            ax2.set_yticks([])

            # Add color bar
            sm = plt.cm.ScalarMappable(cmap='OrRd', norm=plt.Normalize(vmin=0, vmax=quant_dict['TotalPM25']))
            sm._A = []  # Fake empty array for the colorbar
            cbar = fig.colorbar(sm, fraction=0.03)  
            cbar.set_label('PM25' +' concentration (μg m$^{-3}$)')  # Set color bar label

            plt.savefig('MIP_AirPollution/Figures/Output/' + scenario+ '_'+ model +'_'+year+ '_compare_full_ISRM.png', format='png',dpi=300, bbox_inches='tight')
            plt.savefig('MIP_results_comparison/AirPollution/' + scenario+ '_'+ model +'_'+year+ '_compare_full_ISRM.png', format='png',
                        dpi=300, bbox_inches='tight')
