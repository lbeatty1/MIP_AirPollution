import time, random

import pandas as pd

# sleep for a random interval to reduce the chance of conflicts
# if run multiple times in parallel
time.sleep(random.random())

for case in ["base", "current_policies"]:
    with open(f"out/{case}/total_cost.txt") as f:
        cost = float(f.read().strip())
    df = pd.read_csv(f"in/foresight/{case}/financials.csv", na_values=["."])
    for adder in [50, 100, 200]:
        df["system_cost_limit"] = cost + adder * 1e9
        out = f"in/foresight/{case}/financials.{case}_{adder}.csv"
        print("creating", out)
        df.to_csv(out, na_rep=["."])
