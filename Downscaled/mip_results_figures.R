library(ggplot2)
library(tidyverse)
library(sf)
library(RColorBrewer)

setwd("C:/Users/laure/Documents/Switch-USA-PG/")

pal = brewer.pal(9, 'BuGn')
pal2 = brewer.pal(9, 'YlOrRd')


annual_tx_expansion = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/annual_tx_expansion.csv')
capacity = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/capacity.csv')
emissions = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/emissions.csv')
generation = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/generation.csv')
operational_costs = read.csv('MIP_results_comparison/compiled_results/transmission_expansion/operational_costs.csv')

regions = st_read('Data/IPM_Regions/national_emm_boundaries.shp')
regions = regions%>%
  mutate(model_regi=replace(model_regi, model_regi=='TRE_WEST', 'TREW'))
regions_centroids = st_centroid(regions)

case_id_dict = c(
  'full-base-200' = '52-week, $200,Unconstrained',
  'full-base-200-tx-50' = '52-week, $200,50% Constraint',
  'full-base-200-tx-15' = '52-week, $200, 15% Constraint',
  'full-base-200-tx-0' = '52-week, $200, 0% Constraint'
)

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




#make transmission expansion map
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
  filter(planning_year>=2035)%>%
  mutate(case=factor(case,
                     levels=c('full-base-200-tx-0','full-base-200-tx-15','full-base-200-tx-50','full-base-200')))

ggplot(emissions, aes(x = planning_year, y = value / 1e8, color = case, shape = model)) +
  geom_line(size = 0.5) +  
  geom_point(size = 2) + 
  scale_shape_manual(values = c('GenX' = 15, 
                                'SWITCH' = 16, 
                                'USENSYS' = 17, 
                                'TEMOA' = 18)) +
  scale_color_discrete(labels = c('full-base-200' = '52-week, $200,\nunlimited expansion\n',
                                'full-base-200-tx-0' = '52-week, $200,\n0% expansion\n',
                                'full-base-200-tx-15' = '52-week, $200,\n15% expansion\n',
                                'full-base-200-tx-50' = '52-week, $200,\n50% expansion\n')) +
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



#explore substitution with transmission overlay
models = c('SWITCH', 'GenX')
tech_types = c('Solar', 'Wind', 'CCS')
for(case_id in c('full-base-200-tx-0', 'full-base-200-tx-15', 'full-base-200-tx-50')){
  print(paste0('making capacity chart for: ', case_id))
  formatted_case_id = case_id_dict[case_id]
  
  tempdat = capacity%>%
    filter(planning_year==2050,
           case%in%c(case_id, 'full-base-200'),
           tech_type%in%tech_types,
           model %in%models)%>%
    group_by(model, zone, tech_type, case)%>%
    summarise(end_value=sum(end_value))
  
  tempdat = pivot_wider(tempdat, id_cols = c('model','tech_type', 'zone'), names_from='case', values_from='end_value')
  #make sure to get missings
  missings = expand.grid(model=models, zone=unique(tempdat$zone), tech_type=tech_types)
  tempdat = full_join(tempdat, missings, by=c('model', 'zone', 'tech_type'))
  tempdat = left_join(tempdat, regions, by=c("zone"='model_regi'))
  
  tempdat = tempdat%>%
    mutate(across(starts_with('full-base'), ~ replace_na(.x, 0)),
           dif_mw = `full-base-200`- !!sym(case_id),
           dif_pct = dif_mw/`full-base-200`)%>%
    st_sf()
  
  tempdat_transmission = annual_tx_expansion%>%filter(case==case_id|case=='full-base-200')
  tempdat_transmission = pivot_wider(tempdat_transmission, id_cols = c('model', 'planning_year', 'geometry'), names_from='case', values_from='tot_transmission')
  
  tempdat_transmission = tempdat_transmission%>%
    mutate(across(starts_with('full-base'), ~ replace_na(.x, 0)),
           dif_mw = `full-base-200`- !!sym(case_id),
           dif_pct = dif_mw/`full-base-200`)%>%
    filter(planning_year==2050,
           model%in%c('SWITCH', 'GenX'))%>%
    st_sf()
  
  ggplot(tempdat) +
    geom_sf(aes(geometry = geometry, fill = dif_mw)) +
    geom_sf(data = tempdat_transmission, aes(geometry = geometry, color = dif_mw), linewidth=1.5) +
    scale_fill_gradientn(colours = pal, name = "Generation Capacity \n Dif (MW)") + 
    scale_color_gradientn(colours = pal2, name = "Transmission Capacity \n Dif (MW)") +
    ggtitle(paste0('Differences in Generation and Transmission Capacity Relative to Unconstrained: \n', formatted_case_id)) +
    facet_grid(rows = vars(tech_type), cols = vars(model)) +
    theme_bw() +
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/capacity_relative_with_transmission_', case_id, '.png'),
         device='png',
         width=10,
         height=8)
  
  #can't figure out how to set easy x-y limits with this wonky crs
  tempdat = st_transform(tempdat, crs='WGS84')
  tempdat_transmission = st_transform(tempdat_transmission, crs='WGS84')
  
  #keep scales fixed
  min_gendif = min(tempdat$dif_mw)
  max_gendif = max(tempdat$dif_mw)
  
  min_transdif = min(tempdat_transmission$dif_mw)
  max_transdif = 0
  
  #ERCOT-ish region
  x_min = -106
  x_max = -90 
  y_min = 26  
  y_max = 40  
  
  box = st_sfc(st_polygon(list(rbind(c(x_min, y_min), 
                                     c(x_max, y_min), 
                                     c(x_max, y_max), 
                                     c(x_min, y_max), 
                                     c(x_min, y_min)))),
               crs='WGS84')
  
  
  # Filter the regions based on the x and y limits
  tempdat_region = st_intersection(tempdat, box)
  tempdat_transmission_region = st_intersection(tempdat_transmission, box)
    
  ggplot(tempdat_region) +
    geom_sf(aes(geometry = geometry, fill = dif_mw)) +
    geom_sf(data = tempdat_transmission_region, aes(geometry = geometry, color = dif_mw), linewidth=1.5) +
    scale_fill_gradientn(colours = pal, name = "Generation Capacity \n Dif (MW)") + 
    scale_color_gradientn(colours = pal2, name = "Transmission Capacity \n Dif (MW)") +
    ggtitle(paste0('Differences in Generation and Transmission Capacity Relative to Unconstrained: \n', formatted_case_id)) +
    geom_sf_text(aes(label = zone), 
                 size = 3,    
                 nudge_y = 0.1)+
    facet_grid(rows = vars(tech_type), cols = vars(model)) +
    theme_bw() +
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/capacity_relative_with_transmission_ERCOT_', case_id, '.png'),
         device='png',
         width=10,
         height=8)

  #NE-ish region
  x_min = -86
  x_max = -75 
  y_min = 35  
  y_max = 45  
  
  box = st_sfc(st_polygon(list(rbind(c(x_min, y_min), 
                                     c(x_max, y_min), 
                                     c(x_max, y_max), 
                                     c(x_min, y_max), 
                                     c(x_min, y_min)))),
               crs='WGS84')
  
  
  # Filter the regions based on the x and y limits
  tempdat_region = st_intersection(tempdat, box)
  tempdat_transmission_region = st_intersection(tempdat_transmission, box)
  
  ggplot(tempdat_region) +
    geom_sf(aes(geometry = geometry, fill = dif_mw)) +
    geom_sf(data = tempdat_transmission_region, aes(geometry = geometry, color = dif_mw), linewidth=1.5) +
    scale_fill_gradientn(colours = pal, name = "Generation Capacity \n Dif (MW)") + 
    scale_color_gradientn(colours = pal2, name = "Transmission Capacity \n Dif (MW)") +
    ggtitle(paste0('Differences in Generation and Transmission Capacity Relative to Unconstrained: \n', formatted_case_id)) +
    geom_sf_text(aes(label = zone), 
                 size = 3,    
                 nudge_y = 0.7,
                 nudge_x = 0.2)+
    facet_grid(rows = vars(tech_type), cols = vars(model)) +
    theme_bw() +
    theme(
      axis.text.x = element_blank(),
      axis.text.y = element_blank(),
      axis.ticks.x = element_blank(),
      axis.ticks.y = element_blank()
    )
  
  ggsave(filename = paste0('MIP_AirPollution/Figures/MIP_Paper/capacity_relative_with_transmission_NORTHEAST_', case_id, '.png'),
         device='png',
         width=10,
         height=8)
  
}
