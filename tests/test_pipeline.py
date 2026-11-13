"""
test_pipeline.py — End-to-end tests for normalization, association, and disagreement.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import SCHEMA_COLUMNS
from processing.normalize import parse_modis_csv, parse_viirs_csv
from processing.association import associate_sensors, haversine_km
from analysis.disagreement import build_grid_summary, compute_disagreement


def test_haversine_distance():
    # Distance between same points should be 0
    d = haversine_km(np.array([30.0]), np.array([75.0]), np.array([30.0]), np.array([75.0]))
    assert np.isclose(d[0], 0.0)

    # 1 degree latitude is approx 111 km
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


def test_association_logic():
    # Construct a minimal paired fixture
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
    assert matched["match_count"].iloc[1] >= 1


def test_disagreement_computation():
    t0 = pd.Timestamp("2022-11-02 08:00:00", tz="UTC")
    df = pd.DataFrame([
        {
            "sensor": "MODIS", "satellite": "Aqua", "product": "MODIS_SP",
            "latitude": 30.51, "longitude": 75.51, "acq_date": "2022-11-02",
            "acq_time": "0800", "acq_datetime": t0, "frp_mw": 30.0,
            "confidence_raw": "85", "daynight": "D", "scan": 1.0, "track": 1.0,
            "source_file": "test"
        },
        {
            "sensor": "VIIRS", "satellite": "SNPP", "product": "VIIRS_SNPP_SP",
            "latitude": 30.52, "longitude": 75.52, "acq_date": "2022-11-02",
            "acq_time": "0805", "acq_datetime": t0, "frp_mw": 12.0,
            "confidence_raw": "nominal", "daynight": "D", "scan": 0.375, "track": 0.375,
            "source_file": "test"
        }
    ])
    
    grid = build_grid_summary(df)
    disagree = compute_disagreement(grid)
    assert not disagree.empty
    assert (disagree["has_both"] == True).any()
    assert "d_count" in disagree.columns
    assert "d_frp" in disagree.columns
