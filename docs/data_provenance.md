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

## 5. Mathematical Accounting Reconciliation: Diurnal vs Calendar Cell-Days

The apparent counting relationships are reconciled with precision:

### A. Level of Granularity Definitions
1. **Sensor-Specific Observations (`grid_summary` table): 9,332 rows**
   - Unit of observation: `(grid_id, acq_date, daynight, sensor)`
2. **Diurnal Grid-Cell Observations (`disagreement` table): 6,772 rows**
   - Unit of observation: `(grid_id, acq_date, daynight)`
   - Day observations (`daynight == 'D'`): **6,655**
   - Night observations (`daynight == 'N'`): **117**
   - Sum: $6,655 + 117 = 6,772$
3. **Calendar Grid-Cell-Days (pure date grouping): 6,751 unique `(grid_id, acq_date)`**
   - Exactly **21 grid-cell-dates** had burning activity detected during both daytime and nighttime passes.
   - Set-theoretic identity:
     $$\text{Unique (cell, date)} = \text{Day} + \text{Night} - \text{Both} = 6,655 + 117 - 21 = 6,751$$
     $$\text{Diurnal Observations} = 6,751 + 21 = 6,772$$

### B. Sensor Activity Breakdown (at Diurnal Unit Level: 6,772 rows)
- **Co-active pairs (`has_both == True`):** **2,560**
  - Daytime co-active pairs: **2,556**
  - Nighttime co-active pairs: **4**
  - Exactly 2 grid cells had co-active detections during both day and night on the same date ($2,558$ unique `(grid_id, acq_date)` pairs).
- **MODIS-only diurnal observations (`modis_only == True`):** **488** (488 Day, 0 Night)
- **VIIRS-only diurnal observations (`viirs_only == True`):** **3,724** (3,611 Day, 113 Night)

### C. Mathematical Reconciliation Identity
$$\text{Sensor-specific rows} = 2 \times 2,560 + 488 + 3,724 = 5,120 + 488 + 3,724 = \mathbf{9,332} \quad [\checkmark]$$
$$\text{Diurnal cell observations} = 2,560 + 488 + 3,724 = \mathbf{6,772} \quad [\checkmark]$$
$$\text{Unique calendar cell-days} = 6,772 - 21 = \mathbf{6,751} \quad [\checkmark]$$

