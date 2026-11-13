"""
download_data.py — Standalone script to fetch real NASA FIRMS data.

MODIS SP and VIIRS SP both support 1-day requests in the FIRMS area API.
Multi-day requests (>1) return HTTP 400 for SP products.
This script downloads day-by-day for the key fire seasons.

Usage:
    python scripts/download_data.py

Downloaded files go to: data/raw/modis/ and data/raw/viirs/
"""

import sys
import time
import logging
import requests
from datetime import date, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)
log = logging.getLogger(__name__)

# ── Setup ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv
import os
load_dotenv(ROOT / ".env")

KEY     = os.getenv("FIRMS_MAP_KEY", "")
BBOX    = "73.8,29.5,77.5,32.5"   # Punjab & Haryana
BASE    = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
MODIS_D = ROOT / "data" / "raw" / "modis"
VIIRS_D = ROOT / "data" / "raw" / "viirs"
MODIS_D.mkdir(parents=True, exist_ok=True)
VIIRS_D.mkdir(parents=True, exist_ok=True)

# ── Target periods — key fire seasons ─────────────────────────────────────────
# SP data has ~3-month lag; use complete years 2022–2023
# Download Oct–Nov (Kharif stubble) + Apr–May (Rabi stubble)
PERIODS = [
    (date(2022, 10, 1), date(2022, 11, 30)),
    (date(2022,  4, 1), date(2022,  5, 31)),
    (date(2023, 10, 1), date(2023, 11, 30)),
    (date(2023,  4, 1), date(2023,  5, 31)),
]


def download_day(product: str, day: date, out_dir: Path) -> bool:
    """Download one day of data. Returns True if saved successfully."""
    fname = out_dir / f"{product}_{day.isoformat()}.csv"
    if fname.exists() and fname.stat().st_size > 100:
        return False  # Already have it

    url = f"{BASE}/{KEY}/{product}/{BBOX}/1/{day}"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and not r.text.strip().startswith("<"):
            lines = r.text.strip().splitlines()
            n_rows = max(0, len(lines) - 1)
            if n_rows > 0:
                fname.write_text(r.text, encoding="utf-8")
                log.info("  %s  %s  → %d rows", product, day, n_rows)
                return True
            else:
                log.debug("  %s  %s  → 0 rows (no fire activity)", product, day)
                return False
        else:
            log.warning("  HTTP %d for %s on %s", r.status_code, product, day)
            return False
    except Exception as e:
        log.error("  Error %s %s: %s", product, day, e)
        return False


def download_period(product: str, start: date, end: date, out_dir: Path) -> int:
    """Download day-by-day for a date range. Returns count of files saved."""
    saved = 0
    current = start
    while current <= end:
        ok = download_day(product, current, out_dir)
        if ok:
            saved += 1
        time.sleep(0.25)  # polite delay
        current += timedelta(days=1)
    return saved


def main():
    if not KEY:
        log.error("FIRMS_MAP_KEY not set in .env — cannot download real data.")
        sys.exit(1)

    log.info("Starting FIRMS data download (key: %s****)", KEY[:4])
    log.info("Region: Punjab & Haryana — %s", BBOX)
    total = 0

    for start, end in PERIODS:
        log.info("=== MODIS SP: %s → %s ===", start, end)
        saved = download_period("MODIS_SP", start, end, MODIS_D)
        total += saved
        log.info("  Saved %d files with data", saved)

        log.info("=== VIIRS S-NPP SP: %s → %s ===", start, end)
        saved = download_period("VIIRS_SNPP_SP", start, end, VIIRS_D)
        total += saved
        log.info("  Saved %d files with data", saved)

    log.info("=== Done — %d data files downloaded ===", total)
    log.info("MODIS files: %d", len(list(MODIS_D.glob("*.csv"))))
    log.info("VIIRS files: %d", len(list(VIIRS_D.glob("*.csv"))))


if __name__ == "__main__":
    main()
