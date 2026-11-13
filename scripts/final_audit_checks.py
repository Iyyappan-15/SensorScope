import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

from src.processing.normalize import load_all
from src.analysis.disagreement import build_grid_summary, compute_disagreement
from src.analysis.calibration import extract_paired_samples, model_global, model_context, _chronological_split

print("=================================================================")
print("CHECK 1: SENSITIVITY SAMPLE REPRODUCIBILITY")
print("=================================================================")
combined = load_all()
sample_df = combined.sample(min(5000, len(combined)), random_state=42)

print(f"Total rows in sample: {len(sample_df)}")
print(f"MODIS rows: {len(sample_df[sample_df['sensor'] == 'MODIS'])} ({len(sample_df[sample_df['sensor'] == 'MODIS'])/len(sample_df)*100:.2f}%)")
print(f"VIIRS rows: {len(sample_df[sample_df['sensor'] == 'VIIRS'])} ({len(sample_df[sample_df['sensor'] == 'VIIRS'])/len(sample_df)*100:.2f}%)")
print(f"Date range: {sample_df['acq_date'].min()} to {sample_df['acq_date'].max()} ({sample_df['acq_date'].nunique()} unique dates)")
print(f"Latitude range: {sample_df['latitude'].min():.4f} to {sample_df['latitude'].max():.4f}")
print(f"Longitude range: {sample_df['longitude'].min():.4f} to {sample_df['longitude'].max():.4f}")
print("Random seed: 42 on load_all() DataFrame sorted by acq_datetime")
print("Reused across all 9 parameter combinations: True (same sample_df passed to associate_sensors)")

print("\n=================================================================")
print("CHECK 2: FIVE-FOLD DATE-GROUPED CROSS-VALIDATION")
print("=================================================================")
grid = build_grid_summary(combined)
disagree = compute_disagreement(grid)
pairs = extract_paired_samples(disagree)

train_pairs = pairs[pairs["year"] == 2022].copy().reset_index(drop=True)
print(f"Total training pairs (2022): {len(train_pairs)}")

gkf = GroupKFold(n_splits=5)
groups = train_pairs["acq_date"]

fold_maes = []
oof_true = []
oof_preds = []

def _build_features(df: pd.DataFrame) -> np.ndarray:
    frp = df["frp_viirs"].values.reshape(-1, 1)
    count = df["count_viirs"].values.reshape(-1, 1) if "count_viirs" in df.columns else np.ones_like(frp)
    is_night = (df["daynight"].values == "N").astype(float).reshape(-1, 1)
    return np.hstack([frp, count, is_night])

for fold, (trn_idx, val_idx) in enumerate(gkf.split(train_pairs, groups=groups), 1):
    f_trn = train_pairs.iloc[trn_idx]
    f_val = train_pairs.iloc[val_idx]
    
    val_dates = sorted(f_val["acq_date"].unique())
    trn_dates = sorted(f_trn["acq_date"].unique())
    
    X_trn = _build_features(f_trn)
    y_trn = f_trn["frp_modis"].values
    X_val = _build_features(f_val)
    y_val = f_val["frp_modis"].values
    
    lr = LinearRegression()
    lr.fit(X_trn, y_trn)
    preds = lr.predict(X_val)
    
    mae = mean_absolute_error(y_val, preds)
    fold_maes.append(mae)
    oof_true.extend(y_val)
    oof_preds.extend(preds)
    
    print(f"Fold {fold}: Val Dates={val_dates} | n_val={len(f_val)} | n_trn={len(f_trn)} | Fold MAE={mae:.4f} MW")

unweighted_mean_mae = np.mean(fold_maes)
pooled_oof_mae = mean_absolute_error(oof_true, oof_preds)
print(f"\nUnweighted Mean of Fold MAEs: {unweighted_mean_mae:.4f} MW")
print(f"Pooled Out-Of-Fold MAE (concatenated predictions): {pooled_oof_mae:.4f} MW")

print("\n=================================================================")
print("CHECK 4: MODEL B RMA COEFFICIENT RECONCILIATION")
print("=================================================================")
# Let's inspect Model B implementation
res_b = model_global(pairs)
print(f"Model B slope on train split (2022): {res_b.slope:.5f}")
print(f"Model B intercept on train split (2022): {res_b.intercept:.5f}")

# What if slope is computed on full pairs (2022 + 2023)?
x_all = pairs["frp_viirs"].values.astype(float)
y_all = pairs["frp_modis"].values.astype(float)
r_all = pd.Series(x_all).corr(pd.Series(y_all))
slope_all = (np.std(y_all, ddof=1) / np.std(x_all, ddof=1)) * np.sign(r_all)
intercept_all = np.mean(y_all) - slope_all * np.mean(x_all)
print(f"Full pairs (2022+2023) RMA slope: {slope_all:.5f}, intercept: {intercept_all:.5f}")

# What if slope is computed on train_pairs (2022)?
x_trn = train_pairs["frp_viirs"].values.astype(float)
y_trn = train_pairs["frp_modis"].values.astype(float)
r_trn = pd.Series(x_trn).corr(pd.Series(y_trn))
slope_trn = (np.std(y_trn, ddof=1) / np.std(x_trn, ddof=1)) * np.sign(r_trn)
intercept_trn = np.mean(y_trn) - slope_trn * np.mean(x_trn)
print(f"Train split (2022) RMA slope: {slope_trn:.5f}, intercept: {intercept_trn:.5f}")

val_pairs = pairs[pairs["year"] == 2023].copy()
x_val = val_pairs["frp_viirs"].values.astype(float)
y_val = val_pairs["frp_modis"].values.astype(float)
r_val = pd.Series(x_val).corr(pd.Series(y_val))
slope_val = (np.std(y_val, ddof=1) / np.std(x_val, ddof=1)) * np.sign(r_val)
intercept_val = np.mean(y_val) - slope_val * np.mean(x_val)
print(f"Val split (2023) RMA slope: {slope_val:.5f}, intercept: {intercept_val:.5f}")


print("\n=================================================================")
print("CHECK 5: CALIBRATION OBSERVATION TIMING (2,560 CO-ACTIVE CELLS)")
print("=================================================================")
# In each cell-date-daynight, find the MODIS detections and VIIRS detections
# and compute acquisition time difference.
# First add grid_id to combined
from src.analysis.disagreement import _add_grid_id

combined_grid = _add_grid_id(combined)
# Filter to the 2,560 co-active pairs (keys in pairs)
co_active_keys = set(zip(pairs["grid_id"], pairs["acq_date"], pairs["daynight"]))
print(f"Identified {len(co_active_keys)} co-active keys.")

# Group combined_grid by (grid_id, acq_date, daynight)
dt_mean_list = []
dt_min_list = []

grouped = combined_grid.groupby(["grid_id", "acq_date", "daynight"])
for (gid, dt_str, dn), group in grouped:
    if (gid, dt_str, dn) in co_active_keys:
        m_pts = group[group["sensor"] == "MODIS"]
        v_pts = group[group["sensor"] == "VIIRS"]
        if not m_pts.empty and not v_pts.empty:
            m_times = m_pts["acq_datetime"].values
            v_times = v_pts["acq_datetime"].values
            
            # Mean times using unix timestamp in seconds
            m_sec = m_pts["acq_datetime"].apply(lambda dt: dt.timestamp()).values
            v_sec = v_pts["acq_datetime"].apply(lambda dt: dt.timestamp()).values
            
            dt_mean_min = abs(np.mean(m_sec) - np.mean(v_sec)) / 60.0
            dt_mean_list.append(dt_mean_min)
            
            # Min pairwise diff
            diffs = [abs(ms - vs) / 60.0 for ms in m_sec for vs in v_sec]
            dt_min_list.append(min(diffs))



dt_mean_arr = np.array(dt_mean_list)
dt_min_arr = np.array(dt_min_list)

print(f"Total co-active cells with timing matched: {len(dt_mean_arr)}")

for label, arr in [("Method 1: Cell-Centroid Mean Acquisition Time Delta", dt_mean_arr),
                   ("Method 2: Minimum Pairwise Detection Time Delta", dt_min_arr)]:
    print(f"\n--- {label} ---")
    print(f"Median: {np.median(arr):.2f} min")
    print(f"Mean:   {np.mean(arr):.2f} min")
    print(f"Max:    {np.max(arr):.2f} min")
    print(f"5th percentile:  {np.percentile(arr, 5):.2f} min")
    print(f"95th percentile: {np.percentile(arr, 95):.2f} min")
    
    n_5 = np.sum(arr <= 5.0)
    n_15 = np.sum(arr <= 15.0)
    n_30 = np.sum(arr <= 30.0)
    n_60 = np.sum(arr <= 60.0)
    print(f"<= 5 min:  {n_5:4d} / {len(arr)} ({n_5/len(arr)*100:.2f}%)")
    print(f"<= 15 min: {n_15:4d} / {len(arr)} ({n_15/len(arr)*100:.2f}%)")
    print(f"<= 30 min: {n_30:4d} / {len(arr)} ({n_30/len(arr)*100:.2f}%)")
    print(f"<= 60 min: {n_60:4d} / {len(arr)} ({n_60/len(arr)*100:.2f}%)")
    print(f"> 60 min:  {len(arr) - n_60:4d} / {len(arr)} ({(len(arr)-n_60)/len(arr)*100:.2f}%)")
