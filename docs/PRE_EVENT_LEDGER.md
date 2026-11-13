# Pre-Event Development & Asset Ledger

**Project Name:** SensorScope  
**Document Date:** November 13, 2026  
**Status:** Pre-Hackathon Inventory & Disclosure  

## 1. Context & Purpose
In accordance with NASA Space Apps Challenge transparency guidelines, this document explicitly records all code, datasets, tests, and materials created or staged prior to the official event start on November 14, 2026, at 9:00 AM local time.

No commit timestamps, records, or file origins have been backdated, concealed, or misrepresented.

## 2. Inventory of Pre-Event Assets
1. **Source Code:**
   - Multi-page Streamlit application (`app.py`, `pages/`).
   - Normalization, candidate association, and disagreement calculation pipelines (`src/processing/`, `src/analysis/`).
   - Baseline statistical calibration models (`src/analysis/calibration.py`).
   - Initial Reliability Gate logic (`src/analysis/reliability.py`).
2. **Downloaded Data:**
   - NASA FIRMS MODIS Collection 6.1 Standard Processing CSVs (`data/raw/modis/`).
   - NASA FIRMS VIIRS Suomi-NPP Collection 2 Standard Processing CSVs (`data/raw/viirs/`).
   - Synthetically generated fallback fixtures (`data/sample/`).
3. **Tests:**
   - Pytest unit tests (`tests/test_pipeline.py`, `tests/test_calibration.py`).
4. **Git Checkpoint:**
   - Commit `e59bb49` tagged and branched as `pre-event-mvp-checkpoint`.

## 3. Organizer Clarification Directive
The team will present this inventory to local event organizers / the NASA Space Apps Global Organizing Team to confirm formal eligibility and determine the approved protocol for utilizing or refactoring these assets during the competition window.
