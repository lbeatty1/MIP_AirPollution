# Introduction
This repo is designed to model air pollution and jobs from least-cost electricity planning models.  The scripts in `/Downscaled/` are used to take output from `MIP_results_comparison` and project air pollution and jobs impacts.  The scripts in `\Endogenous\` are used to generate cluster-level coefficients that can be used to endogenize air pollution exposure within Switch.

# Installation

Follow the steps at <https://github.com/switch-model/Switch-USA-PG>. Then clone this repository within `Switch-USA-PG`.  This code has a few dependencies so you will also need to type `mamba env update -n switch-pg -f MIP_AirPollution/environment.yml` when you are in the `(base)` environment.

# Running the Endogenous Model
1. Navigate into the Switch-USA-PG folder and activate the `switch-pg` environment.
2. Type `python download_pg_data.py`into the terminal to download necessary data.
3. You will also need data on air pollution emissions. You can download all of this by running `python download_data.py`. You will need a CAMD API key to access this data. Save the API key in `MIP_AirPollution/API_Key.json`.  You can request an API key at <https://www.epa.gov/power-sector/cam-api-portal>.  Other data comes from 
    - EIA 860 and 923: https://www.eia.gov/electricity/data/eia860/
https://www.eia.gov/electricity/data/eia923/
    - NEI: https://www.epa.gov/air-emissions-modeling/2020-emissions-modeling-platform
    - EPA-EIA Power Sector Crosswalk: https://www.epa.gov/power-sector/power-sector-data-crosswalk
    - County-level population data https://www.census.gov/data/tables/time-series/demo/popest/2020s-counties-total.html#v2022
    - EPA linked emissions data from NEI to ids in CAMD: https://www.epa.gov/air-emissions-modeling/2020-emissions-modeling-platform
    - EPA eGRID: https://www.epa.gov/system/files/documents/2024-01/egrid2022_data.xlsx
4. You will also need data from https://drive.google.com/drive/u/0/folders/1fwem9RcmCimD992x6FWzwZXc6HcVWi9P which links existing facilities with resource clusters.

4. Generate inputs for switch `python pg_to_switch.py MIP_results_comparison/case_settings/26-zone/settings-atb2023 switch/26-zone/in/ --case-id current_policies_52_week`
5. Generate emissions locations then cluster-year exposure coefficients with `Gen_Emissions_Locations.py` and `InMap_SR_GenConstraints.py`, respectively.
6. Run switch with the exposure module
    - set `switch` as the working directory -- `cd switch`
    - `python setup_exposure_scenarios.py`
    - Run the base cost-minimization. `switch solve-scenarios --scenario-list scenarios_1.txt`
    - Run the minimizing exposure part. `switch solve-scenarios --scenario-list scenarios_2.txt`

## Data
dpr-data.xlsx - comes from the 'report data' at https://www.eia.gov/petroleum/drilling/
This gives me oil and gas production by basin.
## Repo

Get_CAMD.py - pulls EPA data from their API, sends to data directory

The other parts of the code are split into two folders: Downscaled and Endogenous. The Downcaled code takes MIP outputs and generates concentrations while the endogenous folder calculates cluster-level population-weighted marginal generation impacts on air pollution exposure.

Downscaled
Calculate_Model_Emissions.py - Takes EIA, EPA data, calculates emissions from MIP models, outputs shapefiles to be processed by inmap.  
InMap_SR.ipynb - takes emissions output and uses source-receptor matrices to calculate exposures
Plot_Output.ipynb - takes InMap Output (full inmap) and plots exposures and deaths.
