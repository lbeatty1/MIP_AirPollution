import requests
import json
import pandas as pd
import requests
import zipfile
import os

# Set API key and base URL
# API Keys can be requested at https://www.epa.gov/power-sector/cam-api-portal#/api-key-signup
f = open("API_Key.json")
config = json.load(f) 
API_Key = config['API_Key']

data_directory = "C:/Users/laure/Documents/Switch-USA-PG/AirPollution_Data/"
base_url = "https://api.epa.gov/easey/"


camd_dir = os.path.join(data_directory, "CAMD")
os.makedirs(camd_dir, exist_ok=True)

# Function to fetch data
def fetch_data(endpoint, year):
    data = []
    page = 1
    while True:
        url = f"{base_url}{endpoint}?page={page}&perPage=100&year={year}"
        headers = {
            "x-api-key": API_Key,
            "accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json()
            data.extend(content)
            total_count = int(response.headers.get('X-Total-Count', 0))
            if total_count <= page * 100:
                break
            page += 1
        else:
            print(f"Failed to fetch data for year {year}, page {page}")
            break
    return data

# Fetch facilities attributes data
facilities_attributes_data = []
print('downloading facilities data')
for year in range(2015, 2022):
    endpoint = f"facilities-mgmt/facilities/attributes"
    facilities_attributes_data.extend(fetch_data(endpoint, year))

print('saving facilities data')
# Convert to DataFrame and save as CSV
facilities_attributes_df = pd.DataFrame(facilities_attributes_data)
facilities_attributes_df.to_csv(data_directory+"CAMD/facilities_attributes.csv", index=False)


# Fetch facilities emissions data
facilities_emissions_data = []
print('downloading emissions data')
for year in range(2020, 2022):
    endpoint = f"emissions-mgmt/emissions/apportioned/annual"
    facilities_emissions_data.extend(fetch_data(endpoint, year))

# Convert to DataFrame and save as CSV
print('saving emissions data')
facilities_emissions_df = pd.DataFrame(facilities_emissions_data)
facilities_emissions_df.to_csv(data_directory+"CAMD/facilities_emissions.csv", index=False)

##############################
## Download Other  Data #########
##############################

urls = [
    "https://www2.census.gov/programs-surveys/popest/tables/2020-2024/counties/totals/co-est2024-pop.xlsx",
    "https://www.eia.gov/electricity/data/eia860/archive/xls/eia8602022.zip",
    "https://www.eia.gov/electricity/data/eia923/archive/xls/f923_2022.zip",
    "https://gaftp.epa.gov/Air/emismod/2020/2020emissions/2020ha2_point_inventory_22sep2023.zip",
    "https://github.com/USEPA/camd-eia-crosswalk/releases/download/v0.3/epa_eia_crosswalk.csv",
    'https://www.epa.gov/system/files/documents/2024-06/egrid-draft-pm-emissions.xlsx',
    'https://www.epa.gov/sites/production/files/2019-08/ipm_v6_regions.zip'
]

for url in urls:
    filename = url.split("/")[-1]
    filepath = os.path.join(data_directory, filename)

    print(f"Downloading {filename}...")
    response = requests.get(url, stream=True, verify=False)
    if response.status_code == 200:
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved to {filepath}")

        if filename.endswith(".zip"):
            with zipfile.ZipFile(filepath, "r") as zip_ref:
                zip_ref.extractall(data_directory)
            print(f"Extracted {filename}")
            os.remove(filepath)  # Delete the ZIP file
            print(f"Deleted {filename}")
    else:
        print(f"Failed to download {url} (status {response.status_code})")
