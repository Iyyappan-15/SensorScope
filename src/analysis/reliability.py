"""
reliability.py — Evidence-based Reliability Gate & Empirical Error Bounds.

Decides whether calibrated estimates should be shown, warned, or suppressed:
  🟢 GREEN  — Supported within evaluated pilot conditions:
              adequate distinct paired observations (N >= 50 provisional),
              acceptable held-out bias (<= 15%), and input conditions in-domain.
  🟡 YELLOW — Caution:
              limited evidence (20 <= N < 50 provisional), borderline validation bias,
              or marginal input domain coverage.
  🔴 RED    — Abstain:
              insufficient paired observations (N < 20 provisional),
              or inputs outside the historical training distribution.

Empirical Error Envelopes:
  Computed from out-of-fold training residuals [max(0, y_hat + e_05), y_hat + e_95].
  Transparently labelled as descriptive empirical envelopes, NOT normal 95% intervals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

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
    region_id: str               # grid_id or descriptive region label
    status: str                  # "green" | "yellow" | "red"
    n_paired_obs: int            # Distinct co-active cell-day observations
    best_model: str
    val_mae: Optional[float]
    val_bias_pct: Optional[float]
    in_domain: bool              # True if input variables fall within Q01-Q99 training range
    reason: str                  # Transparent scientific rationale
    show_calibrated: bool        # True -> display calibrated estimate
    show_warning: bool           # True -> display caution banner
    abstain: bool                # True -> suppress calibrated estimate, show raw only


def check_input_domain(
    frp_viirs_value: float,
    daynight_value: str,
    q01_frp: float = 2.13,
    q99_frp: float = 279.18,
    known_daynight: tuple[str, ...] = ("D", "N"),
) -> tuple[bool, str]:
    """
    Check whether predictor input variables fall within the historical training range.
    Uses continuous percentiles on FRP, category representation on Day/Night.
    """
    if daynight_value not in known_daynight:
        return False, f"Day/Night condition '{daynight_value}' was not represented in training."
    
    if frp_viirs_value < q01_frp:
        return False, f"VIIRS FRP ({frp_viirs_value:.1f} MW) is below 1st percentile of training data ({q01_frp:.1f} MW)."
    
    if frp_viirs_value > q99_frp:
        return False, f"VIIRS FRP ({frp_viirs_value:.1f} MW) exceeds 99th percentile of training data ({q99_frp:.1f} MW)."
        
    return True, "Input variables within historical training domain."


def assess_region(
    region_id: str,
    n_paired_obs: int,
    best_result: CalibrationResult,
    input_frp_viirs: Optional[float] = None,
    input_daynight: str = "D",
    timing_dt_min: Optional[float] = None,
) -> RegionReliability:
    """
    Assess reliability for a given analysis unit (region or individual grid cell).
    Enforces sample adequacy, validation performance, input domain limits,
    and temporal subgroup validation bias constraints.
    """
    val = best_result.val_metrics
    
    # 1. Input domain check (if specific input values provided)
    in_domain = True
    domain_msg = ""
    if input_frp_viirs is not None:
        in_domain, domain_msg = check_input_domain(input_frp_viirs, input_daynight)
        if not in_domain:
            return RegionReliability(
                region_id=region_id,
                status="red",
                n_paired_obs=n_paired_obs,
                best_model=best_result.model_name,
                val_mae=None,
                val_bias_pct=None,
                in_domain=False,
                reason=f"Out of domain: {domain_msg} System abstains from extrapolation.",
                show_calibrated=False,
                show_warning=False,
                abstain=True,
            )

    # 2. Sample adequacy check (Provisional engineering rules: 20 / 50 distinct cell-days)
    if n_paired_obs < RELIABILITY_YELLOW_MIN_PAIRS:
        return RegionReliability(
            region_id=region_id,
            status="red",
            n_paired_obs=n_paired_obs,
            best_model=best_result.model_name,
            val_mae=None,
            val_bias_pct=None,
            in_domain=True,
            reason=(
                f"Only {n_paired_obs} distinct co-active cell-days in this unit "
                f"(provisional minimum required: {RELIABILITY_YELLOW_MIN_PAIRS}). "
                "Calibration unavailable; raw satellite observations preserved."
            ),
            show_calibrated=False,
            show_warning=False,
            abstain=True,
        )

    # 3. Validation evidence check
    if val is None or np.isnan(val.mae):
        return RegionReliability(
            region_id=region_id,
            status="yellow",
            n_paired_obs=n_paired_obs,
            best_model=best_result.model_name,
            val_mae=None,
            val_bias_pct=None,
            in_domain=True,
            reason=(
                f"{n_paired_obs} co-active cell-days available, but held-out validation "
                "evidence is incomplete. Calibrated values shown with caution."
            ),
            show_calibrated=True,
            show_warning=True,
            abstain=False,
        )

    mae = val.mae
    bias_pct = val.mean_bias_pct

    # 4. Temporal subgroup validation check (if timing delta is known)
    if timing_dt_min is not None:
        if timing_dt_min <= 5.0:
            # Subgroup bias is +26.94% (> 15% threshold) despite 31% MAE reduction
            subgroup_bias = 26.94
            return RegionReliability(
                region_id=region_id,
                status="yellow",
                n_paired_obs=n_paired_obs,
                best_model=best_result.model_name,
                val_mae=round(mae, 2),
                val_bias_pct=round(subgroup_bias, 1),
                in_domain=True,
                reason=(
                    f"Temporal subgroup caveat (Δt <= 5 min): held-out validation bias is +{subgroup_bias:.1f}%, "
                    f"exceeding the ±{RELIABILITY_GREEN_MAX_BIAS_PCT}% threshold despite a 31.1% MAE reduction. "
                    "Calibrated estimate shown with caution warning."
                ),
                show_calibrated=True,
                show_warning=True,
                abstain=False,
            )
        elif 5.0 < timing_dt_min <= 15.0:
            # Zero observations in 2023 evaluation dataset for 5-15 min interval
            return RegionReliability(
                region_id=region_id,
                status="yellow",
                n_paired_obs=n_paired_obs,
                best_model=best_result.model_name,
                val_mae=round(mae, 2),
                val_bias_pct=None,
                in_domain=True,
                reason=(
                    f"Temporal subgroup limitation (5 < Δt <= 15 min): zero co-active cell observations exist "
                    "in the 2023 evaluation sample for this interval. Calibrated estimate shown with caution."
                ),
                show_calibrated=True,
                show_warning=True,
                abstain=False,
            )

    # 5. Green status: Adequate sample, acceptable bias, supported within pilot conditions
    if (n_paired_obs >= RELIABILITY_GREEN_MIN_PAIRS and
            abs(bias_pct) <= RELIABILITY_GREEN_MAX_BIAS_PCT):
        return RegionReliability(
            region_id=region_id,
            status="green",
            n_paired_obs=n_paired_obs,
            best_model=best_result.model_name,
            val_mae=round(mae, 2),
            val_bias_pct=round(bias_pct, 1),
            in_domain=True,
            reason=(
                f"Reliable within evaluated pilot conditions: {n_paired_obs} co-active cell-days, "
                f"held-out validation MAE = {mae:.1f} MW, bias = {bias_pct:+.1f}%. "
                "(Note: Spatial/temporal dependence may reduce effective independent sample size)."
            ),
            show_calibrated=True,
            show_warning=False,
            abstain=False,
        )

    # 6. Yellow status: Moderate sample or borderline validation
    return RegionReliability(
        region_id=region_id,
        status="yellow",
        n_paired_obs=n_paired_obs,

        best_model=best_result.model_name,
        val_mae=round(mae, 2),
        val_bias_pct=round(bias_pct, 1),
        in_domain=True,
        reason=(
            f"Moderate evidence: {n_paired_obs} co-active cell-days, "
            f"validation bias {bias_pct:+.1f}% "
            f"(threshold ±{RELIABILITY_GREEN_MAX_BIAS_PCT}%). "
            "Calibrated estimate shown with uncertainty warning."
        ),
        show_calibrated=True,
        show_warning=True,
        abstain=False,
    )


def compute_empirical_error_envelope(
    y_pred: np.ndarray,
    e05: float = -52.68,
    e95: float = 77.65,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Construct descriptive empirical error envelopes from date-blocked out-of-fold training residuals.
    Computed via 5-fold GroupKFold by acquisition date on 1,314 training cell-days (e05 = -52.68 MW, e95 = 77.65 MW).
    Evaluated on 1,246 untouched held-out November 2023 cell-days: 1,179/1,246 observations fall within envelope (94.6% coverage).
    Lower bound is clipped at 0.0 MW (FRP cannot be physically negative).
    """
    y_pred = np.asarray(y_pred, dtype=float)
    lower = np.maximum(0.0, y_pred + e05)
    upper = y_pred + e95
    return lower, upper


def build_reliability_table(
    disagree_df: pd.DataFrame,
    best_result: CalibrationResult,
) -> pd.DataFrame:
    """
    Construct per-grid-cell reliability audit table.
    Evaluates each co-active grid cell in Punjab & Haryana against the
    validated regional calibration model and its empirical input domain.
    """
    if disagree_df.empty or best_result is None:
        return pd.DataFrame()

    # Aggregate co-active cells with local pair count and mean VIIRS FRP
    region_pairs = (
        disagree_df[disagree_df["has_both"]]
        .groupby(["grid_id", "grid_lat", "grid_lon"])
        .agg(
            n_paired_obs=("has_both", "size"),
            mean_viirs_frp=("frp_mean_viirs", "mean"),
        )
        .reset_index()
    )

    # Total evaluated regional sample backing the calibration
    total_regional_pairs = (
        best_result.val_metrics.n_pairs
        if (best_result and best_result.val_metrics)
        else len(disagree_df[disagree_df["has_both"]])
    )

    rows = []
    for _, row in region_pairs.iterrows():
        cell_frp = float(row["mean_viirs_frp"]) if not np.isnan(row["mean_viirs_frp"]) else 50.0
        
        # Assess cell against the validated regional model
        rel = assess_region(
            region_id=str(row["grid_id"]),
            n_paired_obs=total_regional_pairs,
            best_result=best_result,
            input_frp_viirs=cell_frp,
            input_daynight="D",
        )
        
        status_label = {
            "green": "🟢 Reliable (pilot)",
            "yellow": "🟡 Use with caution",
            "red": "🔴 Calibration unavailable",
        }.get(rel.status, rel.status)
        
        reason_text = (
            f"Supported by regional model (N={total_regional_pairs}): "
            f"{int(row['n_paired_obs'])} co-active cell-days observed locally; "
            f"mean FRP {cell_frp:.1f} MW within validated domain (Q01-Q99)."
            if rel.status == "green"
            else rel.reason
        )

        rows.append({
            "grid_id": rel.region_id,
            "grid_lat": row["grid_lat"],
            "grid_lon": row["grid_lon"],
            "n_paired_obs": int(row["n_paired_obs"]),
            "status": rel.status,
            "status_label": status_label,
            "best_model": rel.best_model,
            "val_mae": rel.val_mae,
            "val_bias_pct": rel.val_bias_pct,
            "reason": reason_text,
            "show_calibrated": rel.show_calibrated,
            "abstain": rel.abstain,
        })

    return pd.DataFrame(rows)
