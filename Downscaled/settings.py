year_inputs = {
    'p1': 2027,
    'p2': 2030,
    'p3': 2035,
    'p4': 2040,
    'p5': 2045,
    'p6': 2050
}
print("year_inputs loaded")

scenario_dictionary = {
    'full-base-50' : 'base_52_week_50',
    'full-base-200' : 'base_52_week',
    'full-base-1000' : 'base_52_week_1000',
    'full-current-policies' : 'current_policies_52_week',
    'full-current-policies-commit' : 'current_policies_52_week_commit',
    'full-current-policies-retire' : 'current_policies_52_week_retire',
    'full-base-200-tx-0' : 'base_52_week_tx_0',
    'full-base-200-tx-15' : 'base_52_week_tx_15',
    'full-base-200-tx-50' : 'base_52_week_tx_50'
}
print('scenarios to run loaded')

eia_datapath = 'Data/'
epa_datapath = 'Data/'
print("path settings loaded")

ccs_heatrate_penalty =  6.36/7.16
print("ccspenalty settings loaded")

technology_map = {
    'naturalgas_hframe_cc_moderate' : 'Natural Gas CC',
    'naturalgas_fframe_ct' : 'Natural Gas CT',
    'naturalgas_hframe_cc_95_ccs' : 'Natural Gas CCS'
}
print("loaded technology dictionary")