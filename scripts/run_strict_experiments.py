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

# Load strict dataset
combined = load_all()
strict_mask = (
    (combined["acq_date"].str.slice(5, 10).between("11-01", "11-10")) &
    (combined["source_file"].str.contains(r"2022-11-(0[1-9]|10)|2023-11-(0[1-9]|10)", regex=True))
)
combined_strict = combined[strict_mask].copy().reset_index(drop=True)

grid_strict = build_grid_summary(combined_strict)
disagree_strict = compute_disagreement(grid_strict)
pairs_strict = extract_paired_samples(disagree_strict)

# Grid ID and timing computation
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
            
            dt_centroid_min = abs(np.mean(m_sec) - np.mean(v_sec)) / 60.0
            diffs = [abs(ms - vs) / 60.0 for ms in m_sec for vs in v_sec]
            dt_min_min = min(diffs)
            
            timing_records.append({
                "grid_id": gid,
                "acq_date": dt_str,
                "daynight": dn,
                "dt_centroid_min": dt_centroid_min,
                "dt_min_min": dt_min_min,
                "year": int(dt_str[:4]),
            })

df_time = pd.DataFrame(timing_records)
pairs_timed = pd.merge(pairs_strict, df_time, on=["grid_id", "acq_date", "daynight", "year"])

trn_strict = pairs_timed[pairs_timed["year"] == 2022].copy().reset_index(drop=True)
val_strict = pairs_timed[pairs_timed["year"] == 2023].copy().reset_index(drop=True)

print(f"Total Strict Pairs: {len(pairs_timed)} (2022 Train: {len(trn_strict)}, 2023 Eval: {len(val_strict)})")

# Define exclusive bins
def assign_bin(val):
    if val <= 5.0:
        return "0–5 min"
    elif val <= 15.0:
        return ">5–15 min"
    elif val <= 30.0:
        return ">15–30 min"
    else:
        return ">30 min"

pairs_timed["timing_bin"] = pairs_timed["dt_min_min"].apply(assign_bin)
trn_strict["timing_bin"] = trn_strict["dt_min_min"].apply(assign_bin)
val_strict["timing_bin"] = val_strict["dt_min_min"].apply(assign_bin)

print("\n=== EXCLUSIVE TIMING BIN MEMBERSHIP COUNTS ===")
counts_df = pd.DataFrame({
    "Total (2022+2023)": pairs_timed["timing_bin"].value_counts(),
    "Train (2022)": trn_strict["timing_bin"].value_counts(),
    "Eval (2023)": val_strict["timing_bin"].value_counts(),
}).reindex(["0–5 min", ">5–15 min", ">15–30 min", ">30 min"]).fillna(0).astype(int)

counts_df["Train %"] = (counts_df["Train (2022)"] / len(trn_strict) * 100).round(1)
counts_df["Eval %"] = (counts_df["Eval (2023)"] / len(val_strict) * 100).round(1)
print(counts_df)

# Global Model Training (on all 1,312 strict 2022 train pairs)
def _feat(df):
    f = df["frp_viirs"].values.reshape(-1, 1)
    c = df["count_viirs"].values.reshape(-1, 1) if "count_viirs" in df.columns else np.ones_like(f)
    n = (df["daynight"].values == "N").astype(float).reshape(-1, 1)
    return np.hstack([f, c, n])

lr_global = LinearRegression().fit(_feat(trn_strict), trn_strict["frp_modis"].values)
r_global = float(pd.Series(trn_strict["frp_viirs"]).corr(pd.Series(trn_strict["frp_modis"])))
slope_b_global = (np.std(trn_strict["frp_modis"]) / np.std(trn_strict["frp_viirs"])) * np.sign(r_global)
inter_b_global = np.mean(trn_strict["frp_modis"]) - slope_b_global * np.mean(trn_strict["frp_viirs"])

print("\n=== EXPERIMENT A: GLOBAL MODEL C EVALUATED ACROSS EXCLUSIVE TIMING BINS ===")
bin_order = ["0–5 min", ">5–15 min", ">15–30 min", ">30 min"]
exp_a_rows = []

for b in bin_order:
    sub_val = val_strict[val_strict["timing_bin"] == b].copy()
    n_v = len(sub_val)
    if n_v == 0:
        exp_a_rows.append({
            "Timing Interval": b, "Eval n": 0, "Identity MAE": "N/A (0 obs)",
            "Model B MAE": "N/A", "Model C MAE": "N/A", "Model C Bias %": "N/A",
            "Improvement vs Identity": "N/A (No 2023 passes)"
        })
        continue
    
    y_v = sub_val["frp_modis"].values
    x_v = sub_val["frp_viirs"].values
    
    mae_a = mean_absolute_error(y_v, x_v)
    pred_b = slope_b_global * x_v + inter_b_global
    mae_b = mean_absolute_error(y_v, pred_b)
    pred_c = lr_global.predict(_feat(sub_val))
    mae_c = mean_absolute_error(y_v, pred_c)
    bias_c = np.mean(pred_c - y_v) / np.mean(y_v) * 100
    imp = (mae_a - mae_c) / mae_a * 100
    
    exp_a_rows.append({
        "Timing Interval": b, "Eval n": n_v, "Identity MAE": f"{mae_a:.2f} MW",
        "Model B MAE": f"{mae_b:.2f} MW", "Model C MAE": f"{mae_c:.2f} MW",
        "Model C Bias %": f"{bias_c:+.2f}%", "Improvement vs Identity": f"{imp:+.2f}%"
    })

print(pd.DataFrame(exp_a_rows).to_string(index=False))

print("\n=== EXPERIMENT B: INDEPENDENT MODELS RETRAINED WITHIN TIMING BINS ===")
exp_b_rows = []

for b in bin_order:
    sub_trn = trn_strict[trn_strict["timing_bin"] == b].copy()
    sub_val = val_strict[val_strict["timing_bin"] == b].copy()
    n_t = len(sub_trn)
    n_v = len(sub_val)
    
    if n_t < 50 or n_v == 0:
        reason = "0 eval observations" if n_v == 0 else f"Insufficient train ({n_t} pairs)"
        exp_b_rows.append({
            "Timing Interval": b, "Train n": n_t, "Eval n": n_v,
            "In-Bin Model C MAE": "N/A", "In-Bin Bias %": "N/A",
            "Improvement vs Identity": "N/A", "Status / Caveat": f"Skipped: {reason}"
        })
        continue
    
    y_t = sub_trn["frp_modis"].values
    y_v = sub_val["frp_modis"].values
    x_v = sub_val["frp_viirs"].values
    
    lr_bin = LinearRegression().fit(_feat(sub_trn), y_t)
    pred_bin = lr_bin.predict(_feat(sub_val))
    
    mae_bin = mean_absolute_error(y_v, pred_bin)
    bias_bin = np.mean(pred_bin - y_v) / np.mean(y_v) * 100
    mae_a = mean_absolute_error(y_v, x_v)
    imp = (mae_a - mae_bin) / mae_a * 100
    
    exp_b_rows.append({
        "Timing Interval": b, "Train n": n_t, "Eval n": n_v,
        "In-Bin Model C MAE": f"{mae_bin:.2f} MW", "In-Bin Bias %": f"{bias_bin:+.2f}%",
        "Improvement vs Identity": f"{imp:+.2f}%",
        "Status / Caveat": "Trained & Evaluated in-bin"
    })

print(pd.DataFrame(exp_b_rows).to_string(index=False))

# Also calculate cumulative groups for complete reference
print("\n=== SUPPLEMENTARY: CUMULATIVE TIMING GROUPS (GLOBAL MODEL C) ===")
cum_bins = [
    ("<= 5 min", val_strict["dt_min_min"] <= 5.0, trn_strict["dt_min_min"] <= 5.0),
    ("<= 15 min", val_strict["dt_min_min"] <= 15.0, trn_strict["dt_min_min"] <= 15.0),
    ("<= 30 min", val_strict["dt_min_min"] <= 30.0, trn_strict["dt_min_min"] <= 30.0),
    ("> 30 min", val_strict["dt_min_min"] > 30.0, trn_strict["dt_min_min"] > 30.0),
]
cum_rows = []
for c_name, val_m, trn_m in cum_bins:
    sub_val = val_strict[val_m].copy()
    y_v = sub_val["frp_modis"].values
    x_v = sub_val["frp_viirs"].values
    mae_a = mean_absolute_error(y_v, x_v)
    pred_c = lr_global.predict(_feat(sub_val))
    mae_c = mean_absolute_error(y_v, pred_c)
    bias_c = np.mean(pred_c - y_v) / np.mean(y_v) * 100
    imp = (mae_a - mae_c) / mae_a * 100
    cum_rows.append({
        "Cumulative Window": c_name, "Train n": int(trn_m.sum()),
        "Eval n": len(sub_val), "Identity MAE": f"{mae_a:.2f} MW", "Model C MAE": f"{mae_c:.2f} MW",
        "Improvement": f"{imp:+.2f}%"
    })
print(pd.DataFrame(cum_rows).to_string(index=False))

