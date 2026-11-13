"""
disagreement.py — Compute cross-sensor disagreement metrics.

Produces:
  - Per grid-cell daily summaries (count, FRP) for each sensor
  - D_count = VIIRS_count - MODIS_count
  - D_frp   = VIIRS_frp_sum - MODIS_frp_sum
  - Breakdowns by: daynight, season, frp_quartile, year, month
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import GRID_SIZE_KM

log = logging.getLogger(__name__)


SEASON_MAP = {12: "Winter", 1: "Winter", 2: "Winter",
              3: "Pre-monsoon", 4: "Pre-monsoon", 5: "Pre-monsoon",
              6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
              10: "Post-monsoon", 11: "Post-monsoon"}

FRP_BINS = [0, 10, 25, 75, float("inf")]
FRP_LABELS = ["Weak (<10 MW)", "Moderate (10–25 MW)",
              "Strong (25–75 MW)", "Very strong (>75 MW)"]


def _add_grid_id(df: pd.DataFrame, cell_deg: float = 0.1) -> pd.DataFrame:
    """
    Assign each detection to a rectangular grid cell.
    cell_deg ≈ 0.1° ≈ 11 km — close enough to 10 km for pilot analysis.
    """
    df = df.copy()
    df["grid_lat"] = (df["latitude"] / cell_deg).apply(np.floor) * cell_deg
    df["grid_lon"] = (df["longitude"] / cell_deg).apply(np.floor) * cell_deg
    df["grid_id"] = (
        df["grid_lat"].round(4).astype(str) + "_" +
        df["grid_lon"].round(4).astype(str)
    )
    return df


def _add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add year, month, season columns from acq_date."""
    df = df.copy()
    dates = pd.to_datetime(df["acq_date"])
    df["year"]   = dates.dt.year
    df["month"]  = dates.dt.month
    df["season"] = dates.dt.month.map(SEASON_MAP)
    return df


def _add_frp_quartile(df: pd.DataFrame) -> pd.DataFrame:
    """Label each detection by its FRP strength bin."""
    df = df.copy()
    df["frp_band"] = pd.cut(
        df["frp_mw"], bins=FRP_BINS, labels=FRP_LABELS, right=False
    )
    return df


# ── Grid-cell daily aggregation ────────────────────────────────────────────────

def build_grid_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate detections into (grid_id, acq_date, daynight, sensor) groups.

    Returns DataFrame with columns:
      grid_id, grid_lat, grid_lon, acq_date, year, month, season,
      daynight, sensor, count, frp_sum, frp_mean, frp_max
    """
    if df.empty:
        return pd.DataFrame()

    df = _add_grid_id(df)
    df = _add_temporal_features(df)

    agg = (
        df.groupby(["grid_id", "grid_lat", "grid_lon",
                    "acq_date", "year", "month", "season",
                    "daynight", "sensor"])
        .agg(
            count=("frp_mw", "count"),
            frp_sum=("frp_mw", "sum"),
            frp_mean=("frp_mw", "mean"),
            frp_max=("frp_mw", "max"),
        )
        .reset_index()
    )

    log.info("Grid summary: %d cell-day-sensor records.", len(agg))
    return agg


# ── Disagreement computation ───────────────────────────────────────────────────

def compute_disagreement(grid_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot the grid summary to have MODIS and VIIRS side by side,
    then compute delta metrics.

    Returns DataFrame with one row per (grid_id, acq_date, daynight)
    with columns:
      modis_count, viirs_count, d_count,
      modis_frp_sum, viirs_frp_sum, d_frp,
      has_both, modis_only, viirs_only
    """
    if grid_summary.empty:
        return pd.DataFrame()

    pivot = grid_summary.pivot_table(
        index=["grid_id", "grid_lat", "grid_lon",
               "acq_date", "year", "month", "season", "daynight"],
        columns="sensor",
        values=["count", "frp_sum", "frp_mean"],
        aggfunc="first",
    ).reset_index()

    # Flatten multi-level columns
    pivot.columns = [
        "_".join(c).strip("_") if isinstance(c, tuple) else c
        for c in pivot.columns
    ]

    # Rename to clear names
    rename_map = {}
    for col in pivot.columns:
        if col.endswith("_MODIS"):
            rename_map[col] = col.replace("_MODIS", "_modis")
        elif col.endswith("_VIIRS"):
            rename_map[col] = col.replace("_VIIRS", "_viirs")
    pivot = pivot.rename(columns=rename_map)

    # Fill NaN with 0 for sensors that didn't observe
    for col in ["count_modis", "count_viirs", "frp_sum_modis", "frp_sum_viirs"]:
        if col not in pivot.columns:
            pivot[col] = 0.0
        else:
            pivot[col] = pivot[col].fillna(0.0)

    # Disagreement deltas
    pivot["d_count"] = pivot["count_viirs"] - pivot["count_modis"]
    pivot["d_frp"]   = pivot["frp_sum_viirs"] - pivot["frp_sum_modis"]

    # Observation flags
    pivot["has_both"]   = (pivot["count_modis"] > 0) & (pivot["count_viirs"] > 0)
    pivot["modis_only"] = (pivot["count_modis"] > 0) & (pivot["count_viirs"] == 0)
    pivot["viirs_only"] = (pivot["count_viirs"] > 0) & (pivot["count_modis"] == 0)

    log.info(
        "Disagreement: %d cell-days | both=%d | MODIS-only=%d | VIIRS-only=%d",
        len(pivot),
        pivot["has_both"].sum(),
        pivot["modis_only"].sum(),
        pivot["viirs_only"].sum(),
    )
    return pivot


# ── Summary statistics ─────────────────────────────────────────────────────────

def disagreement_by_daynight(disagree_df: pd.DataFrame) -> pd.DataFrame:
    """Group disagreement stats by day/night."""
    return (
        disagree_df.groupby("daynight")
        .agg(
            n_cells=("grid_id", "count"),
            mean_d_count=("d_count", "mean"),
            mean_d_frp=("d_frp", "mean"),
            pct_has_both=("has_both", "mean"),
            pct_modis_only=("modis_only", "mean"),
            pct_viirs_only=("viirs_only", "mean"),
        )
        .reset_index()
    )


def disagreement_by_season(disagree_df: pd.DataFrame) -> pd.DataFrame:
    """Group disagreement stats by season."""
    return (
        disagree_df.groupby("season")
        .agg(
            n_cells=("grid_id", "count"),
            mean_d_count=("d_count", "mean"),
            mean_d_frp=("d_frp", "mean"),
            pct_has_both=("has_both", "mean"),
        )
        .reset_index()
    )


def disagreement_by_year(disagree_df: pd.DataFrame) -> pd.DataFrame:
    """Monthly fire activity time series for both sensors."""
    return (
        disagree_df.groupby(["year", "month"])
        .agg(
            modis_total_count=("count_modis", "sum"),
            viirs_total_count=("count_viirs", "sum"),
            modis_total_frp=("frp_sum_modis", "sum"),
            viirs_total_frp=("frp_sum_viirs", "sum"),
            d_count=("d_count", "sum"),
            d_frp=("d_frp", "sum"),
        )
        .reset_index()
    )
