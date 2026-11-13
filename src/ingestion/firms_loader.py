"""
firms_loader.py — Download MODIS SP and VIIRS SP data from NASA FIRMS API.

FIRMS Area API endpoint:
  GET /api/area/csv/{MAP_KEY}/{product}/{area}/{dayrange}/{date}

Where:
  product  = MODIS_SP | VIIRS_SNPP_SP
  area     = "west,south,east,north"  (decimal degrees)
  dayrange = 1–10  (days ending on `date`)
  date     = YYYY-MM-DD

Handles:
  - Rate-limit awareness (5000 tx / 10 min)
  - Chunked year-by-year downloading to stay within limits
  - Fallback detection if API returns empty or HTML error page
  - Saving raw CSVs with provenance filenames
"""

from __future__ import annotations

import time
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Generator

import requests

# Local import — use absolute so it works from any entry point
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    FIRMS_MAP_KEY,
    FIRMS_BASE_URL,
    MODIS_PRODUCT,
    VIIRS_PRODUCT,
    DEFAULT_BBOX,
    RAW_MODIS_DIR,
    RAW_VIIRS_DIR,
    FIRMS_MAX_DAYS_PER_REQUEST,
)

log = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _bbox_str(bbox: tuple[float, float, float, float]) -> str:
    """Format bounding box as FIRMS area string: west,south,east,north"""
    return ",".join(str(round(v, 4)) for v in bbox)


def _date_chunks(
    start: date,
    end: date,
    chunk_days: int = FIRMS_MAX_DAYS_PER_REQUEST,
) -> Generator[tuple[date, int], None, None]:
    """
    Yield (end_date, n_days) pairs for chunked FIRMS requests.
    FIRMS returns data for the `n_days` ENDING on `end_date`.
    """
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        n_days = (chunk_end - current).days + 1
        yield chunk_end, n_days
        current = chunk_end + timedelta(days=1)


def _safe_key() -> str:
    """Return masked key for logging — never log the real key."""
    if not FIRMS_MAP_KEY:
        return "<NOT SET>"
    return FIRMS_MAP_KEY[:4] + "****" + FIRMS_MAP_KEY[-4:]


# ── API test ───────────────────────────────────────────────────────────────────

def test_api_connection() -> dict:
    """
    Quick sanity check: request 1 day of MODIS data for the pilot AOI.
    Returns dict with keys: success (bool), status_code, rows, error.
    Never exposes the API key in the returned error string.
    """
    if not FIRMS_MAP_KEY:
        return {
            "success": False,
            "status_code": None,
            "rows": 0,
            "error": "FIRMS_MAP_KEY is not set. Add it to your .env file.",
        }

    # Use a known historical date to ensure SP data exists
    test_date = date(2022, 11, 1)
    area = _bbox_str(DEFAULT_BBOX)
    url = f"{FIRMS_BASE_URL}/{FIRMS_MAP_KEY}/{MODIS_PRODUCT}/{area}/1/{test_date}"

    log.info("Testing FIRMS API connection (key: %s)…", _safe_key())

    try:
        resp = requests.get(url, timeout=30)
        status = resp.status_code

        if status == 200:
            # Check it's real CSV, not an HTML error page
            text = resp.text.strip()
            if text.startswith("<"):
                return {
                    "success": False,
                    "status_code": status,
                    "rows": 0,
                    "error": "API returned HTML instead of CSV. Key may be invalid.",
                }
            lines = [l for l in text.splitlines() if l.strip()]
            # First line is header
            data_rows = max(0, len(lines) - 1)
            log.info("API test OK — %d data rows returned.", data_rows)
            return {"success": True, "status_code": 200, "rows": data_rows, "error": None}
        elif status == 400:
            return {"success": False, "status_code": 400, "rows": 0,
                    "error": "Bad request — check bounding box or date format."}
        elif status == 401:
            return {"success": False, "status_code": 401, "rows": 0,
                    "error": "Unauthorized — API key rejected."}
        elif status == 429:
            return {"success": False, "status_code": 429, "rows": 0,
                    "error": "Rate limit hit. Wait and retry."}
        else:
            return {"success": False, "status_code": status, "rows": 0,
                    "error": f"Unexpected HTTP {status}."}

    except requests.exceptions.ConnectionError:
        return {"success": False, "status_code": None, "rows": 0,
                "error": "Network error — cannot reach FIRMS server."}
    except requests.exceptions.Timeout:
        return {"success": False, "status_code": None, "rows": 0,
                "error": "Request timed out after 30 s."}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "status_code": None, "rows": 0,
                "error": f"Unexpected error: {type(exc).__name__}"}


# ── Downloader ─────────────────────────────────────────────────────────────────

def download_product(
    product: str,
    start_year: int,
    end_year: int,
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX,
    out_dir: Path | None = None,
    delay_seconds: float = 1.0,
    skip_existing: bool = True,
) -> list[Path]:
    """
    Download one product (MODIS_SP or VIIRS_SNPP_SP) for a year range.

    Downloads in 10-day chunks and saves each as a dated CSV.
    Returns list of paths to files that were saved (not skipped).
    """
    if not FIRMS_MAP_KEY:
        raise EnvironmentError(
            "FIRMS_MAP_KEY is not set. Add it to your .env file."
        )

    if out_dir is None:
        out_dir = RAW_MODIS_DIR if "MODIS" in product else RAW_VIIRS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    area = _bbox_str(bbox)
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    # SP data has a ~3-month lag; cap at a safe historical date
    # NRT data would be near-real-time but we use SP for scientific consistency
    safe_end = date.today() - timedelta(days=90)
    end = min(end, safe_end)

    saved: list[Path] = []

    for chunk_end, n_days in _date_chunks(start, end):
        fname = out_dir / f"{product}_{chunk_end.isoformat()}_d{n_days}.csv"
        if skip_existing and fname.exists() and fname.stat().st_size > 100:
            log.debug("Skip existing: %s", fname.name)
            continue

        url = f"{FIRMS_BASE_URL}/{FIRMS_MAP_KEY}/{product}/{area}/{n_days}/{chunk_end}"
        log.info("Fetching %s → %s", product, chunk_end)

        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200 and not resp.text.strip().startswith("<"):
                fname.write_text(resp.text, encoding="utf-8")
                saved.append(fname)
                log.info("  Saved %s (%d bytes)", fname.name, len(resp.text))
            elif resp.status_code == 429:
                log.warning("Rate limited — sleeping 60 s…")
                time.sleep(60)
                # Retry once
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200:
                    fname.write_text(resp.text, encoding="utf-8")
                    saved.append(fname)
            else:
                log.warning("HTTP %d for %s on %s", resp.status_code, product, chunk_end)
        except Exception as exc:  # noqa: BLE001
            log.error("Error downloading %s %s: %s", product, chunk_end, type(exc).__name__)

        time.sleep(delay_seconds)  # Be polite to the API

    return saved


def download_all(
    start_year: int,
    end_year: int,
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX,
    delay_seconds: float = 1.0,
) -> dict[str, list[Path]]:
    """Download both MODIS and VIIRS for the given period."""
    log.info("=== Downloading MODIS SP ===")
    modis_files = download_product(
        MODIS_PRODUCT, start_year, end_year, bbox,
        out_dir=RAW_MODIS_DIR, delay_seconds=delay_seconds,
    )
    log.info("=== Downloading VIIRS S-NPP SP ===")
    viirs_files = download_product(
        VIIRS_PRODUCT, start_year, end_year, bbox,
        out_dir=RAW_VIIRS_DIR, delay_seconds=delay_seconds,
    )
    return {"modis": modis_files, "viirs": viirs_files}
