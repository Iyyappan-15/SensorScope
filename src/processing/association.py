"""
association.py — Spatial and temporal cross-sensor candidate matching.

Strategy:
  1. Group observations by (date, daynight) — broad day/night window.
  2. For each MODIS record, find VIIRS records within:
     - ASSOC_TIME_WINDOW_MINUTES of acquisition time
     - ASSOC_SPATIAL_TOLERANCE_KM of lat/lon (Haversine)
  3. Classify each record:
     - "matched"    — has ≥1 candidate association
     - "unmatched"  — no candidate found
     - "ambiguous"  — has >1 candidate with similar time+distance

NOTE: This produces *candidate* associations, not confirmed fire identity.
      A large MODIS pixel can overlap many small VIIRS pixels (many-to-many).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    ASSOC_TIME_WINDOW_MINUTES,
    ASSOC_SPATIAL_TOLERANCE_KM,
)

log = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0


# ── Haversine distance ─────────────────────────────────────────────────────────

def haversine_km(
    lat1: np.ndarray, lon1: np.ndarray,
    lat2: np.ndarray, lon2: np.ndarray,
) -> np.ndarray:
    """Vectorized Haversine distance in km."""
    lat1 = np.asarray(lat1, dtype=np.float64)
    lon1 = np.asarray(lon1, dtype=np.float64)
    lat2 = np.asarray(lat2, dtype=np.float64)
    lon2 = np.asarray(lon2, dtype=np.float64)
    r = EARTH_RADIUS_KM
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


# ── Time difference helper ─────────────────────────────────────────────────────

def _time_diff_minutes(dt1: pd.Series, dt2: pd.Series) -> np.ndarray:
    """Absolute time difference in minutes between two Timestamp series."""
    return (dt1 - dt2).abs().dt.total_seconds().values / 60.0


# ── Main association function ──────────────────────────────────────────────────

def associate_sensors(
    df: pd.DataFrame,
    time_window_minutes: int = ASSOC_TIME_WINDOW_MINUTES,
    spatial_tolerance_km: float = ASSOC_SPATIAL_TOLERANCE_KM,
) -> pd.DataFrame:
    """
    Add association columns to the combined MODIS+VIIRS DataFrame.

    New columns added:
      match_status    — "matched" | "unmatched" | "ambiguous"
      match_count     — number of candidate partners found
      match_min_dist_km  — closest partner distance (NaN if unmatched)
      match_min_dt_min   — closest partner time delta in minutes (NaN if unmatched)

    Returns the DataFrame with these columns added.
    """
    if df.empty:
        for col in ["match_status", "match_count", "match_min_dist_km", "match_min_dt_min"]:
            df[col] = pd.NA
        return df

    # Ensure datetime is timezone-aware
    if not pd.api.types.is_datetime64_any_dtype(df["acq_datetime"]):
        df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], utc=True)

    # Initialize output columns
    df = df.copy()
    df["match_count"] = 0
    df["match_min_dist_km"] = float("nan")
    df["match_min_dt_min"] = float("nan")

    modis_mask = df["sensor"] == "MODIS"
    viirs_mask = df["sensor"] == "VIIRS"

    modis_df = df[modis_mask].copy()
    viirs_df = df[viirs_mask].copy()

    if modis_df.empty or viirs_df.empty:
        log.warning("One sensor has no records — skipping association.")
        df["match_status"] = "unmatched"
        return df

    log.info("Associating %d MODIS × %d VIIRS records…", len(modis_df), len(viirs_df))

    modis_lats = modis_df["latitude"].astype(float).to_numpy()
    modis_lons = modis_df["longitude"].astype(float).to_numpy()
    modis_dts  = modis_df["acq_datetime"].values

    viirs_lats = viirs_df["latitude"].astype(float).to_numpy()
    viirs_lons = viirs_df["longitude"].astype(float).to_numpy()
    viirs_dts  = viirs_df["acq_datetime"].values

    # For memory safety on 8 GB machines, process MODIS in blocks
    BLOCK = 500
    modis_idx = modis_df.index.to_numpy()

    for block_start in range(0, len(modis_df), BLOCK):
        block_end = min(block_start + BLOCK, len(modis_df))
        m_lats = modis_lats[block_start:block_end, None]  # (B, 1)
        m_lons = modis_lons[block_start:block_end, None]
        m_dts  = pd.to_datetime(modis_dts[block_start:block_end])

        # Broadcast VIIRS across this block
        v_lats = viirs_lats[None, :]  # (1, V)
        v_lons = viirs_lons[None, :]

        dist_km = haversine_km(m_lats, m_lons, v_lats, v_lons)  # (B, V)

        for b, global_idx in enumerate(modis_idx[block_start:block_end]):
            m_dt = m_dts[b]
            dt_min = (
                (pd.to_datetime(viirs_dts) - m_dt).total_seconds().values
                / 60.0
            )
            dt_min_abs = np.abs(dt_min)

            within_time  = dt_min_abs <= time_window_minutes
            within_space = dist_km[b] <= spatial_tolerance_km
            candidates   = within_time & within_space
            n_cands      = int(candidates.sum())

            df.at[global_idx, "match_count"] = n_cands
            if n_cands > 0:
                df.at[global_idx, "match_min_dist_km"] = float(dist_km[b][candidates].min())
                df.at[global_idx, "match_min_dt_min"]  = float(dt_min_abs[candidates].min())

    # Mirror: for each VIIRS record, check if any MODIS matched it
    viirs_idx = viirs_df.index.to_numpy()
    viirs_match_counts = np.zeros(len(viirs_df), dtype=int)

    for block_start in range(0, len(modis_df), BLOCK):
        block_end = min(block_start + BLOCK, len(modis_df))
        m_lats = modis_lats[block_start:block_end, None]
        m_lons = modis_lons[block_start:block_end, None]
        m_dts  = pd.to_datetime(modis_dts[block_start:block_end])

        for b in range(block_end - block_start):
            m_dt = m_dts[b]
            dt_min_abs = np.abs(
                (pd.to_datetime(viirs_dts) - m_dt).total_seconds().values / 60.0
            )
            within_time  = dt_min_abs <= time_window_minutes
            within_space = haversine_km(
                m_lats[b], m_lons[b], viirs_lats, viirs_lons
            ) <= spatial_tolerance_km
            viirs_match_counts += (within_time & within_space).astype(int)

    for i, vidx in enumerate(viirs_idx):
        df.at[vidx, "match_count"] = int(viirs_match_counts[i])

    # Classify match status
    def _status(row: pd.Series) -> str:
        n = row["match_count"]
        if n == 0:
            return "unmatched"
        if n == 1:
            return "matched"
        return "ambiguous"

    df["match_status"] = df.apply(_status, axis=1)

    counts = df["match_status"].value_counts().to_dict()
    log.info("Association complete: %s", counts)
    return df
