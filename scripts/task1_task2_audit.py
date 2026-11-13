import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GroupKFold

from src.processing.normalize import load_all
from src.analysis.disagreement import build_grid_summary, compute_disagreement, _add_grid_id
from src.analysis.calibration import extract_paired_samples, model_global, model_context

combined = load_all()
grid = build_grid_summary(combined)
disagree = compute_disagreement(grid)
pairs = extract_paired_samples(disagree)

print("=================================================================")
print("TASK 1: TRAINING-PERIOD INCONSISTENCY & PROVENANCE TRACE")
print("=================================================================")
print("\n--- All Raw CSV Files Loaded by load_all() ---")
p_mod = Path("data/raw/modis")
p_vii = Path("data/raw/viirs")
for p, name in [(p_mod, "MODIS"), (p_vii, "VIIRS")]:
    print(f"\n{name} Files ({len(list(p.glob('*.csv')))} files):")
    for f in sorted(p.glob("*.csv")):
        df_f = pd.read_csv(f)
        dates = df_f["acq_date"].unique() if "acq_date" in df_f.columns else []
        print(f"  {f.name:32s} | rows: {len(df_f):5d} | dates: {dates}")

print("\n--- 2022 Training Pairs Date Distribution ---")
trn_all = pairs[pairs["year"] == 2022].copy().reset_index(drop=True)
print(trn_all["acq_date"].value_counts().sort_index())
print(f"Total 2022 pairs: {len(trn_all)}")

print("\n--- 2023 Validation Pairs Date Distribution ---")
val_all = pairs[pairs["year"] == 2023].copy().reset_index(drop=True)
print(val_all["acq_date"].value_counts().sort_index())
print(f"Total 2023 pairs: {len(val_all)}")

# Compare Option A (Strict Nov 1-10) vs Option B (All Loaded Data)
trn_strict = trn_all[trn_all["acq_date"].between("2022-11-01", "2022-11-10")].copy().reset_index(drop=True)
val_strict = val_all[val_all["acq_date"].between("2023-11-01", "2023-11-10")].copy().reset_index(drop=True)

def eval_pipeline(train_df, eval_df, label):
    def _feat(df):
        f = df["frp_viirs"].values.reshape(-1, 1)
        c = df["count_viirs"].values.reshape(-1, 1) if "count_viirs" in df.columns else np.ones_like(f)
        n = (df["daynight"].values == "N").astype(float).reshape(-1, 1)
        return np.hstack([f, c, n])
    
    y_trn = train_df["frp_modis"].values
    x_trn_v = train_df["frp_viirs"].values
    y_eval = eval_df["frp_modis"].values
    x_eval_v = eval_df["frp_viirs"].values
    
    # Model A: Identity
    mae_a = mean_absolute_error(y_eval, x_eval_v)
    bias_a = np.mean(x_eval_v - y_eval) / np.mean(y_eval) * 100
    
    # Model B: Global RMA
    r = float(pd.Series(x_trn_v).corr(pd.Series(y_trn)))
    slope_b = (np.std(y_trn) / np.std(x_trn_v)) * np.sign(r)
    inter_b = np.mean(y_trn) - slope_b * np.mean(x_trn_v)
    pred_b = slope_b * x_eval_v + inter_b
    mae_b = mean_absolute_error(y_eval, pred_b)
    bias_b = np.mean(pred_b - y_eval) / np.mean(y_eval) * 100
    
    # Model C: Context OLS
    lr = LinearRegression().fit(_feat(train_df), y_trn)
    pred_c = lr.predict(_feat(eval_df))
    mae_c = mean_absolute_error(y_eval, pred_c)
    bias_c = np.mean(pred_c - y_eval) / np.mean(y_eval) * 100
    
    # 5-fold Date Grouped CV on train_df
    gkf = GroupKFold(n_splits=5)
    oof_t, oof_p, fold_maes = [], [], []
    for f, (t_idx, v_idx) in enumerate(gkf.split(train_df, groups=train_df["acq_date"]), 1):
        f_trn, f_val = train_df.iloc[t_idx], train_df.iloc[v_idx]
        m = LinearRegression().fit(_feat(f_trn), f_trn["frp_modis"].values)
        p = m.predict(_feat(f_val))
        fold_maes.append(mean_absolute_error(f_val["frp_modis"].values, p))
        oof_t.extend(f_val["frp_modis"].values)
        oof_p.extend(p)
        
    pooled_oof_mae = mean_absolute_error(oof_t, oof_p)
    mean_fold_mae = np.mean(fold_maes)
    
    print(f"\n--- {label} ---")
    print(f"Train Pairs: {len(train_df)} | Eval Pairs: {len(eval_df)}")
    print(f"Model B Slope: {slope_b:.5f} | Intercept: {inter_b:.5f} MW")
    print(f"Model A (Identity):    Val MAE = {mae_a:.4f} MW | Bias = {bias_a:+.2f}%")
    print(f"Model B (Global RMA):  Val MAE = {mae_b:.4f} MW | Bias = {bias_b:+.2f}%")
    print(f"Model C (Context OLS): Val MAE = {mae_c:.4f} MW | Bias = {bias_c:+.2f}%")
    print(f"Pooled OOF MAE (CV):   {pooled_oof_mae:.4f} MW | Unweighted Fold Mean: {mean_fold_mae:.4f} MW")

eval_pipeline(trn_all, val_all, "Option B: All Loaded CSV Files (1,314 train pairs, 1,246 val pairs)")
eval_pipeline(trn_strict, val_strict, "Option A: Strict Nov 1-10 Window (1,312 train pairs, 1,242 val pairs)")

print("\n=================================================================")
print("TASK 2: ACQUISITION-TIME SENSITIVITY EXPERIMENT")
print("=================================================================")
combined_grid = _add_grid_id(combined)

# For every co-active cell in pairs, compute minimum pairwise delta-t and centroid delta-t
timing_records = []
co_keys = set(zip(pairs["grid_id"], pairs["acq_date"], pairs["daynight"]))

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
            
            # Pass counts (unique acq_time strings)
            m_passes = m_pts["acq_time"].nunique()
            v_passes = v_pts["acq_time"].nunique()
            
            timing_records.append({
                "grid_id": gid,
                "acq_date": dt_str,
                "daynight": dn,
                "dt_centroid_min": dt_centroid_min,
                "dt_min_min": dt_min_min,
                "m_passes": m_passes,
                "v_passes": v_passes,
                "year": int(dt_str[:4]),
            })

df_time = pd.DataFrame(timing_records)
pairs_timed = pd.merge(pairs, df_time, on=["grid_id", "acq_date", "daynight", "year"])
print(f"Successfully matched timing to {len(pairs_timed)} co-active pairs.")

# Categorize into timing bins based on minimum pairwise delta-t
bins = [
    ("<= 5 min", pairs_timed["dt_min_min"] <= 5.0),
    ("<= 15 min", pairs_timed["dt_min_min"] <= 15.0),
    ("<= 30 min", pairs_timed["dt_min_min"] <= 30.0),
    ("> 30 min", pairs_timed["dt_min_min"] > 30.0),
]

print("\n--- Calibration Sensitivity Across Temporal Separation Bins (Val Split: 2023) ---")
val_timed = pairs_timed[pairs_timed["year"] == 2023].copy()
trn_timed = pairs_timed[pairs_timed["year"] == 2022].copy()

# Fit Model C on full 2022 train
def _feat(df):
    f = df["frp_viirs"].values.reshape(-1, 1)
    c = df["count_viirs"].values.reshape(-1, 1) if "count_viirs" in df.columns else np.ones_like(f)
    n = (df["daynight"].values == "N").astype(float).reshape(-1, 1)
    return np.hstack([f, c, n])

lr_full = LinearRegression().fit(_feat(trn_timed), trn_timed["frp_modis"].values)

# Model B on full 2022 train
r_trn = float(pd.Series(trn_timed["frp_viirs"]).corr(pd.Series(trn_timed["frp_modis"])))
slope_b = (np.std(trn_timed["frp_modis"]) / np.std(trn_timed["frp_viirs"])) * np.sign(r_trn)
inter_b = np.mean(trn_timed["frp_modis"]) - slope_b * np.mean(trn_timed["frp_viirs"])

print(f"{'Bin':<12s} | {'Total n':<7s} | {'Val n':<6s} | {'Mod A MAE':<10s} | {'Mod B MAE':<10s} | {'Mod C MAE':<10s} | {'Mod C Bias %':<12s} | {'Improvement vs A':<16s}")
print("-" * 95)

for b_name, mask_cond in bins:
    sub_val = pairs_timed[mask_cond & (pairs_timed["year"] == 2023)].copy()
    sub_total = pairs_timed[mask_cond]
    n_tot = len(sub_total)
    n_val = len(sub_val)
    
    if n_val == 0:
        print(f"{b_name:<12s} | {n_tot:<7d} | {n_val:<6d} | Insufficient data")
        continue
        
    y_v = sub_val["frp_modis"].values
    x_v = sub_val["frp_viirs"].values
    
    mae_a = mean_absolute_error(y_v, x_v)
    
    pred_b = slope_b * x_v + inter_b
    mae_b = mean_absolute_error(y_v, pred_b)
    
    pred_c = lr_full.predict(_feat(sub_val))
    mae_c = mean_absolute_error(y_v, pred_c)
    bias_c = np.mean(pred_c - y_v) / np.mean(y_v) * 100
    
    imp = (mae_a - mae_c) / mae_a * 100
    print(f"{b_name:<12s} | {n_tot:<7d} | {n_val:<6d} | {mae_a:8.2f} MW | {mae_b:8.2f} MW | {mae_c:8.2f} MW | {bias_c:+10.2f}% | {imp:+14.2f}%")

print("\n--- Also Fit & Evaluate Within Specific Bin (Where n_trn >= 100) ---")
for b_name, mask_cond in bins:
    sub_trn = pairs_timed[mask_cond & (pairs_timed["year"] == 2022)].copy()
    sub_val = pairs_timed[mask_cond & (pairs_timed["year"] == 2023)].copy()
    
    if len(sub_trn) < 50 or len(sub_val) < 20:
        print(f"{b_name:<12s}: In-bin training skipped (n_trn={len(sub_trn)}, n_val={len(sub_val)} insufficient for reliable model fitting).")
        continue
        
    y_trn = sub_trn["frp_modis"].values
    y_val = sub_val["frp_modis"].values
    
    lr_bin = LinearRegression().fit(_feat(sub_trn), y_trn)
    pred_bin = lr_bin.predict(_feat(sub_val))
    mae_bin = mean_absolute_error(y_val, pred_bin)
    bias_bin = np.mean(pred_bin - y_val) / np.mean(y_val) * 100
    mae_a = mean_absolute_error(y_val, sub_val["frp_viirs"].values)
    imp = (mae_a - mae_bin) / mae_a * 100
    print(f"{b_name:<12s}: In-bin model fitted (n_trn={len(sub_trn)}, n_val={len(sub_val)}) -> MAE={mae_bin:.2f} MW (Bias={bias_bin:+.2f}%, Imp vs A: {imp:+.2f}%)")
