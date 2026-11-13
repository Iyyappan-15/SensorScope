"""
normalize.py — Parse raw FIRMS CSVs into the common SensorScope schema.

MODIS SP columns (Collection 6.1):
  latitude, longitude, brightness, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, bright_t31, frp, daynight, type

VIIRS SP columns (Suomi-NPP C2):
  latitude, longitude, bright_ti4, scan, track, acq_date, acq_time,
  satellite, instrument, confidence, version, bright_ti5, frp, daynight, type

Both map to our canonical SCHEMA_COLUMNS.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SCHEMA_COLUMNS, RAW_MODIS_DIR, RAW_VIIRS_DIR

log = logging.getLogger(__name__)


# ── Column maps ────────────────────────────────────────────────────────────────

MODIS_RENAME: dict[str, str] = {
    "latitude": "latitude",
    "longitude": "longitude",
    "frp": "frp_mw",
    "confidence": "confidence_raw",
    "acq_date": "acq_date",
    "acq_time": "acq_time",
    "satellite": "satellite",
    "scan": "scan",
    "track": "track",
    "daynight": "daynight",
}

VIIRS_RENAME: dict[str, str] = {
    "latitude": "latitude",
    "longitude": "longitude",
    "frp": "frp_mw",
    "confidence": "confidence_raw",
    "acq_date": "acq_date",
    "acq_time": "acq_time",
    "satellite": "satellite",
    "scan": "scan",
    "track": "track",
    "daynight": "daynight",
}

# MODIS satellite name mapping from FIRMS satellite column
MODIS_SAT_MAP: dict[str, str] = {
    "Terra": "Terra",
    "Aqua": "Aqua",
    "T": "Terra",
    "A": "Aqua",
}


# ── Core parsers ───────────────────────────────────────────────────────────────

def _parse_datetime(df: pd.DataFrame) -> pd.Series:
    """Combine acq_date + zero-padded acq_time into UTC Timestamp series."""
    times = df["acq_time"].astype(str).str.zfill(4)
    dt_str = df["acq_date"].astype(str) + " " + times.str[:2] + ":" + times.str[2:]
    return pd.to_datetime(dt_str, format="%Y-%m-%d %H:%M", utc=True, errors="coerce")


def _validate_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows with obviously invalid lat/lon."""
    before = len(df)
    df = df[
        df["latitude"].between(-90, 90) &
        df["longitude"].between(-180, 180)
    ].copy()
    dropped = before - len(df)
    if dropped:
        log.warning("Dropped %d rows with invalid coordinates.", dropped)
    return df


def _validate_frp(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where FRP is negative or NaN."""
    before = len(df)
    df = df[df["frp_mw"] > 0].copy()
    dropped = before - len(df)
    if dropped:
        log.warning("Dropped %d rows with non-positive FRP.", dropped)
    return df


def parse_modis_csv(path: Path) -> pd.DataFrame:
    """
    Parse a single MODIS SP CSV file into the canonical schema.
    Returns empty DataFrame on failure.
    """
    try:
        raw = pd.read_csv(path, dtype={"acq_time": str, "confidence": str})
    except Exception as exc:  # noqa: BLE001
        log.error("Cannot read MODIS file %s: %s", path.name, exc)
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    if raw.empty:
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    # Lowercase column names to be robust
    raw.columns = raw.columns.str.lower().str.strip()

    # Rename
    df = raw.rename(columns=MODIS_RENAME)

    # Required columns
    required = ["latitude", "longitude", "frp_mw", "acq_date", "acq_time"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        log.error("MODIS file %s missing columns: %s", path.name, missing)
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    df["sensor"] = "MODIS"
    df["product"] = "MODIS_SP"

    # Normalize satellite name
    if "satellite" in df.columns:
        df["satellite"] = df["satellite"].map(MODIS_SAT_MAP).fillna(df["satellite"])
    else:
        df["satellite"] = "Unknown"

    # Day/night default
    if "daynight" not in df.columns:
        df["daynight"] = "D"
    df["daynight"] = df["daynight"].str.upper().str.strip()

    # Scan/track — keep as float, NaN if missing
    for col in ["scan", "track"]:
        if col not in df.columns:
            df[col] = float("nan")
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["frp_mw"] = pd.to_numeric(df["frp_mw"], errors="coerce")
    df["acq_time"] = df["acq_time"].astype(str).str.zfill(4)
    df["acq_datetime"] = _parse_datetime(df)
    df["source_file"] = path.name

    df = _validate_coordinates(df)
    df = _validate_frp(df)

    return df[SCHEMA_COLUMNS].copy()


def parse_viirs_csv(path: Path) -> pd.DataFrame:
    """
    Parse a single VIIRS SP CSV file into the canonical schema.
    """
    try:
        raw = pd.read_csv(path, dtype={"acq_time": str, "confidence": str})
    except Exception as exc:  # noqa: BLE001
        log.error("Cannot read VIIRS file %s: %s", path.name, exc)
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    if raw.empty:
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    raw.columns = raw.columns.str.lower().str.strip()
    df = raw.rename(columns=VIIRS_RENAME)

    required = ["latitude", "longitude", "frp_mw", "acq_date", "acq_time"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        log.error("VIIRS file %s missing columns: %s", path.name, missing)
        return pd.DataFrame(columns=SCHEMA_COLUMNS)

    df["sensor"] = "VIIRS"
    df["product"] = "VIIRS_SNPP_SP"

    # VIIRS satellite column is usually "N" (Suomi-NPP) or "1" (NOAA-20)
    if "satellite" in df.columns:
        sat_map = {"N": "SNPP", "Suomi-NPP": "SNPP", "1": "NOAA20", "NOAA-20": "NOAA20"}
        df["satellite"] = df["satellite"].astype(str).map(sat_map).fillna("SNPP")
    else:
        df["satellite"] = "SNPP"

    if "daynight" not in df.columns:
        df["daynight"] = "D"
    df["daynight"] = df["daynight"].str.upper().str.strip()

    # VIIRS also has scan/track in the CSV but they are fixed (0.375 km)
    for col in ["scan", "track"]:
        if col not in df.columns:
            df[col] = 0.375
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["frp_mw"] = pd.to_numeric(df["frp_mw"], errors="coerce")
    df["acq_time"] = df["acq_time"].astype(str).str.zfill(4)
    df["acq_datetime"] = _parse_datetime(df)
    df["source_file"] = path.name

    df = _validate_coordinates(df)
    df = _validate_frp(df)

    return df[SCHEMA_COLUMNS].copy()


# ── Batch loaders ──────────────────────────────────────────────────────────────

def load_all_modis(directory: Path = RAW_MODIS_DIR) -> pd.DataFrame:
    """Load and concatenate all MODIS CSVs in directory with non-destructive duplicate auditing."""
    files = sorted(directory.glob("*.csv"))
    if not files:
        log.warning("No MODIS CSV files found in %s", directory)
        return pd.DataFrame(columns=SCHEMA_COLUMNS)
    frames = [parse_modis_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    exact_dups = df.duplicated().sum()
    if exact_dups > 0:
        log.info("Dropped %d exact duplicate MODIS rows.", exact_dups)
        df = df.drop_duplicates()
    log.info("MODIS: loaded %d records from %d files.", len(df), len(files))
    return df


def load_all_viirs(directory: Path = RAW_VIIRS_DIR) -> pd.DataFrame:
    """Load and concatenate all VIIRS CSVs in directory with non-destructive duplicate auditing."""
    files = sorted(directory.glob("*.csv"))
    if not files:
        log.warning("No VIIRS CSV files found in %s", directory)
        return pd.DataFrame(columns=SCHEMA_COLUMNS)
    frames = [parse_viirs_csv(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    exact_dups = df.duplicated().sum()
    if exact_dups > 0:
        log.info("Dropped %d exact duplicate VIIRS rows.", exact_dups)
        df = df.drop_duplicates()
    log.info("VIIRS: loaded %d records from %d files.", len(df), len(files))
    return df


def load_all(
    modis_dir: Path = RAW_MODIS_DIR,
    viirs_dir: Path = RAW_VIIRS_DIR,
) -> pd.DataFrame:
    """Load both sensors and return a single combined DataFrame."""
    modis = load_all_modis(modis_dir)
    viirs = load_all_viirs(viirs_dir)
    combined = pd.concat([modis, viirs], ignore_index=True)
    combined = combined.sort_values("acq_datetime").reset_index(drop=True)
    log.info("Combined: %d records total (MODIS=%d, VIIRS=%d).",
             len(combined), len(modis), len(viirs))
    return combined
