import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from src.processing.normalize import load_all
from src.analysis.disagreement import build_grid_summary, compute_disagreement, _add_grid_id
from src.analysis.calibration import extract_paired_samples

# Load all data
combined = load_all()

# FILTER STRICT TO NOV 1-10 ONLY (Exclude 05-31 and 11-30 probe files)
strict_mask = (
    (combined["acq_date"].str.slice(5, 10).between("11-01", "11-10")) &
    (combined["source_file"].str.contains(r"2022-11-(0[1-9]|10)|2023-11-(0[1-9]|10)", regex=True))
)
combined_strict = combined[strict_mask].copy().reset_index(drop=True)

print(f"Strict records: MODIS={len(combined_strict[combined_strict['sensor']=='MODIS'])}, VIIRS={len(combined_strict[combined_strict['sensor']=='VIIRS'])}")
print(f"Strict dates: {sorted(combined_strict['acq_date'].unique())}")

grid_strict = build_grid_summary(combined_strict)
disagree_strict = compute_disagreement(grid_strict)
pairs_strict = extract_paired_samples(disagree_strict)

train_strict = pairs_strict[pairs_strict["year"] == 2022].copy().reset_index(drop=True)
val_strict = pairs_strict[pairs_strict["year"] == 2023].copy().reset_index(drop=True)

print(f"\nStrict Co-Active Pairs Total: {len(pairs_strict)}")
print(f"Strict 2022 Training Pairs: {len(train_strict)}")
print(f"Strict 2023 Evaluation Pairs: {len(val_strict)}")

# Now compute timing for all 2,554 co-active pairs
combined_grid = _add_grid_id(combined_strict)
co_keys = set(zip(pairs_strict["grid_id"], pairs_strict["acq_date"], pairs_strict["daynight"]))

timing_records = []
grouped = combined_grid.groupby(["grid_id", "acq_date", "daynight"])
for (gid, dt_str, dn), group in grouped:
    if (gid, dt_str, dn) in co_keys:
        m_pts = group[group["sensor"] == "MODIS"]
        v_pts = group[group["sensor"] == "VIIRS"]
        if not m_pts.empty and not v_pts.empty:
            m_sec = m_pts["acq_datetime"].apply(lambda dt: dt.timestamp()).values
            v_sec = v_pts["acq_datetime"].apply(lambda dt: dt.timestamp()).values
            
            # Centroid delta-t
            dt_centroid_min = abs(np.mean(m_sec) - np.mean(v_sec)) / 60.0
            # Min pairwise delta-t
            diffs = [abs(ms - vs) / 60.0 for ms in m_sec for vs in v_sec]
            dt_min_min = min(diffs)
            
            # Distinct pass times
            m_times = sorted(m_pts["acq_time"].unique())
            v_times = sorted(v_pts["acq_time"].unique())
            
            timing_records.append({
                "grid_id": gid,
                "acq_date": dt_str,
                "daynight": dn,
                "dt_centroid_min": dt_centroid_min,
                "dt_min_min": dt_min_min,
                "m_times": str(m_times),
                "v_times": str(v_times),
                "year": int(dt_str[:4]),
            })

df_time = pd.DataFrame(timing_records)
pairs_timed = pd.merge(pairs_strict, df_time, on=["grid_id", "acq_date", "daynight", "year"])
print(f"Timing calculated for {len(pairs_timed)} pairs.")

# CHECK ISSUE 2: Print distribution of dt_min_min across 2022 and 2023
print("\n=== DETAILED TIMING VALUE COUNTS (0 to 20 minutes) ===")
print("2022 dt_min_min distribution <= 20 min:")
t22 = pairs_timed[pairs_timed["year"] == 2022]["dt_min_min"]
print(pd.cut(t22, bins=[-0.1, 1, 3, 5, 10, 15, 20, 30, 200]).value_counts().sort_index())

print("\n2023 dt_min_min distribution <= 20 min:")
t23 = pairs_timed[pairs_timed["year"] == 2023]["dt_min_min"]
print(pd.cut(t23, bins=[-0.1, 1, 3, 5, 10, 15, 20, 30, 200]).value_counts().sort_index())

print("\nExact values of dt_min_min <= 20 min in 2023:")
print(pairs_timed[(pairs_timed["year"] == 2023) & (pairs_timed["dt_min_min"] <= 20)][["acq_date", "daynight", "m_times", "v_times", "dt_min_min"]].drop_duplicates())
