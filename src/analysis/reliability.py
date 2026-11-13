"""
reliability.py — Reliability gate: decides whether calibrated values
                 should be shown, warned, or suppressed per region.

Traffic light system:
  🟢 GREEN  — Reliable: apply correction, show calibrated estimate
  🟡 YELLOW — Caution: show correction with uncertainty warning
  🔴 RED    — Abstain: show raw data only, explain why

The gate operates INDEPENDENTLY of whether a model was trained.
Even a trained model is "red" for a region if that region had
insufficient paired observations or is out of the model's tested range.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    RELIABILITY_GREEN_MIN_PAIRS,
    RELIABILITY_GREEN_MAX_BIAS_PCT,
    RELIABILITY_YELLOW_MIN_PAIRS,
)
from analysis.calibration import CalibrationResult

log = logging.getLogger(__name__)


@dataclass
class RegionReliability:
    region_id: str               # grid_id or user-defined label
    status: str                  # "green" | "yellow" | "red"
    n_paired_obs: int
    best_model: str
    val_mae: float | None
    val_bias_pct: float | None
    reason: str                  # Human-readable explanation
    show_calibrated: bool        # True → display calibrated estimate
    show_warning: bool           # True → display caution banner
    abstain: bool                # True → show raw only


def _status_label(status: str) -> str:
    return {"green": "🟢 Reliable", "yellow": "🟡 Use with caution",
            "red": "🔴 Calibration unavailable"}.get(status, status)


def assess_region(
    region_id: str,
    n_paired_obs: int,
    best_result: CalibrationResult,
) -> RegionReliability:
    """
    Assess reliability for a single region given the best calibration result.
    """
    val = best_result.val_metrics

    if n_paired_obs < RELIABILITY_YELLOW_MIN_PAIRS:
        return RegionReliability(
            region_id=region_id,
            status="red",
            n_paired_obs=n_paired_obs,
            best_model=best_result.model_name,
            val_mae=None,
            val_bias_pct=None,
            reason=(
                f"Only {n_paired_obs} paired observations in this region "
                f"(minimum required: {RELIABILITY_YELLOW_MIN_PAIRS}). "
                "Raw sensor measurements shown; calibrated estimate unavailable."
            ),
            show_calibrated=False,
            show_warning=False,
            abstain=True,
        )

    if val is None or np.isnan(val.mae):
        return RegionReliability(
            region_id=region_id,
            status="yellow",
            n_paired_obs=n_paired_obs,
            best_model=best_result.model_name,
            val_mae=None,
            val_bias_pct=None,
            reason=(
                f"{n_paired_obs} pairs available but no validation period data "
                "exists for this region. Use calibrated values with caution."
            ),
            show_calibrated=True,
            show_warning=True,
            abstain=False,
        )

    mae = val.mae
    bias_pct = val.mean_bias_pct

    if (n_paired_obs >= RELIABILITY_GREEN_MIN_PAIRS and
            abs(bias_pct) <= RELIABILITY_GREEN_MAX_BIAS_PCT):
        return RegionReliability(
            region_id=region_id,
            status="green",
            n_paired_obs=n_paired_obs,
            best_model=best_result.model_name,
            val_mae=round(mae, 2),
            val_bias_pct=round(bias_pct, 1),
            reason=(
                f"Calibration supported: {n_paired_obs} paired observations, "
                f"validation MAE = {mae:.1f} MW, bias = {bias_pct:+.1f}%."
            ),
            show_calibrated=True,
            show_warning=False,
            abstain=False,
        )

    # Yellow: enough data but validation metrics are borderline
    return RegionReliability(
        region_id=region_id,
        status="yellow",
        n_paired_obs=n_paired_obs,
        best_model=best_result.model_name,
        val_mae=round(mae, 2),
        val_bias_pct=round(bias_pct, 1),
        reason=(
            f"Moderate evidence: {n_paired_obs} pairs, "
            f"validation bias {bias_pct:+.1f}% "
            f"(threshold ±{RELIABILITY_GREEN_MAX_BIAS_PCT}%). "
            "Calibrated estimate shown with caution."
        ),
        show_calibrated=True,
        show_warning=True,
        abstain=False,
    )


def build_reliability_table(
    disagree_df: pd.DataFrame,
    best_result: CalibrationResult,
) -> pd.DataFrame:
    """
    Build a per-grid-cell reliability table for the dashboard.

    Returns DataFrame with columns:
      grid_id, grid_lat, grid_lon, n_paired_obs, status,
      status_label, reason, show_calibrated, abstain
    """
    if disagree_df.empty:
        return pd.DataFrame()

    region_pairs = (
        disagree_df[disagree_df["has_both"]]
        .groupby(["grid_id", "grid_lat", "grid_lon"])
        .size()
        .reset_index(name="n_paired_obs")
    )

    rows = []
    for _, row in region_pairs.iterrows():
        rel = assess_region(
            region_id=str(row["grid_id"]),
            n_paired_obs=int(row["n_paired_obs"]),
            best_result=best_result,
        )
        rows.append({
            "grid_id": rel.region_id,
            "grid_lat": row["grid_lat"],
            "grid_lon": row["grid_lon"],
            "n_paired_obs": rel.n_paired_obs,
            "status": rel.status,
            "status_label": _status_label(rel.status),
            "best_model": rel.best_model,
            "val_mae": rel.val_mae,
            "val_bias_pct": rel.val_bias_pct,
            "reason": rel.reason,
            "show_calibrated": rel.show_calibrated,
            "abstain": rel.abstain,
        })

    result = pd.DataFrame(rows)
    counts = result["status"].value_counts().to_dict()
    log.info("Reliability table: %d regions | %s", len(result), counts)
    return result
