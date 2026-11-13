"""
scripts/sensitivity_matrix.py — 9-cell candidate association sensitivity scan.

Evaluates 3 temporal windows (5, 15, 30 minutes) x 3 spatial tolerances (5, 11, 20 km)
on real NASA FIRMS data, recording complete raw counts, denominators, and rates:
  - Total records evaluated (denominator)
  - Raw matched counts (1 candidate match)
  - Raw ambiguous counts (>1 candidate match)
  - Raw unmatched counts (0 candidate matches)
  - Resulting match and ambiguity rates (%)
  - Empirical delta-t distribution (mean, median in minutes)
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from processing.normalize import load_all
from processing.association import associate_sensors
from config import RAW_MODIS_DIR, RAW_VIIRS_DIR


def run_sensitivity_scan():
    print("=== LOADING REAL DATA FOR SENSITIVITY SCAN ===")
    combined = load_all(RAW_MODIS_DIR, RAW_VIIRS_DIR)
    
    # 5,000 representative sample
    sample_df = combined.sample(min(5000, len(combined)), random_state=42)
    
    time_windows = [5, 15, 30]       # minutes
    spatial_tolerances = [5.0, 11.0, 20.0]  # km
    
    results = []
    
    print("\nRunning 9-cell sensitivity scan with full counts & denominators...")
    for dt in time_windows:
        for dr in spatial_tolerances:
            assoc = associate_sensors(sample_df, time_window_minutes=dt, spatial_tolerance_km=dr)
            
            modis_sub = assoc[assoc["sensor"] == "MODIS"]
            viirs_sub = assoc[assoc["sensor"] == "VIIRS"]
            
            n_m = len(modis_sub)
            n_v = len(viirs_sub)
            
            m_matched = int((modis_sub["match_status"] == "matched").sum())
            m_ambig   = int((modis_sub["match_status"] == "ambiguous").sum())
            m_unmatch = int((modis_sub["match_status"] == "unmatched").sum())
            
            v_matched = int((viirs_sub["match_status"] == "matched").sum())
            v_ambig   = int((viirs_sub["match_status"] == "ambiguous").sum())
            v_unmatch = int((viirs_sub["match_status"] == "unmatched").sum())
            
            dt_matched = modis_sub.loc[modis_sub["match_count"] > 0, "match_min_dt_min"].dropna()
            mean_dt = dt_matched.mean() if not dt_matched.empty else np.nan
            median_dt = dt_matched.median() if not dt_matched.empty else np.nan
            
            results.append({
                "time_window_min": dt,
                "spatial_tol_km": dr,
                # MODIS statistics
                "modis_denom": n_m,
                "modis_matched_count": m_matched,
                "modis_ambig_count": m_ambig,
                "modis_unmatch_count": m_unmatch,
                "modis_match_pct": round((m_matched + m_ambig) / n_m * 100, 1) if n_m > 0 else 0,
                "modis_ambig_pct": round(m_ambig / n_m * 100, 1) if n_m > 0 else 0,
                # VIIRS statistics
                "viirs_denom": n_v,
                "viirs_matched_count": v_matched,
                "viirs_ambig_count": v_ambig,
                "viirs_unmatch_count": v_unmatch,
                "viirs_match_pct": round((v_matched + v_ambig) / n_v * 100, 1) if n_v > 0 else 0,
                "viirs_ambig_pct": round(v_ambig / n_v * 100, 1) if n_v > 0 else 0,
                # Observed temporal offsets
                "mean_observed_dt_min": round(mean_dt, 2) if not np.isnan(mean_dt) else "—",
                "median_observed_dt_min": round(median_dt, 2) if not np.isnan(median_dt) else "—",
            })
            print(f"  dt={dt:2d}m, dr={dr:4.1f}km | MODIS: {m_matched+m_ambig}/{n_m} ({results[-1]['modis_match_pct']}%) [ambig: {m_ambig}] | VIIRS: {v_matched+v_ambig}/{n_v} ({results[-1]['viirs_match_pct']}%) [ambig: {v_ambig}] | dt: {results[-1]['mean_observed_dt_min']}m")
            
    df_res = pd.DataFrame(results)
    out_csv = ROOT / "docs" / "sensitivity_scan_results.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\nSaved updated sensitivity scan with full counts to {out_csv.name}")
    return df_res


if __name__ == "__main__":
    run_sensitivity_scan()
