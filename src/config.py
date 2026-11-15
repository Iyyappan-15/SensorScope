"""
SensorScope — Global configuration and constants.
All region defaults, API endpoints, and schema constants live here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ──────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent.parent / ".env")

# ── API ────────────────────────────────────────────────────────────────────────
FIRMS_MAP_KEY: str = os.getenv("FIRMS_MAP_KEY", "")
FIRMS_BASE_URL: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_AVAILABILITY_URL: str = "https://firms.modaps.eosdis.nasa.gov/api/data_availability.json"

# ── Regional Key Cities (Punjab & Haryana reference landmarks) ─────────────────
REGIONAL_KEY_CITIES: list[dict[str, any]] = [
    {"name": "Ludhiana", "lat": 30.9010, "lon": 75.8573, "state": "Punjab"},
    {"name": "Amritsar", "lat": 31.6340, "lon": 74.8723, "state": "Punjab"},
    {"name": "Jalandhar", "lat": 31.3260, "lon": 75.5762, "state": "Punjab"},
    {"name": "Patiala", "lat": 30.3398, "lon": 76.3869, "state": "Punjab"},
    {"name": "Bathinda", "lat": 30.2110, "lon": 74.9455, "state": "Punjab"},
    {"name": "Sangrur", "lat": 30.2458, "lon": 75.8420, "state": "Punjab"},
    {"name": "Firozpur", "lat": 30.9237, "lon": 74.6111, "state": "Punjab"},
    {"name": "Moga", "lat": 30.8165, "lon": 75.1717, "state": "Punjab"},
    {"name": "Chandigarh", "lat": 30.7333, "lon": 76.7794, "state": "UT"},
    {"name": "Ambala", "lat": 30.3782, "lon": 76.7767, "state": "Haryana"},
    {"name": "Karnal", "lat": 29.6857, "lon": 76.9905, "state": "Haryana"},
    {"name": "Hisar", "lat": 29.1492, "lon": 75.7217, "state": "Haryana"},
    {"name": "Sirsa", "lat": 29.5349, "lon": 75.0296, "state": "Haryana"},
    {"name": "Panipat", "lat": 29.3909, "lon": 76.9635, "state": "Haryana"},
]

# ── Products ───────────────────────────────────────────────────────────────────
MODIS_PRODUCT: str = "MODIS_SP"       # Collection 6.1 Standard Processing
VIIRS_PRODUCT: str = "VIIRS_SNPP_SP"  # Suomi-NPP Collection 2 Standard Processing

# ── Pilot Area of Interest — Punjab & Haryana, India ──────────────────────────
# Bounding box: (west, south, east, north)
DEFAULT_BBOX: tuple[float, float, float, float] = (73.8, 29.5, 77.5, 32.5)
AOI_NAME: str = "Punjab & Haryana, India"

# Parse override from env
_bbox_env = os.getenv("AOI_BBOX", "")
if _bbox_env:
    try:
        _parts = [float(x) for x in _bbox_env.split(",")]
        if len(_parts) == 4:
            DEFAULT_BBOX = tuple(_parts)  # type: ignore
    except ValueError:
        pass

# ── Date ranges ────────────────────────────────────────────────────────────────
DATA_START_YEAR: int = int(os.getenv("DATA_START_YEAR", "2022"))
DATA_END_YEAR: int = int(os.getenv("DATA_END_YEAR", "2024"))

# FIRMS API limit: max 10 days per request for area queries
FIRMS_MAX_DAYS_PER_REQUEST: int = 10

# ── Spatial grid ───────────────────────────────────────────────────────────────
GRID_SIZE_KM: float = 10.0   # Nominal ~10 km scale; actual analysis bins use 0.1° geographic grid (~11.1 km N-S x 9.6 km E-W)
GRID_CRS: str = "EPSG:32643"  # UTM Zone 43N — covers Punjab/Haryana well

# ── Sensor association thresholds ──────────────────────────────────────────────
ASSOC_TIME_WINDOW_MINUTES: int = 15     # Candidate temporal window
ASSOC_SPATIAL_TOLERANCE_KM: float = 11.0  # Exploratory candidate-association search radius (~0.1° scale)

# ── Calibration ────────────────────────────────────────────────────────────────
# Minimum paired samples required to attempt calibration
MIN_PAIRS_FOR_CALIBRATION: int = 30
# Minimum pairs required for a context-aware (feature-rich) model
MIN_PAIRS_FOR_CONTEXT_MODEL: int = 100
# Train / validation / test split years
TRAIN_YEARS: list[int] = [2022]
VAL_YEARS: list[int] = [2023]
TEST_YEARS: list[int] = [2024]

# ── Reliability gate thresholds ────────────────────────────────────────────────
# Green  — calibration applied
RELIABILITY_GREEN_MIN_PAIRS: int = 50
RELIABILITY_GREEN_MAX_BIAS_PCT: float = 15.0   # % mean bias

# Yellow — use with caution
RELIABILITY_YELLOW_MIN_PAIRS: int = 20

# Red    — abstain (below yellow threshold or out-of-domain)

# ── Canonical schema ───────────────────────────────────────────────────────────
# Column names after normalization — both sensors map to these
SCHEMA_COLUMNS: list[str] = [
    "sensor",        # "MODIS" | "VIIRS"
    "satellite",     # "Aqua" | "Terra" | "SNPP" | "NOAA20"
    "product",       # e.g. "MODIS_SP" | "VIIRS_SNPP_SP"
    "latitude",
    "longitude",
    "acq_date",      # date  (YYYY-MM-DD)
    "acq_time",      # int   (HHMM UTC)
    "acq_datetime",  # pd.Timestamp UTC
    "frp_mw",        # Fire Radiative Power in MW
    "confidence_raw",# Original string confidence
    "daynight",      # "D" | "N"
    "scan",          # reported scan size (km) — MODIS only; NaN for VIIRS
    "track",         # reported track size (km) — MODIS only; NaN for VIIRS
    "source_file",   # original filename for provenance
]

# ── Paths ───────────────────────────────────────────────────────────────────────
ROOT_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = ROOT_DIR / "data"
RAW_MODIS_DIR: Path = DATA_DIR / "raw" / "modis"
RAW_VIIRS_DIR: Path = DATA_DIR / "raw" / "viirs"
PROCESSED_DIR: Path = DATA_DIR / "processed"
SAMPLE_DIR: Path = DATA_DIR / "sample"
DUCKDB_PATH: Path = PROCESSED_DIR / "sensorscope.duckdb"

# Ensure dirs exist at import time
for _d in [RAW_MODIS_DIR, RAW_VIIRS_DIR, PROCESSED_DIR, SAMPLE_DIR]:
    _d.mkdir(parents=True, exist_ok=True)
