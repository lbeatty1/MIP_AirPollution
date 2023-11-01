rm(list=ls())

library(httr2)
library(tidyverse)
library(jsonlite)


setwd("C:/Users/laure/Documents/Gen_Plant_Emissions/")

source("Gen_Plant_Emissions/API_Key.R")

# facilities = request("https://api.epa.gov/easey/facilities-mgmt/facilities")%>%
#   req_headers(`x-api-key`=API_Key,
#               `accept`= "application/json")%>%
#   req_perform()
# 
# facilities = fromJSON(rawToChar(facilities$body))

facilities_attributes_data=NULL
for(y in 2015:2020){
  url=paste("https://api.epa.gov/easey/facilities-mgmt/facilities/attributes?page=1&perPage=100&year=", y, sep="")
  facilities_attributes = request(url)%>%
    req_headers(`x-api-key`=API_Key,
                `accept`= "application/json")%>%
    req_perform()
  
  num_pages = ceiling(as.numeric(facilities_attributes$headers$`X-Total-Count`)/100)
  
  facilities_attributes = fromJSON(rawToChar(facilities_attributes$body))
  facilities_attributes_data=rbind(facilities_attributes_data, facilities_attributes)
  for(p in 2:num_pages){
    url=paste("https://api.epa.gov/easey/facilities-mgmt/facilities/attributes?page=", p, "&perPage=100&year=", y, sep="")
    facilities_attributes = request(url)%>%
      req_headers(`x-api-key`=API_Key,
                  `accept`= "application/json")%>%
      req_perform()
    facilities_attributes = fromJSON(rawToChar(facilities_attributes$body))
    facilities_attributes_data=rbind(facilities_attributes_data, facilities_attributes)
    print(p)
  }
}
write.csv(facilities_attributes_data, "Data/CAMD/facilities_attributes.csv")


facilities_emissions_data=NULL
for(y in 2015:2020){
  url=paste("https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/annual?page=1&perPage=100&year=", y, sep="")
  facilities_emissions = request(url)%>%
    req_headers(`x-api-key`=API_Key,
                `accept`= "application/json")%>%
    req_perform()
  
  num_pages = ceiling(as.numeric(facilities_emissions$headers$`X-Total-Count`)/100)
  
  facilities_emissions = fromJSON(rawToChar(facilities_emissions$body))
  facilities_emissions_data=rbind(facilities_emissions_data, facilities_emissions)
  for(p in 2:num_pages){
    url=paste("https://api.epa.gov/easey/emissions-mgmt/emissions/apportioned/annual?page=", p, "&perPage=100&year=", y, sep="")
    facilities_emissions = request(url)%>%
      req_headers(`x-api-key`=API_Key,
                  `accept`= "application/json")%>%
      req_perform()
    facilities_emissions = fromJSON(rawToChar(facilities_emissions$body))
    facilities_emissions_data=rbind(facilities_emissions_data, facilities_emissions)
    print(p)
  }
}
write.csv(facilities_emissions_data, "Data/CAMD/facilities_emissions.csv")

