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
