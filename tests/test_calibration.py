"""
test_calibration.py — Tests for calibration models and reliability gate.
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
)
from analysis.reliability import assess_region, RegionReliability


def test_reliability_abstention_on_sparse_data():
    # If pairs < 20, reliability status must be RED
    sparse_pairs = pd.DataFrame({
        "year": [2022] * 5,
        "month": [11] * 5,
        "season": ["Post-monsoon"] * 5,
        "daynight": ["D"] * 5,
        "frp_viirs": [10.0, 15.0, 20.0, 25.0, 30.0],
        "frp_modis": [12.0, 18.0, 22.0, 28.0, 35.0],
    })
    
    res = model_global(sparse_pairs)
    assert res.trained is False
    assert res.reliability_status == "red"
    assert "Insufficient" in res.reason


def test_reliability_gate_green_threshold():
    # Create an artificial result that meets green criteria
    from analysis.calibration import CalibrationResult, CalibrationMetrics
    mock_metrics = CalibrationMetrics(
        n_pairs=60,
        mae=4.2,
        rmse=5.1,
        mean_bias=0.5,
        mean_bias_pct=4.8,  # Under 15%
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
