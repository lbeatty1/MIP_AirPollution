# Gen_Plant_Emissions
Code to analyze emissions from generation facilities, and impute emissions for clusters from PowerGenome.

## Data
EIA Data comes from EIA-860 and EIA-923 which can be downloaded at:
https://www.eia.gov/electricity/data/eia860/
https://www.eia.gov/electricity/data/eia923/

EPA Data comes from CAMD which is mostly accessed via API by the script Get_CAMD.py
However, additional data on PM2.5 comes from https://www.epa.gov/egrid/egrid-related-materials

EPA-EIA Power Sector Data Crosswalk (epa_eia_crosswalk.csv) can be downloaded at 
https://www.epa.gov/power-sector/power-sector-data-crosswalk

Other emissions data comes from 
https://www.epa.gov/air-emissions-modeling/2020-emissions-modeling-platform
which collects emissions data from NEI and links it to electricity generation ids in CAMD

dpr-data.xlsx - comes from the 'report data' at https://www.eia.gov/petroleum/drilling/
This gives me oil and gas production by basin.

## Repo

Get_CAMD.py - pulls EPA data from their API, sends to data directory

Calculate_Model_Emissions.ipynb - Takes EIA, EPA data, calculates emissions from MIP models, outputs shapefiles to be processed by inmap.  
InMap_SR.ipynb - takes emissions output and uses source-receptor matrices to calculate exposures
Plot_Output.ipynb - takes InMap Output (full inmap) and plots exposures and deaths.

run_airpollution.sh - runs all of the scripts in sequential order, including InMap.  It pulls InMap settings from InMap_config.toml
