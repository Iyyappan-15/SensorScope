"""
scripts/sensitivity_matrix.py — 9-cell candidate association sensitivity scan.

Evaluates 3 temporal windows (5, 15, 30 minutes) x 3 spatial tolerances (5, 11, 20 km)
on real NASA FIRMS data, recording complete raw counts, denominators, and granular rates:
  - Denominator (total observations evaluated)
  - Unambiguous matches (count and % of all obs)
  - Ambiguous matches (count, % of all obs, and % of candidate-associated obs)
  - Total Candidate-Associated (count and % of all obs)
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
    
    print("\nRunning 9-cell sensitivity scan with full counts & ambiguity breakdowns...")
    for dt in time_windows:
        for dr in spatial_tolerances:
            assoc = associate_sensors(sample_df, time_window_minutes=dt, spatial_tolerance_km=dr)
            
            modis_sub = assoc[assoc["sensor"] == "MODIS"]
            viirs_sub = assoc[assoc["sensor"] == "VIIRS"]
            
            n_m = len(modis_sub)
            n_v = len(viirs_sub)
            
            m_unambig = int((modis_sub["match_status"] == "matched").sum())
            m_ambig   = int((modis_sub["match_status"] == "ambiguous").sum())
            m_unmatch = int((modis_sub["match_status"] == "unmatched").sum())
            m_assoc   = m_unambig + m_ambig
            
            v_unambig = int((viirs_sub["match_status"] == "matched").sum())
            v_ambig   = int((viirs_sub["match_status"] == "ambiguous").sum())
            v_unmatch = int((viirs_sub["match_status"] == "unmatched").sum())
            v_assoc   = v_unambig + v_ambig
            
            dt_matched = modis_sub.loc[modis_sub["match_count"] > 0, "match_min_dt_min"].dropna()
            mean_dt = dt_matched.mean() if not dt_matched.empty else np.nan
            median_dt = dt_matched.median() if not dt_matched.empty else np.nan
            
            # Ambiguity fractions among candidate-associated records
            m_ambig_of_assoc = (m_ambig / m_assoc * 100) if m_assoc > 0 else 0.0
            v_ambig_of_assoc = (v_ambig / v_assoc * 100) if v_assoc > 0 else 0.0
            
            results.append({
                "time_window_min": dt,
                "spatial_tol_km": dr,
                # MODIS statistics
                "modis_denom": n_m,
                "modis_unambig_n": m_unambig,
                "modis_ambig_n": m_ambig,
                "modis_unmatch_n": m_unmatch,
                "modis_unambig_pct": round(m_unambig / n_m * 100, 1),
                "modis_ambig_of_all_pct": round(m_ambig / n_m * 100, 1),
                "modis_candidate_assoc_pct": round(m_assoc / n_m * 100, 1),
                "modis_ambig_of_assoc_pct": round(m_ambig_of_assoc, 1),
                # VIIRS statistics
                "viirs_denom": n_v,
                "viirs_unambig_n": v_unambig,
                "viirs_ambig_n": v_ambig,
                "viirs_unmatch_n": v_unmatch,
                "viirs_unambig_pct": round(v_unambig / n_v * 100, 1),
                "viirs_ambig_of_all_pct": round(v_ambig / n_v * 100, 1),
                "viirs_candidate_assoc_pct": round(v_assoc / n_v * 100, 1),
                "viirs_ambig_of_assoc_pct": round(v_ambig_of_assoc, 1),
                # Observed temporal offsets
                "mean_observed_dt_min": round(mean_dt, 2) if not np.isnan(mean_dt) else "—",
                "median_observed_dt_min": round(median_dt, 2) if not np.isnan(median_dt) else "—",
            })
            print(f"  dt={dt:2d}m, dr={dr:4.1f}km | MODIS assoc: {m_assoc}/{n_m} ({results[-1]['modis_candidate_assoc_pct']}%) [ambig of assoc: {results[-1]['modis_ambig_of_assoc_pct']}%] | VIIRS assoc: {v_assoc}/{n_v} ({results[-1]['viirs_candidate_assoc_pct']}%) [ambig of assoc: {results[-1]['viirs_ambig_of_assoc_pct']}%] | mean dt: {results[-1]['mean_observed_dt_min']}m")
            
    df_res = pd.DataFrame(results)
    out_csv = ROOT / "docs" / "sensitivity_scan_results.csv"
    df_res.to_csv(out_csv, index=False)
    print(f"\nSaved updated sensitivity scan with granular rates to {out_csv.name}")
    return df_res


if __name__ == "__main__":
    run_sensitivity_scan()
