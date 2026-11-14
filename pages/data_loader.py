"""Shared data-loading logic for all pages — cached at session level."""

from __future__ import annotations
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import RAW_MODIS_DIR, RAW_VIIRS_DIR, SAMPLE_DIR
from processing.normalize import load_all_modis, load_all_viirs
from processing.association import associate_sensors
from analysis.disagreement import build_grid_summary, compute_disagreement
from analysis.calibration import extract_paired_samples, run_all_calibrations
from analysis.reliability import build_reliability_table


def _has_real_data() -> bool:
    return (
        any(RAW_MODIS_DIR.glob("*.csv")) and
        any(RAW_VIIRS_DIR.glob("*.csv"))
    )


@st.cache_data(show_spinner="Loading satellite data…")
def load_data() -> dict:
    """
    Load, normalize, associate, and analyse MODIS + VIIRS data.
    Falls back to synthetic sample data if no real data downloaded yet.
    """
    using_real = _has_real_data()

    if using_real:
        modis = load_all_modis(RAW_MODIS_DIR)
        viirs = load_all_viirs(RAW_VIIRS_DIR)
    else:
        # Use synthetic sample data
        modis = load_all_modis(SAMPLE_DIR)
        viirs = load_all_viirs(SAMPLE_DIR)

    combined = pd.concat([modis, viirs], ignore_index=True)
    combined = combined.sort_values("acq_datetime").reset_index(drop=True)

    # Association — skip on empty
    if not combined.empty and len(modis) > 0 and len(viirs) > 0:
        # Only associate a sample for performance (<= 20 k rows)
        sample_size = min(len(combined), 20_000)
        combined_sample = combined.sample(n=sample_size, random_state=42) if len(combined) > sample_size else combined
        combined_assoc = associate_sensors(combined_sample)
    else:
        combined_assoc = combined.copy()
        combined_assoc["match_status"] = "unmatched"
        combined_assoc["match_count"] = 0
        combined_assoc["match_min_dist_km"] = float("nan")
        combined_assoc["match_min_dt_min"] = float("nan")

    # Disagreement (Exploratory Archive: all ingested pilot records)
    grid_summary = build_grid_summary(combined)
    disagree = compute_disagreement(grid_summary)
    pairs = extract_paired_samples(disagree)

    # Strict November 1–10 calibration cohort (Strict Nov 1–10, 2022 & 2023 window: 2,554 co-active pairs)
    strict_dates = [f"2022-11-{d:02d}" for d in range(1, 11)] + [f"2023-11-{d:02d}" for d in range(1, 11)]
    combined_strict = combined[combined["acq_date"].isin(strict_dates)].copy().reset_index(drop=True)
    grid_strict = build_grid_summary(combined_strict)
    disagree_strict = compute_disagreement(grid_strict)
    pairs_strict = extract_paired_samples(disagree_strict)

    # Scientific calibration engine is evaluated strictly on the strict November 1–10 cohort (1,312 train / 1,242 eval)
    cal_results = run_all_calibrations(pairs_strict) if not pairs_strict.empty else {}

    # Reliability table — use best trained model
    best_model = None
    for key in ["context", "global", "identity"]:
        if key in cal_results and cal_results[key].trained:
            best_model = cal_results[key]
            break

    reliability = (
        build_reliability_table(disagree, best_model)
        if best_model and not disagree.empty
        else pd.DataFrame()
    )

    return {
        "modis": modis,
        "viirs": viirs,
        "combined": combined,
        "combined_assoc": combined_assoc,
        "grid_summary": grid_summary,
        "disagree": disagree,
        "pairs": pairs,
        "pairs_strict": pairs_strict,
        "cal_results": cal_results,
        "reliability": reliability,
        "using_real_data": using_real,
        "n_modis": len(modis),
        "n_viirs": len(viirs),
    }


def data_source_banner(using_real: bool) -> None:
    if using_real:
        st.markdown(
            '<div class="real-banner">✅ <strong>Real NASA FIRMS data</strong> — '
            'MODIS SP Collection 6.1 · VIIRS S-NPP SP Collection 2</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="synthetic-banner">⚠️ <strong>Synthetic demonstration data</strong> — '
            'Modelled on real Punjab/Haryana burning patterns. '
            'Download real data via the sidebar or run <code>python scripts/download_data.py</code>.</div>',
            unsafe_allow_html=True,
        )
