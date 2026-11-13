"""
sample_data.py — Generate realistic synthetic FIRMS-format sample data.

Used as a fallback when:
  - API key is pending
  - API is unreachable
  - No downloaded files exist yet

Data is modelled on real Punjab/Haryana agricultural burning:
  - Peak seasons: Oct–Nov (Kharif stubble) and Apr–May (Rabi stubble)
  - MODIS: coarser, fewer detections, higher per-pixel FRP
  - VIIRS: finer, more detections, lower per-pixel FRP
  - Realistic overlap-period mismatch ratios

This data is CLEARLY LABELLED as synthetic.
Never mix it with real data in the same analysis.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SAMPLE_DIR, DEFAULT_BBOX

log = logging.getLogger(__name__)

RNG = np.random.default_rng(42)


# ── Region bounds ──────────────────────────────────────────────────────────────
WEST, SOUTH, EAST, NORTH = DEFAULT_BBOX  # Punjab/Haryana bbox


def _random_lats(n: int) -> np.ndarray:
    return RNG.uniform(SOUTH, NORTH, n)


def _random_lons(n: int) -> np.ndarray:
    return RNG.uniform(WEST, EAST, n)


def _seasonal_weight(month: int) -> float:
    """Higher fire probability in Oct–Nov and Apr–May."""
    weights = {10: 1.0, 11: 0.9, 4: 0.7, 5: 0.5,
               3: 0.2, 12: 0.15, 1: 0.05, 2: 0.05,
               6: 0.02, 7: 0.02, 8: 0.02, 9: 0.05}
    return weights.get(month, 0.03)


def _generate_month_counts(year: int, sensor: str) -> list[tuple]:
    """
    Returns list of (year, month, n_detections) tuples.
    VIIRS gets ~1.5-2.5× more detections than MODIS in the same month.
    """
    multiplier = 1.0 if sensor == "MODIS" else RNG.uniform(1.5, 2.5)
    base = 150 if sensor == "MODIS" else 300
    rows = []
    for month in range(1, 13):
        w = _seasonal_weight(month)
        n = max(0, int(base * w * multiplier * RNG.uniform(0.7, 1.3)))
        rows.append((year, month, n))
    return rows


def _make_records(year: int, month: int, n: int, sensor: str) -> pd.DataFrame:
    """Generate n fake fire detection records for one year-month-sensor."""
    if n == 0:
        return pd.DataFrame()

    # Random days in month
    import calendar
    max_day = calendar.monthrange(year, month)[1]
    days = RNG.integers(1, max_day + 1, n)
    dates = [f"{year}-{month:02d}-{d:02d}" for d in days]

    # Day/night mix: ~60% day, 40% night for MODIS; ~55/45 for VIIRS
    day_prob = 0.60 if sensor == "MODIS" else 0.55
    daynight = RNG.choice(["D", "N"], n, p=[day_prob, 1 - day_prob])

    # FRP: MODIS pixels are larger → higher aggregate FRP per pixel
    if sensor == "MODIS":
        frp = RNG.lognormal(mean=2.8, sigma=1.0, size=n)  # median ~16 MW
    else:
        frp = RNG.lognormal(mean=2.2, sigma=0.9, size=n)  # median ~9 MW
    frp = np.clip(frp, 1.0, 5000.0)

    times = RNG.integers(600, 1500, n)  # HHMM UTC

    if sensor == "MODIS":
        satellite = RNG.choice(["Aqua", "Terra"], n, p=[0.6, 0.4])
        scan  = RNG.uniform(0.9, 4.8, n)
        track = RNG.uniform(0.9, 2.5, n)
        confidence = RNG.choice(["l", "n", "h"], n, p=[0.1, 0.5, 0.4])
    else:
        satellite = np.full(n, "N")  # Suomi-NPP
        scan  = np.full(n, 0.375)
        track = np.full(n, 0.375)
        confidence = RNG.choice(["l", "n", "h"], n, p=[0.05, 0.4, 0.55])

    return pd.DataFrame({
        "latitude":   _random_lats(n).round(4),
        "longitude":  _random_lons(n).round(4),
        "acq_date":   dates,
        "acq_time":   [f"{t:04d}" for t in times],
        "satellite":  satellite,
        "frp":        frp.round(2),
        "confidence": confidence,
        "scan":       scan.round(3),
        "track":      track.round(3),
        "daynight":   daynight,
        "type":       0,
        "version":    "6.1NRT" if sensor == "MODIS" else "2.0NRT",
        "instrument": sensor,
    })


def generate_sample_data(
    years: list[int] | None = None,
    out_dir: Path = SAMPLE_DIR,
    label: str = "SYNTHETIC",
) -> dict[str, Path]:
    """
    Generate and save sample MODIS and VIIRS CSV files.
    Returns dict with keys 'modis' and 'viirs' pointing to saved files.
    """
    if years is None:
        years = [2022, 2023, 2024]

    out_dir.mkdir(parents=True, exist_ok=True)

    all_modis, all_viirs = [], []

    for year in years:
        for sensor, store in [("MODIS", all_modis), ("VIIRS", all_viirs)]:
            for y, m, n in _generate_month_counts(year, sensor):
                df = _make_records(y, m, n, sensor)
                if not df.empty:
                    store.append(df)

    modis_df = pd.concat(all_modis, ignore_index=True) if all_modis else pd.DataFrame()
    viirs_df = pd.concat(all_viirs, ignore_index=True) if all_viirs else pd.DataFrame()

    # Add bright columns that FIRMS CSVs have (we don't use them but normalize.py tolerates extras)
    if not modis_df.empty:
        modis_df["brightness"] = RNG.uniform(300, 400, len(modis_df)).round(2)
        modis_df["bright_t31"] = RNG.uniform(280, 330, len(modis_df)).round(2)

    if not viirs_df.empty:
        viirs_df["bright_ti4"] = RNG.uniform(300, 420, len(viirs_df)).round(2)
        viirs_df["bright_ti5"] = RNG.uniform(280, 340, len(viirs_df)).round(2)

    modis_path = out_dir / f"MODIS_SP_{label}_{years[0]}_{years[-1]}.csv"
    viirs_path = out_dir / f"VIIRS_SNPP_SP_{label}_{years[0]}_{years[-1]}.csv"

    modis_df.to_csv(modis_path, index=False)
    viirs_df.to_csv(viirs_path, index=False)

    log.info(
        "Synthetic data saved: MODIS=%d rows → %s | VIIRS=%d rows → %s",
        len(modis_df), modis_path.name,
        len(viirs_df), viirs_path.name,
    )

    return {"modis": modis_path, "viirs": viirs_path}
