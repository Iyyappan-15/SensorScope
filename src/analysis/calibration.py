"""
calibration.py — SensorShift calibration models.

Three models in increasing complexity:
  A) Identity        — raw VIIRS FRP as MODIS reference (no correction)
  B) Global OLS      — simple linear regression across all matched pairs
  C) Context-aware   — OLS with interaction features (daynight, season, scan)

For scientific validity we use Reduced Major Axis (RMA/Deming) for the
global calibration (following Li et al. 2018 methodology), and OLS with
interaction terms for the context-aware model (simpler to validate clearly).

The module also exposes the RELIABILITY GATE which decides whether to:
  GREEN  — apply correction (sufficient data, good validation)
  YELLOW — show correction with caution warning
  RED    — abstain (insufficient data or out-of-domain)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import OneHotEncoder

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    MIN_PAIRS_FOR_CALIBRATION,
    MIN_PAIRS_FOR_CONTEXT_MODEL,
    RELIABILITY_GREEN_MIN_PAIRS,
    RELIABILITY_GREEN_MAX_BIAS_PCT,
    RELIABILITY_YELLOW_MIN_PAIRS,
    TRAIN_YEARS,
    VAL_YEARS,
    TEST_YEARS,
)

log = logging.getLogger(__name__)


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class CalibrationMetrics:
    n_pairs: int
    mae: float
    rmse: float
    mean_bias: float
    mean_bias_pct: float
    spearman_r: float
    model_name: str
    split: str  # "train" | "val" | "test"


@dataclass
class CalibrationResult:
    model_name: str
    trained: bool
    reason: str                      # Why model was/was not trained
    intercept: float = 0.0
    slope: float = 1.0
    feature_names: list[str] = field(default_factory=list)
    model_obj: object = None         # sklearn model (if any)
    train_metrics: CalibrationMetrics | None = None
    val_metrics: CalibrationMetrics | None = None
    test_metrics: CalibrationMetrics | None = None
    reliability_status: str = "red"  # "green" | "yellow" | "red"
    reliability_reason: str = ""


# ── Pair extractor ─────────────────────────────────────────────────────────────

def extract_paired_samples(
    disagree_df: pd.DataFrame,
    min_modis: float = 0.0,
    min_viirs: float = 0.0,
) -> pd.DataFrame:
    """
    Extract grid-cells where BOTH sensors reported activity.
    These are our calibration-eligible samples.

    Returns DataFrame with columns:
      year, month, season, daynight,
      frp_modis, frp_viirs, (and grid metadata)
    """
    pairs = disagree_df[disagree_df["has_both"]].copy()
    pairs = pairs[
        (pairs["frp_sum_modis"] > min_modis) &
        (pairs["frp_sum_viirs"] > min_viirs)
    ]

    # Rename for clarity
    pairs = pairs.rename(columns={
        "frp_sum_modis": "frp_modis",
        "frp_sum_viirs": "frp_viirs",
    })

    log.info("Paired samples available: %d", len(pairs))
    return pairs


def _chronological_split(
    pairs: pd.DataFrame,
    train_years: list[int] = TRAIN_YEARS,
    val_years: list[int] = VAL_YEARS,
    test_years: list[int] = TEST_YEARS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by year — strict chronological, no leakage."""
    train = pairs[pairs["year"].isin(train_years)]
    val   = pairs[pairs["year"].isin(val_years)]
    test  = pairs[pairs["year"].isin(test_years)]
    log.info("Split: train=%d val=%d test=%d", len(train), len(val), len(test))
    return train, val, test


# ── Metric computation ─────────────────────────────────────────────────────────

def _compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str,
    split: str,
) -> CalibrationMetrics:
    n = len(y_true)
    if n == 0:
        return CalibrationMetrics(0, np.nan, np.nan, np.nan, np.nan, np.nan, model_name, split)

    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    bias = float(np.mean(y_pred - y_true))
    bias_pct = bias / (np.mean(y_true) + 1e-9) * 100
    try:
        s1 = pd.Series(y_true)
        s2 = pd.Series(y_pred)
        rho = float(s1.corr(s2, method="spearman"))
        if np.isnan(rho):
            rho = 0.0
    except Exception:
        rho = 0.0

    return CalibrationMetrics(
        n_pairs=n, mae=mae, rmse=rmse,
        mean_bias=bias, mean_bias_pct=bias_pct,
        spearman_r=float(rho),
        model_name=model_name, split=split,
    )


# ── Reliability gate ───────────────────────────────────────────────────────────

def _assess_reliability(
    n_pairs: int,
    val_metrics: CalibrationMetrics | None,
) -> tuple[str, str]:
    """
    Return (status, reason) where status is 'green' | 'yellow' | 'red'.
    """
    if n_pairs < RELIABILITY_YELLOW_MIN_PAIRS:
        return "red", (
            f"Only {n_pairs} paired observations — below minimum of "
            f"{RELIABILITY_YELLOW_MIN_PAIRS} required for any calibration."
        )

    if val_metrics is None or np.isnan(val_metrics.mae):
        return "yellow", (
            f"{n_pairs} pairs available but validation data is insufficient. "
            "Use with caution."
        )

    if n_pairs >= RELIABILITY_GREEN_MIN_PAIRS and \
       abs(val_metrics.mean_bias_pct) <= RELIABILITY_GREEN_MAX_BIAS_PCT:
        return "green", (
            f"Calibration supported: {n_pairs} pairs, "
            f"validation bias {val_metrics.mean_bias_pct:.1f}%."
        )

    if n_pairs >= RELIABILITY_YELLOW_MIN_PAIRS:
        return "yellow", (
            f"Moderate evidence: {n_pairs} pairs, "
            f"validation bias {val_metrics.mean_bias_pct:.1f}% "
            f"(threshold ±{RELIABILITY_GREEN_MAX_BIAS_PCT}%). Use with caution."
        )

    return "red", f"Calibration not supported ({n_pairs} pairs)."


# ── Model A — Identity ─────────────────────────────────────────────────────────

def model_identity(pairs: pd.DataFrame) -> CalibrationResult:
    """Baseline A: no correction — VIIRS FRP used as-is."""
    result = CalibrationResult(
        model_name="Identity (no correction)",
        trained=True,
        reason="Baseline — raw VIIRS FRP reported as-is.",
        slope=1.0, intercept=0.0,
    )
    if pairs.empty:
        result.reliability_status = "red"
        result.reliability_reason = "No data."
        return result

    train, val, test = _chronological_split(pairs)
    y_v = pairs["frp_viirs"].values
    y_m = pairs["frp_modis"].values

    result.train_metrics = _compute_metrics(
        train["frp_modis"].values, train["frp_viirs"].values, result.model_name, "train"
    )
    if not val.empty:
        result.val_metrics = _compute_metrics(
            val["frp_modis"].values, val["frp_viirs"].values, result.model_name, "val"
        )
    if not test.empty:
        result.test_metrics = _compute_metrics(
            test["frp_modis"].values, test["frp_viirs"].values, result.model_name, "test"
        )

    status, reason = _assess_reliability(len(pairs), result.val_metrics)
    result.reliability_status = status
    result.reliability_reason = reason
    return result


# ── Model B — Global RMA regression ───────────────────────────────────────────

def model_global(pairs: pd.DataFrame) -> CalibrationResult:
    """
    Baseline B: Reduced Major Axis (RMA) regression — VIIRS → MODIS reference.
    Following Li et al. (2018) methodology.
    """
    result = CalibrationResult(
        model_name="Global RMA calibration",
        trained=False,
        reason="",
    )

    if len(pairs) < MIN_PAIRS_FOR_CALIBRATION:
        result.reason = (
            f"Insufficient pairs ({len(pairs)} < {MIN_PAIRS_FOR_CALIBRATION}) "
            "for global calibration."
        )
        result.reliability_status = "red"
        result.reliability_reason = result.reason
        return result

    train, val, test = _chronological_split(pairs)

    if len(train) < MIN_PAIRS_FOR_CALIBRATION:
        result.reason = f"Training split too small ({len(train)} pairs)."
        result.reliability_status = "red"
        result.reliability_reason = result.reason
        return result

    x_train = train["frp_viirs"].values
    y_train = train["frp_modis"].values

    # RMA slope = std(y) / std(x)  × sign(pearson r)
    r = float(pd.Series(x_train).corr(pd.Series(y_train)))
    if np.isnan(r) or r == 0:
        r = 1.0
    slope = (np.std(y_train) / (np.std(x_train) + 1e-9)) * np.sign(r)
    intercept = np.mean(y_train) - slope * np.mean(x_train)

    result.slope = float(slope)
    result.intercept = float(intercept)
    result.trained = True
    result.reason = f"RMA trained on {len(train)} pairs."

    def _predict(df: pd.DataFrame) -> np.ndarray:
        return slope * df["frp_viirs"].values + intercept

    result.train_metrics = _compute_metrics(
        y_train, _predict(train), result.model_name, "train"
    )
    if not val.empty:
        result.val_metrics = _compute_metrics(
            val["frp_modis"].values, _predict(val), result.model_name, "val"
        )
    if not test.empty:
        result.test_metrics = _compute_metrics(
            test["frp_modis"].values, _predict(test), result.model_name, "test"
        )

    status, reason = _assess_reliability(len(pairs), result.val_metrics)
    result.reliability_status = status
    result.reliability_reason = reason
    return result


# ── Model C — Context-aware OLS ───────────────────────────────────────────────

def model_context(pairs: pd.DataFrame) -> CalibrationResult:
    """
    Model C: OLS with contextual features.
    Features: frp_viirs, daynight (D/N), season, month_sin, month_cos.
    """
    result = CalibrationResult(
        model_name="Context-aware calibration",
        trained=False,
        reason="",
    )

    if len(pairs) < MIN_PAIRS_FOR_CONTEXT_MODEL:
        result.reason = (
            f"Insufficient pairs ({len(pairs)} < {MIN_PAIRS_FOR_CONTEXT_MODEL}) "
            "for context-aware model."
        )
        result.reliability_status = "red"
        result.reliability_reason = result.reason
        return result

    train, val, test = _chronological_split(pairs)

    if len(train) < MIN_PAIRS_FOR_CONTEXT_MODEL:
        result.reason = f"Training split too small ({len(train)} pairs)."
        result.reliability_status = "red"
        result.reliability_reason = result.reason
        return result

    def _build_features(df: pd.DataFrame) -> np.ndarray:
        frp = df["frp_viirs"].values.reshape(-1, 1)
        # Cyclic month encoding
        month_sin = np.sin(2 * np.pi * df["month"].values / 12).reshape(-1, 1)
        month_cos = np.cos(2 * np.pi * df["month"].values / 12).reshape(-1, 1)
        # Day/night binary
        is_night = (df["daynight"].values == "N").astype(float).reshape(-1, 1)
        return np.hstack([frp, month_sin, month_cos, is_night])

    X_train = _build_features(train)
    y_train = train["frp_modis"].values

    model = LinearRegression()
    model.fit(X_train, y_train)

    result.model_obj = model
    result.trained = True
    result.reason = f"Context-aware OLS trained on {len(train)} pairs."
    result.feature_names = ["frp_viirs", "month_sin", "month_cos", "is_night"]

    def _predict_ctx(df: pd.DataFrame) -> np.ndarray:
        return model.predict(_build_features(df))

    result.train_metrics = _compute_metrics(
        y_train, _predict_ctx(train), result.model_name, "train"
    )
    if not val.empty:
        result.val_metrics = _compute_metrics(
            val["frp_modis"].values, _predict_ctx(val), result.model_name, "val"
        )
    if not test.empty:
        result.test_metrics = _compute_metrics(
            test["frp_modis"].values, _predict_ctx(test), result.model_name, "test"
        )

    status, reason = _assess_reliability(len(pairs), result.val_metrics)
    result.reliability_status = status
    result.reliability_reason = reason
    return result


# ── Run all models ─────────────────────────────────────────────────────────────

def run_all_calibrations(pairs: pd.DataFrame) -> dict[str, CalibrationResult]:
    """Run all three models and return results dict."""
    return {
        "identity": model_identity(pairs),
        "global": model_global(pairs),
        "context": model_context(pairs),
    }
