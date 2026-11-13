import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.processing.normalize import load_all
from src.analysis.disagreement import build_grid_summary, compute_disagreement
from src.analysis.calibration import extract_paired_samples, run_all_calibrations

combined = load_all()
grid = build_grid_summary(combined)
disagree = compute_disagreement(grid)
pairs = extract_paired_samples(disagree)

# Double precision
res_orig = run_all_calibrations(pairs)

print("Pairs year breakdown:")
print(pairs["year"].value_counts())

# Check metrics on train and val
for split_name in ["train", "val"]:
    print(f"\n=== {split_name.upper()} METRICS (float64) ===")
    for k in ['identity', 'global', 'context']:
        m_obj = getattr(res_orig[k], f"{split_name}_metrics")
        val = m_obj.spearman_r if m_obj else float('nan')
        print(f"Model {k.capitalize()}: {split_name} Spearman = {val:.10f}")
    
    m_id = getattr(res_orig['identity'], f"{split_name}_metrics")
    m_gl = getattr(res_orig['global'], f"{split_name}_metrics")
    if m_id and m_gl:
        delta = abs(m_id.spearman_r - m_gl.spearman_r)
        print(f"Identity vs Global delta ({split_name}): {delta:.10e}")

# Integer cents (exact cents: 100 * round)
pairs_cents = pairs.copy()
pairs_cents['frp_viirs'] = (pairs_cents['frp_viirs'] * 100).round()
pairs_cents['frp_modis'] = (pairs_cents['frp_modis'] * 100).round()
res_cents = run_all_calibrations(pairs_cents)

for split_name in ["train", "val"]:
    print(f"\n=== {split_name.upper()} METRICS (integer cents) ===")
    for k in ['identity', 'global', 'context']:
        m_obj = getattr(res_cents[k], f"{split_name}_metrics")
        val = m_obj.spearman_r if m_obj else float('nan')
        print(f"Model {k.capitalize()}: {split_name} Spearman = {val:.10f}")
    
    m_id = getattr(res_cents['identity'], f"{split_name}_metrics")
    m_gl = getattr(res_cents['global'], f"{split_name}_metrics")
    if m_id and m_gl:
        delta = abs(m_id.spearman_r - m_gl.spearman_r)
        print(f"Identity vs Global delta ({split_name}): {delta:.10e}")






