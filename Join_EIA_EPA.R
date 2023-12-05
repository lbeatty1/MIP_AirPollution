rm(list=ls())

library(plyr)
library(sf)
library(tidyverse)
library(readxl)

setwd("C:/Users/laure/Documents/Gen_Plant_Emissions/")


###################
## Read in Data ###
###################

crosswalk = read.csv("Data/epa_eia_crosswalk.csv")
emissions = read.csv("Data/CAMD/facilities_emissions.csv")

#pm25
pm25=NULL
for(y in 2018:2020){
  sheetname=paste(y, "PM Unit-level Data")
  pm25_temp = read_excel("Data/eGRID2020 DRAFT PM Emissions.xlsx", sheet=sheetname, skip=1)
  pm25=rbind(pm25, pm25_temp)
}
pm25 = pm25%>%
  group_by(YEAR, ORISPL, UNITID)%>%
  summarise(pm25 = sum(PM25AN))
#pm25 reported in tons

####### 
# EIA 923 For Annual Generation
#######
eia923=NULL
files923 = list.files("Data/eia923/", full.names = T)
files923 = files923[which(grepl("2_3_4", files923))]
for(j in files923){
  tempdat = read_excel(j, sheet='Page 4 Generator Data', skip=5, .name_repair = "universal")
  eia923 = rbind.fill(eia923, tempdat)
  print(j)
}


eia923 = eia923%>%
  select(
    EIA_PLANT_ID = "Plant.Id",
    EIA_GENERATOR_ID = "Generator.Id",
    EIA_PLANT_NAME = "Plant.Name",
    EIA_STATE = "Plant.State",
    NET_GEN = "Net.Generation..Year.To.Date",
    YEAR)
  
#### 
## EIA 860 for Generator Info 
####

eia860=NULL
files860 = list.files("Data/eia860/", full.names = T)
files860 = files860[which(grepl("Generator", files860))]
for(j in files860){
  tempdat = read_excel(j, skip=1, .name_repair = "universal")
  tempdat$year = substr(j,28,31)
  eia860 = rbind.fill(eia860, tempdat)
  print(j)
}

eia860 = eia860%>%
  select(EIA_PLANT_ID = "Plant.Code",
         EIA_GENERATOR_ID = "Generator.ID",
         Capacity = "Nameplate.Capacity..MW.",
         RetirementYear = "Planned.Retirement.Year",
         RetirementMonth = "Planned.Retirement.Month",
         SynchronizedToGrid  ="Synchronized.to.Transmission.Grid",
         year)%>%
  mutate(year=as.numeric(year))

##############################
## Join CAMD with Crosswalk ##
##############################

#Note: Emissions are reported at the unit level which can aggregate multiple boilers
# I'm going to sum eia reported values within unit to avoid double-counting

#start by combining 860 and 923
eia_joined = left_join(eia923, eia860, by=c("EIA_PLANT_ID", "EIA_GENERATOR_ID", "YEAR"="year"))
if(nrow(eia923)==nrow(eia_joined)){
  print("One-to-one Join")
}else{
  print("Inspect Join for many to one matches.")
}

#now merge crosswalk into eia so that we can collapse eia by camd facility, unit
#only need a few variables from crosswalk
crosswalk <- crosswalk %>%
  select(
    CAMD_PLANT_ID,
    CAMD_UNIT_ID,
    CAMD_GENERATOR_ID,
    EIA_PLANT_ID,
    EIA_GENERATOR_ID,
    EIA_UNIT_TYPE
  )
eia_joined = left_join(eia_joined, crosswalk, by=c("EIA_PLANT_ID", "EIA_GENERATOR_ID"))
if(nrow(eia923)==nrow(eia_joined)){
  print("One-to-one Join")
}else{
  print("Inspect Join for many to one matches.")
}

eia_collapsed = eia_joined%>%
  group_by(CAMD_PLANT_ID, CAMD_UNIT_ID, YEAR)%>%
  summarise(NET_GEN = sum(NET_GEN),
            Capacity = sum(Capacity))

## Join CAMD with PM25
nrow(emissions)
emissions = left_join(emissions, pm25, by=c("facilityId"="ORISPL", "unitId"="UNITID", "year"="YEAR"))
nrow(emissions)
#############
#Join with CAMD
camd_eia_data = left_join(emissions, eia_collapsed, by=c("facilityId"="CAMD_PLANT_ID", "unitId"="CAMD_UNIT_ID", "year"="YEAR"))

############
## Examine Coal
camd_eia_data_coal <- camd_eia_data %>%
  filter(grepl("Coal", primaryFuelInfo)) %>%
  filter(facilityId < 880000) #filter out non-grid-connected units

camd_eia_data_coal <- camd_eia_data_coal %>%
  mutate(nox_lbs = noxMass*2000,
         NOX_RATE = nox_lbs/NET_GEN,
         so2_lbs = so2Mass*2000,
         so2_rate = so2_lbs/NET_GEN,
         pm25_lbs = pm25*2000,
         pm25_rate = pm25_lbs/NET_GEN)

ggplot(camd_eia_data_coal)+
  geom_point(aes(x=NET_GEN, y=NOX_RATE, color=factor(year)))+
  ylim(0,19)+
  ylab("NOx Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/NoxRate_AnnualGen_coal.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_coal)+
  geom_point(aes(x=NET_GEN, y=so2_rate, color=factor(year)))+
  ylim(0,30)+
  ylab("SO2 Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_AnnualGen_coal.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_coal)+
  geom_point(aes(x=NET_GEN, y=so2_rate, color=factor(year)))+
  ylim(0,30)+
  ylab("SO2 Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_AnnualGen_coal.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_coal%>%filter(year>=2018))+
  geom_point(aes(x=NET_GEN, y=pm25_rate, color=factor(year)))+
  ylim(0,5)+
  ylab("PM2.5 Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/PM25_AnnualGen_coal.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_coal)+
  geom_point(aes(x=Capacity, y=NOX_RATE, color=factor(year)))+
  ylim(0,19)+
  ylab("NOx Rate (lbs/MWh)")+
  xlab("Capacity (MW)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/NoxRate_Capacity_coal.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_coal)+
  geom_point(aes(x=Capacity, y=so2_rate, color=factor(year)))+
  ylim(0,30)+
  ylab("SO2 Rate (lbs/MWh)")+
  xlab("Capacity (MW)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_Capacity_coal.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_coal%>%filter(year>=2018))+
  geom_point(aes(x=Capacity, y=pm25_rate, color=factor(year)))+
  ylim(0,5)+
  ylab("PM2.5 Rate (lbs/MWh)")+
  xlab("Capacity (MW)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/PM25_Capacity_coal.jpg",
       height=5,
       width=8)

#Make generation weighted emissions over time
yearly_coal_emissions = camd_eia_data_coal%>%
  group_by(year)%>%
  mutate(NoxRate_weighted = NOX_RATE*NET_GEN,
         So2Rate_weighted = so2_rate*NET_GEN)%>%
  summarise(NoxRate_weighted = sum(NoxRate_weighted, na.rm=T),
            So2Rate_weighted = sum(So2Rate_weighted, na.rm=T),
            NET_GEN = sum(NET_GEN, na.rm=T))%>%
  mutate(NoxRate_weighted = NoxRate_weighted/NET_GEN,
         So2Rate_weighted = So2Rate_weighted/NET_GEN)

ggplot(data=yearly_coal_emissions)+
  geom_line(aes(x=year, y=NoxRate_weighted))+
  ylab("Generation-weighted average Nox Rate (lbs/Mwh)")+
  xlab("Year")+
  ggtitle("NOx Emissions Rate: Coal Plants")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/NoxRate_timeseries_coal.jpg",
       height=5,
       width=8)

ggplot(data=yearly_coal_emissions)+
  geom_line(aes(x=year, y=So2Rate_weighted))+
  ylab("Generation-weighted average So2 Rate (lbs/Mwh)")+
  xlab("Year")+
  ggtitle("SO2 Emissions Rate: Coal Plants")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_timeseries_coal.jpg",
       height=5,
       width=8)

################
## Natural Gas

camd_eia_data_natgas <- camd_eia_data %>%
  filter(grepl("Natural Gas", primaryFuelInfo),
         !grepl("Coal", primaryFuelInfo)) %>%
  filter(facilityId < 880000) #filter out non-grid-connected units

camd_eia_data_natgas <- camd_eia_data_natgas %>%
  mutate(nox_lbs = noxMass*2000,
         NOX_RATE = nox_lbs/NET_GEN,
         so2_lbs = so2Mass*2000,
         so2_rate = so2_lbs/NET_GEN,
         pm25_lbs = pm25*2000,
         pm25_rate = pm25_lbs/NET_GEN)

ggplot(camd_eia_data_natgas)+
  geom_point(aes(x=NET_GEN, y=NOX_RATE, color=factor(year)))+
  ylim(0,19)+
  ylab("NOx Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/NoxRate_AnnualGen_natgas.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_natgas)+
  geom_point(aes(x=NET_GEN, y=so2_rate, color=factor(year)))+
  ylim(0,30)+
  ylab("SO2 Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_AnnualGen_natgas.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_natgas%>%filter(year>=2018))+
  geom_point(aes(x=NET_GEN, y=pm25_rate, color=factor(year)))+
  ylim(0,3)+
  ylab("PM25 Rate (lbs/MWh)")+
  xlab("Annual Net Generation (MWh)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/PM25_AnnualGen_natgas.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_natgas)+
  geom_point(aes(x=Capacity, y=NOX_RATE, color=factor(year)))+
  ylim(0,19)+
  ylab("NOx Rate (lbs/MWh)")+
  xlab("Capacity (MW)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/NoxRate_Capacity_natgas.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_natgas)+
  geom_point(aes(x=Capacity, y=so2_rate, color=factor(year)))+
  ylim(0,30)+
  ylab("SO2 Rate (lbs/MWh)")+
  xlab("Capacity (MW)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_Capacity_natgas.jpg",
       height=5,
       width=8)

ggplot(camd_eia_data_natgas%>%filter(year>=2018))+
  geom_point(aes(x=Capacity, y=pm25_rate, color=factor(year)))+
  ylab("PM25 Rate (lbs/MWh)")+
  xlab("Capacity (MW)")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/PM25_AnnualGen_natgas.jpg",
       height=5,
       width=8)


#Make generation weighted emissions over time
yearly_natgas_emissions = camd_eia_data_natgas%>%
  group_by(year)%>%
  mutate(NoxRate_weighted = NOX_RATE*NET_GEN,
         So2Rate_weighted = so2_rate*NET_GEN)%>%
  summarise(NoxRate_weighted = sum(NoxRate_weighted, na.rm=T),
            So2Rate_weighted = sum(So2Rate_weighted, na.rm=T),
            NET_GEN = sum(NET_GEN, na.rm=T))%>%
  mutate(NoxRate_weighted = NoxRate_weighted/NET_GEN,
         So2Rate_weighted = So2Rate_weighted/NET_GEN)

ggplot(data=yearly_natgas_emissions)+
  geom_line(aes(x=year, y=NoxRate_weighted))+
  ylab("Generation-weighted average Nox Rate (lbs/Mwh)")+
  xlab("Year")+
  ggtitle("NOx Emissions Rate: natgas Plants")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/NoxRate_timeseries_natgas.jpg",
       height=5,
       width=8)

ggplot(data=yearly_natgas_emissions)+
  geom_line(aes(x=year, y=So2Rate_weighted))+
  ylab("Generation-weighted average So2 Rate (lbs/Mwh)")+
  xlab("Year")+
  ggtitle("SO2 Emissions Rate: natgas Plants")+
  theme_bw()
ggsave(filename="Gen_Plant_Emissions/Figures/So2Rate_timeseries_natgas.jpg",
       height=5,
       width=8)


######################
## Notes for future Lauren
### 
#Powergenome clusters at the EIA Generator level
#This means that some CAMD Units will be in two separate clusters (For example a nat gas plant with both CT and ST)
#IDK what to do about this 



##########
## What about missings?
##

missing=camd_eia_data%>%filter(is.na(NET_GEN))
missing=left_join(missing, crosswalk, by=c("facilityId"="CAMD_PLANT_ID", "unitId"="CAMD_UNIT_ID"))

#missings are largely present in EIA-860 but not in 923
#think they might just be shut down a lot?
notmissing=camd_eia_data%>%filter(!is.na(NET_GEN))
mean(notmissing$so2Mass,na.rm=T)
mean(missing$so2Mass,na.rm=T)

#couple missings are because of mismatches in unit eg plant 56609