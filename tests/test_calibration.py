"""
test_calibration.py — Tests for calibration models, reliability gate, and empirical uncertainty.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from analysis.calibration import (
    model_identity,
    model_global,
    model_context,
    run_all_calibrations,
    extract_paired_samples,
    _compute_metrics,
)
from analysis.reliability import (
    assess_region,
    check_input_domain,
    compute_empirical_error_envelope,
    RegionReliability,
)


def test_reliability_abstention_on_sparse_data():
    """If distinct co-active cell-days < 20, reliability gate must ABSTAIN (RED)."""
    sparse_pairs = pd.DataFrame({
        "year": [2022] * 5,
        "month": [11] * 5,
        "season": ["Post-monsoon"] * 5,
        "daynight": ["D"] * 5,
        "frp_viirs": [10.0, 15.0, 20.0, 25.0, 30.0],
        "count_viirs": [2, 3, 2, 4, 3],
        "frp_modis": [12.0, 18.0, 22.0, 28.0, 35.0],
    })
    
    res = model_global(sparse_pairs)
    assert res.trained is False
    assert res.reliability_status == "red"
    assert "Insufficient" in res.reason


def test_reliability_gate_green_threshold():
    """Adequate sample + low bias + in-domain yields GREEN status."""
    from analysis.calibration import CalibrationResult, CalibrationMetrics
    mock_metrics = CalibrationMetrics(
        n_pairs=60,
        mae=4.2,
        rmse=5.1,
        mean_bias=0.5,
        mean_bias_pct=4.8,  # <= 15%
        spearman_r=0.88,
        model_name="Global RMA",
        split="val",
    )
    result = CalibrationResult(
        model_name="Global RMA",
        trained=True,
        reason="Mock",
        slope=1.1,
        intercept=2.0,
        val_metrics=mock_metrics,
        reliability_status="green",
    )
    
    assessment = assess_region("cell_30.5_75.5", n_paired_obs=65, best_result=result)
    assert assessment.status == "green"
    assert assessment.show_calibrated is True
    assert assessment.abstain is False


def test_input_domain_bounds_check():
    """Inputs outside Q01-Q99 training range or unrepresented categories must be rejected."""
    # Valid in-domain
    in_dom, msg = check_input_domain(50.0, "D", q01_frp=2.0, q99_frp=280.0)
    assert in_dom is True
    
    # Below Q01
    in_dom_low, msg_low = check_input_domain(0.5, "D", q01_frp=2.0, q99_frp=280.0)
    assert in_dom_low is False
    assert "below 1st percentile" in msg_low
    
    # Above Q99
    in_dom_high, msg_high = check_input_domain(500.0, "D", q01_frp=2.0, q99_frp=280.0)
    assert in_dom_high is False
    assert "exceeds 99th percentile" in msg_high
    
    # Unknown category
    in_dom_cat, msg_cat = check_input_domain(50.0, "Twilight", q01_frp=2.0, q99_frp=280.0)
    assert in_dom_cat is False
    assert "not represented" in msg_cat


def test_empirical_error_envelope_non_negative():
    """Lower error bounds must be physically non-negative (clipped at 0.0 MW)."""
    preds = np.array([5.0, 20.0, 100.0])
    e05 = -30.0  # Would push 5.0 and 20.0 negative
    e95 = 50.0
    lower, upper = compute_empirical_error_envelope(preds, e05=e05, e95=e95)
    
    assert (lower >= 0.0).all()
    assert lower[0] == 0.0
    assert lower[1] == 0.0
    assert lower[2] == 70.0
    assert upper[0] == 55.0
    assert upper[2] == 150.0


def test_no_target_leakage_in_model_context():
    """Verify Model C feature matrix uses ONLY predictor-side features."""
    pairs = pd.DataFrame({
        "year": [2022] * 120 + [2023] * 120,
        "month": [11] * 240,
        "season": ["Post-monsoon"] * 240,
        "daynight": ["D"] * 240,
        "frp_viirs": np.linspace(10, 100, 240),
        "count_viirs": np.random.randint(1, 5, 240),
        "frp_modis": np.linspace(12, 110, 240),
        "count_modis": np.random.randint(1, 4, 240),  # Target side
    })
    
    res = model_context(pairs)
    assert res.trained is True
    # Feature names must NOT include any modis attributes
    for fname in res.feature_names:
        assert "modis" not in fname.lower()
    assert res.feature_names == ["frp_viirs", "count_viirs", "is_night"]
