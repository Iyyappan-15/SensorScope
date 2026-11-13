# NASA Data Provenance & Quality Audit Report

**Project:** SensorScope  
**Audit Date:** November 13, 2026  
**Auditor:** Automated Empirical Pipeline Check  

---

## 1. Primary NASA Data Sources

| Parameter | MODIS Standard Processing | VIIRS Standard Processing |
|:---|:---|:---|
| **Product Name** | `MODIS_SP` (Collection 6.1) | `VIIRS_SNPP_SP` (Collection 2) |
| **Instrument** | Moderate Resolution Imaging Spectroradiometer | Visible Infrared Imaging Radiometer Suite |
| **Satellite Platforms** | Aqua (97.9%), Terra (2.1%) | Suomi-NPP (100.0%) |
| **Nominal Nadir Resolution** | 1,000 m (expands to ~4.8 km at scan edges) | 375 m (I-band active fire product) |
| **Source Agency** | NASA LANCE / FIRMS EOSDIS | NASA LANCE / FIRMS EOSDIS |
| **Source URL** | https://firms.modaps.eosdis.nasa.gov | https://firms.modaps.eosdis.nasa.gov |

---

## 2. Spatial Extent & Temporal Coverage

- **Pilot Bounding Box:** `[73.8°E, 29.5°N, 77.5°E, 32.5°N]`  
  *Clarification:* This is a regular rectangular bounding box enclosing the Punjab and Haryana agricultural burning region. It is **not** an administrative boundary clip.
- **Acquisition Dates:**
  - Training Window: `2022-11-01` to `2022-11-10` (Peak Kharif stubble burning)
  - Held-Out Evaluation Window: `2023-11-01` to `2023-11-10` (Subsequent year peak Kharif)
  - Ancillary Spring Season Check: `2022-04-01` to `2022-05-31` and `2023-04-01` to `2023-05-31` (Rabi season)

---

## 3. Data Cleaning, Filtering & Duplicates

- **Raw Rows Downloaded:**
  - MODIS: 8,472 records across 24 files
  - VIIRS: 33,853 records across 24 files
- **Duplicate Audit:**
  - Exact identical row duplicates: **0 rows** (0.0%)
  - Lat/Lon/Time identical co-occurrences: **0 rows** (0.0%)
  - All 8,472 MODIS and 33,853 VIIRS records are genuinely unique observations.
- **FRP Bounds & Missing Values:**
  - Non-positive or negative FRP values: **0 records**
  - Minimum observed FRP: MODIS = 3.10 MW, VIIRS = 0.23 MW (reflecting VIIRS 375 m fine-pixel sensitivity)
  - Maximum observed FRP: MODIS = 158.00 MW, VIIRS = 139.01 MW
  - Coordinate validation: 100% of detections fall within latitude [-90, 90] and longitude [-180, 180].

---

## 4. FRP Metric Formulation & Physical Interpretation

$$\text{FRP}_{\text{cell-day}} = \sum_{i=1}^{n} \text{FRP}_{\text{pixel}, i}$$

- **Formal Definition:** **Summed observed pixel-level FRP per grid-cell-day (MW)**.
- **Physical Boundary:** This is an instantaneous power summary (in Megawatts, MW) of detected hotspot pixels within the cell on that acquisition day.
- **Explicit Clarification:** This is **not** integrated fire radiative energy (FRE, which is in Joules/Megajoules integrated over fire duration) and does **not** represent continuous total physical fire energy.

---

## 5. Mathematical Cell-Day Accounting Reconciliation

The apparent discrepancy between 9,332 records and 6,772 cells is fully reconciled as follows:
- **`grid_summary` table (9,332 rows):** Grouped by `(grid_id, acq_date, daynight, sensor)`.
- **`disagreement` table (6,772 rows):** Pivoted by `(grid_id, acq_date, daynight)` with MODIS and VIIRS side by side.
  - Jointly active cell-days (Both sensors detected fire): **2,560**
  - MODIS-only cell-days (VIIRS detected no fire in cell): **488**
  - VIIRS-only cell-days (MODIS detected no fire in cell): **3,724**

**Mathematical Proof:**
$$\text{Sensor-specific rows} = 2 \times 2,560 + 488 + 3,724 = 5,120 + 488 + 3,724 = 9,332 \quad [\checkmark]$$
$$\text{Distinct active cell-days} = 2,560 + 488 + 3,724 = 6,772 \quad [\checkmark]$$
