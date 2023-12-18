cd C:/Users/lbeatty/Documents/Lauren_MIP_Contribution

set evaldata=C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/InMap/evaldata_v1.6.1

:: python MIP_AirPollution/Get_CAMD.py
:: python MIP_AirPollution/Calculate_Model_Emissions.py

set emissionsfile=InMap/MIP_Emissions/26z-thin-debug/SWITCH/emissions_2030.shp
set outputfile=emissions2030_out
InMap\inmap-v1.9.6-windows-amd64.exe run steady --config=MIP_AirPollution\InMap_config.toml

set emissionsfile=InMap/MIP_Emissions/26z-thin-debug/SWITCH/emissions_2040.shp
set outputfile=emissions2040_out
InMap\inmap-v1.9.6-windows-amd64.exe run steady --config=MIP_AirPollution\InMap_config.toml

set emissionsfile=InMap/MIP_Emissions/26z-thin-debug/SWITCH/emissions_2050.shp
set outputfile=emissions2050_out
InMap\inmap-v1.9.6-windows-amd64.exe run steady --config=MIP_AirPollution\InMap_config.toml
