require(supportR)
require(usethis)
require(readr)
require(RCurl)
require(ggplot2)
require(dplyr)
require(tidyr)
library(sf)
library(RColorBrewer)

setwd("C:/Users/laure/Documents/Switch-USA-PG/")

annual_tx_expansion = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/annual_tx_expansion.csv')
capacity = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/capacity.csv')
emissions = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/emissions.csv')
generation = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/generation.csv')
operational_costs = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/operational_costs.csv')

regions = st_read('Data/IPM_Regions/national_emm_boundaries.shp')
regions = regions%>%
  mutate(model_regi=replace(model_regi, model_regi=='TRE_WEST', 'TREW'))
regions_centroids = st_centroid(regions)

techs <- data.frame(tech_type = levels(factor(generation$tech_type)), 
                    plot = c("Battery", 
                             "CCS", 
                             "Coal", 
                             "Dist. Solar",
                             "Geothermal",
                             "Hydro",
                             "Hydrogen",
                             "Nat Gas CC", 
                             "Nat Gas CT", 
                             "Nuclear",
                             "Solar", 
                             "Wind"),
                    source = c("Battery", 
                               "CCS",
                               "Coal",
                               "Solar",
                               "Geother",
                               "Hydro",
                               "Hydrogen",
                               "Nat Gas",
                               "Nat Gas",
                               "Nuclear",
                               "Solar",
                               "Wind"))

# create dataframe to assign and filter results by scenario and configuration

cases <- data.frame(case = levels(factor(emissions$case)),
                    tx = NA)


cases$tx <- ifelse(grepl("tx-0", cases$case), "tx 0 perc  ",
                   ifelse(grepl("tx-15", cases$case), "tx 15 perc ",
                          ifelse(grepl("tx-50", cases$case), "tx 50 perc ", "unconstrain")))  




# create dataframe to simplify labels
annual_tx_expansion = left_join(annual_tx_expansion, 
                                regions_centroids, 
                                by=c('start_region'='model_regi'))
annual_tx_expansion = annual_tx_expansion%>%
  rename(start_centroid = geometry)

annual_tx_expansion = left_join(annual_tx_expansion, 
                                regions_centroids, 
                                by=c('dest_region'='model_regi'))

annual_tx_expansion = annual_tx_expansion%>%
  rename(dest_centroid = geometry)%>%
  group_by(model, case, line_name)%>%
  arrange(planning_year)%>%
  mutate(tot_transmission=cumsum(value))

annual_tx_expansion = annual_tx_expansion %>%
  rowwise() %>%
  mutate(geometry = st_sfc(st_linestring(rbind(st_coordinates(start_centroid), st_coordinates(dest_centroid))))) %>%
  st_as_sf()
st_crs(annual_tx_expansion$geometry) = st_crs(regions)


for(case_id in cases$case){
  print(paste0('making transmission chart for: ', case_id))
  
  tempdat = annual_tx_expansion%>%
    filter(case==case_id,
           planning_year!=2023)
  
  ggplot() +
    geom_sf(data=regions, fill='antiquewhite')+
    geom_sf(data = tempdat, aes(geometry=geometry, color = tot_transmission), size = 1) +
    scale_color_viridis_c()+
    theme_bw() +
    labs(color = "MW") +
    facet_grid(rows = vars(planning_year), cols = vars(model))+
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/transmission_all_models_', case_id, '.png'),
         device='png',
         width=8,
         height=10)
  
}

### make plots relative to full-base-200
for(case_id in c('full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx-50')){
  print(paste0('making transmission chart for: ', case_id))
  
  tempdat = annual_tx_expansion%>%filter(case==case_id|case=='full-base-200')
  tempdat = pivot_wider(tempdat, id_cols = c('model', 'planning_year', 'geometry'), names_from='case', values_from='tot_transmission')
  
  tempdat = tempdat%>%
    mutate(dif_mw = `full-base-200`- !!sym(case_id))%>%
    filter(planning_year!=2023)%>%
    st_sf()
  
  ggplot() +
    geom_sf(data=regions, fill='antiquewhite')+
    geom_sf(data = tempdat, aes(geometry=geometry, color = dif_mw), size = 1) +
    scale_color_viridis_c()+
    ggtitle(paste0("Difference Between Unconstrained Optimum and Constrained Transmission \n", case_id))+
    theme_bw() +
    labs(color = "MW") +
    facet_grid(rows = vars(planning_year), cols = vars(model))+
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/transmission_relative_', case_id, '.png'),
         device='png',
         width=8,
         height=10)
}

#what is the effect on emissions?
emissions = emissions%>%
  group_by(model, planning_year, case)%>%
  summarise(value=sum(value))%>%
  filter(planning_year>=2030)

ggplot(emissions, aes(x = planning_year, y = value/1e8, color = model, shape = case)) +
  geom_line(size = 1) +  
  geom_point(size = 3) + 
  theme_bw() +
  labs(
    title = "Emissions",
    x = "Planning Year",
    y = "Emissions (Billion Tons)",
    color = "Model",
    shape = "Case"
  )

ggsave(filename='MIP_AirPollution/Figures/MIP_Paper/emissions_transmission.png',
       device='png',
       width=6,
       height=4)


#explore substitution
for(case_id in c('full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx-50')){
  print(paste0('making capacity chart for: ', case_id))
  tempdat = capacity%>%
    filter(planning_year==2050,
           case%in%c(case_id, 'full-base-200'))%>%
    group_by(model, zone, tech_type, case)%>%
    summarise(end_value=sum(end_value))

  tempdat = pivot_wider(tempdat, id_cols = c('model','tech_type', 'zone'), names_from='case', values_from='end_value')
  tempdat = left_join(tempdat, regions, by=c("zone"='model_regi'))
  
  tempdat = tempdat%>%
    mutate(dif_mw = `full-base-200`- !!sym(case_id))%>%
    st_sf()
  
  ggplot(tempdat)+
    geom_sf(aes(geometry=geometry, fill=dif_mw))+
    scale_fill_viridis_c()+
    facet_grid(rows=vars(tech_type), cols=vars(model))+
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/capacity_relative', case_id, '.png'),
         device='png',
         width=8,
         height=10)
}



#explore substitution
for(case_id in c('full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx-50')){
  print(paste0('making capacity chart for: ', case_id))
  tempdat = capacity%>%
    filter(planning_year==2050,
           case%in%c(case_id, 'full-base-200'),
           tech_type%in%c('Solar', 'Wind', 'CCS'))%>%
    group_by(model, zone, tech_type, case)%>%
    summarise(end_value=sum(end_value))
  
  tempdat = pivot_wider(tempdat, id_cols = c('model','tech_type', 'zone'), names_from='case', values_from='end_value')
  tempdat = left_join(tempdat, regions, by=c("zone"='model_regi'))
  
  tempdat = tempdat%>%
    mutate(dif_mw = `full-base-200`- !!sym(case_id))%>%
    st_sf()
  
  tempdat_transmission = annual_tx_expansion%>%filter(case==case_id|case=='full-base-200')
  tempdat_transmission = pivot_wider(tempdat_transmission, id_cols = c('model', 'planning_year', 'geometry'), names_from='case', values_from='tot_transmission')
  
  tempdat_transmission = tempdat_transmission%>%
    mutate(dif_mw = `full-base-200`- !!sym(case_id))%>%
    filter(planning_year==2050)%>%
    st_sf()
  
  ggplot(tempdat)+
    geom_sf(aes(geometry=geometry, fill=dif_mw))+
    geom_sf(data=tempdat_transmission, aes(geometry=geometry, col=dif_mw))+
    scale_fill_viridis_c(name="Generation Capacity \n Dif (MW)")+
    scale_color_viridis_c(name="Transmission Capacity \n Dif (MW)")+
    ggtitle(paste0('Differences in Generation and Transmission Capacity Relative to Unconstrained: \n', case_id))+
    facet_grid(rows=vars(tech_type), cols=vars(model))+
    theme_bw()+
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/capacity_relative_with_transmission_', case_id, '.png'),
         device='png',
         width=8,
         height=6)
}
