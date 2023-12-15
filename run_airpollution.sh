cd C:/Users/lbeatty/Documents/Lauren_MIP_Contribution

set evaldata=C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/InMap/evaldata_v1.6.1
set emissionsfile=InMap/MIP_Emissions/26z-thin-debug/SWITCH/emissions_2030.shp

python MIP_AirPollution/Get_CAMD.py
python MIP_AirPollution/Calculate_Model_Emissions.py

InMap\inmap-v1.9.6-windows-amd64.exe run steady --config=MIP_AirPollution\InMap_config.toml

set emissionsfile=InMap/MIP_Emissions/26z-thin-debug/SWITCH/emissions_2040.shp
InMap\inmap-v1.9.6-windows-amd64.exe run steady --config=MIP_AirPollution\InMap_config.toml
