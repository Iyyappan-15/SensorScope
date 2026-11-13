"""
test_pipeline.py — End-to-end tests for normalization, association, disagreement, and accounting.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import SCHEMA_COLUMNS, RAW_MODIS_DIR, RAW_VIIRS_DIR
from processing.normalize import parse_modis_csv, parse_viirs_csv, load_all
from processing.association import associate_sensors, haversine_km
from analysis.disagreement import build_grid_summary, compute_disagreement


def test_haversine_distance():
    d = haversine_km(np.array([30.0]), np.array([75.0]), np.array([30.0]), np.array([75.0]))
    assert np.isclose(d[0], 0.0)

    d1 = haversine_km(np.array([30.0]), np.array([75.0]), np.array([31.0]), np.array([75.0]))
    assert 110.0 < d1[0] < 112.0


def test_normalize_schema_compliance():
    sample_modis = ROOT / "data" / "sample" / "MODIS_SP_SYNTHETIC_2022_2024.csv"
    if sample_modis.exists():
        df = parse_modis_csv(sample_modis)
        assert not df.empty
        assert list(df.columns) == SCHEMA_COLUMNS
        assert (df["sensor"] == "MODIS").all()
        assert (df["frp_mw"] > 0).all()


def test_association_candidate_logic():
    t0 = pd.Timestamp("2022-11-02 08:00:00", tz="UTC")
    df = pd.DataFrame([
        {
            "sensor": "MODIS", "satellite": "Aqua", "product": "MODIS_SP",
            "latitude": 30.500, "longitude": 75.500, "acq_date": "2022-11-02",
            "acq_time": "0800", "acq_datetime": t0, "frp_mw": 25.0,
            "confidence_raw": "80", "daynight": "D", "scan": 1.1, "track": 1.0,
            "source_file": "test"
        },
        {
            "sensor": "VIIRS", "satellite": "SNPP", "product": "VIIRS_SNPP_SP",
            "latitude": 30.505, "longitude": 75.505, "acq_date": "2022-11-02",
            "acq_time": "0805", "acq_datetime": t0 + pd.Timedelta(minutes=5), "frp_mw": 15.0,
            "confidence_raw": "nominal", "daynight": "D", "scan": 0.375, "track": 0.375,
            "source_file": "test"
        }
    ])
    
    matched = associate_sensors(df, time_window_minutes=15, spatial_tolerance_km=11.0)
    assert matched["match_status"].iloc[0] == "matched"
    assert matched["match_status"].iloc[1] == "matched"
    assert matched["match_count"].iloc[0] >= 1


def test_cell_day_accounting_reconciliation():
    """Verify exact mathematical reconciliation between sensor-specific and pivoted cell-days."""
    if not (RAW_MODIS_DIR.exists() and list(RAW_MODIS_DIR.glob("*.csv"))):
        pytest.skip("Raw NASA data not downloaded yet.")
        
    combined = load_all(RAW_MODIS_DIR, RAW_VIIRS_DIR)
    grid = build_grid_summary(combined)
    dis = compute_disagreement(grid)
    
    both = int(dis["has_both"].sum())
    m_only = int(dis["modis_only"].sum())
    v_only = int(dis["viirs_only"].sum())
    
    # 1. Total distinct active cell-days must equal sum of partition
    assert len(dis) == both + m_only + v_only
    # 2. Total sensor-specific grid rows must equal 2*both + m_only + v_only
    assert len(grid) == 2 * both + m_only + v_only
    # 3. Check exact real dataset counts and diurnal vs calendar reconciliation
    if len(dis) == 6772:
        assert len(grid) == 9332
        assert both == 2560
        assert m_only == 488
        assert v_only == 3724
        # Unique (grid_id, acq_date) calendar cell-days
        n_unique_cell_dates = len(dis.drop_duplicates(subset=["grid_id", "acq_date"]))
        assert n_unique_cell_dates == 6751
        assert len(dis) - n_unique_cell_dates == 21  # exactly 21 cell-dates had both Day and Night passes

