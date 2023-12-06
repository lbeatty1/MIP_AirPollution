import requests
import json
import pandas as pd

# Set API key and base URL
# API Keys can be requested at https://www.epa.gov/power-sector/cam-api-portal#/api-key-signup
f = open("MIP_AirPollution/API_Key.json")
config = json.load(f) 
API_Key = config['API_Key']

data_directory = "C:/Users/lbeatty/Documents/Lauren_MIP_Contribution/Data/"
base_url = "https://api.epa.gov/easey/"

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
for year in range(2015, 2021):
    endpoint = f"facilities-mgmt/facilities/attributes"
    facilities_attributes_data.extend(fetch_data(endpoint, year))

# Convert to DataFrame and save as CSV
facilities_attributes_df = pd.DataFrame(facilities_attributes_data)
facilities_attributes_df.to_csv(data_directory+"facilities_attributes.csv", index=False)

# Fetch facilities emissions data
facilities_emissions_data = []
for year in range(2015, 2021):
    endpoint = f"emissions-mgmt/emissions/apportioned/annual"
    facilities_emissions_data.extend(fetch_data(endpoint, year))

# Convert to DataFrame and save as CSV
facilities_emissions_df = pd.DataFrame(facilities_emissions_data)
facilities_emissions_df.to_csv(data_directory+"facilities_emissions.csv", index=False)