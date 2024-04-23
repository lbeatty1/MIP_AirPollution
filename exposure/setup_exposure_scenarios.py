import pandas as pd

dfs = []
for y in [2030, 2040, 2050]:
    dfs.append(
        pd.read_csv(
            f"https://raw.githubusercontent.com/lbeatty1/MIP_AirPollution/main/marginal_gen_exposure_coefs_{y}.csv",
            index_col=0,
        )
    )
exposure = (
    pd.concat(dfs)
    .groupby(["Cluster", "year", "Race"], as_index=False)["Exposure"]
    .sum()
).query("Exposure != 0")
exposure.columns = [
    "GENERATION_PROJECT",
    "PERIOD",
    "EXPOSURE_GROUP",
    "group_exposure_coefficient",
]
for case in ["base", "current_policies"]:
    exposure.to_csv(
        f"in/foresight/{case}/group_exposure_coefficients.csv", na_rep=".", index=False
    )
    df = pd.read_csv(f"in/foresight/{case}/financials.csv", na_values=["."])
    df["system_cost_limit"] = 1000000000000000
    df.to_csv(f"in/foresight/{case}/financials.{case}_100.csv", na_rep=["."])
    df.to_csv(f"in/foresight/{case}/financials.{case}_200.csv", na_rep=["."])
