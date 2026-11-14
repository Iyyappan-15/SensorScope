# SensorScope: Final Release-Blocker Audit & Verification Report

**Project:** SensorScope — Cross-Sensor Active Fire Observation Calibration & Discrepancy Analysis  
**Repository:** `https://github.com/Iyyappan-15/SensorScope.git`  
**Target Local Commit:** `b53c686` (on branch `master`)  
**Remote Checkpoint Commit:** `e59bb49` (`pre-event-mvp-checkpoint`)  
**Audit Timestamp:** 2026-11-14T21:55:00+05:30  
**Eligibility Status:** **`ELIGIBILITY CLEARANCE PENDING`**  
**Push Authorization Status:** **HELD — Awaiting explicit user approval**

---

## 1. Executive Summary & Verification Matrix

All critical release-blocker checks have been systematically executed, diagnosed, independently reproduced, and verified against the live application runtime.

| Item | Target Requirement | Status | Verification Evidence |
|:---|:---|:---:|:---|
| **1. Diagnostic Resolution** | Resolve all runtime verification command failures | **PASS** | Root causes identified and resolved; `scripts/audit_calibration_flow.py` exited with code 0. |
| **2. Data Flow Isolation** | Strict cohort (`pairs_strict`, 2,554) separated from exploratory archive (`pairs`, 2,560) | **PASS** | Code trace in `data_loader.py` and `calibration_lab.py` confirms strict separation for all calibration models & scatterplots. |
| **3. Model C Equation** | Direct estimator verification (`intercept_`, `coef_`, `feature_names_in_`) | **PASS** | Exact parameters extracted: `intercept_ = 28.190453`, `coef_ = [0.2253, 1.0867, 2.3564]`. Independent MAE matches 26.1863 MW. |
| **4. Population Reconciliation** | Full audit of 14-row MODIS difference (8,472 archive vs. 8,458 strict) | **PASS** | All 14 records itemized by file, platform (10 Aqua, 4 Terra), date, and acquisition time via `scripts/audit_modis_discrepancy.py`. |
| **5. Terminology Accuracy** | Replace "Kharif" with "Strict November 1–10 calibration cohort" & "post-monsoon" | **PASS** | Full repository search & replace executed; population described as co-active cell/date/diurnal observations. |
| **6. Application Health** | Live Streamlit server HTTP response & 5-page rendering | **PASS** | Server responds HTTP 200 OK (`/_stcore/health`). All 5 pages active and visually inspected. |
| **7. Unit Test Suite** | Full automated regression test suite | **PASS** | **`10 passed in 4.86s`** (`pytest tests -v`). |
| **8. Git Status & Safety** | Clean Git history; no unauthorized push | **PASS** | No commits pushed; working tree preserved; checkpoint branch intact. |

---

## 2. Diagnosis and Resolution of Previous Verification Failures

During the preliminary check, interactive one-liner verification snippets exited with code 1. A complete post-mortem was conducted to identify the root causes:

### 2.1 Failure Post-Mortem
1. **Import Error (`ImportError: cannot import name 'load_or_generate_data'`):**
   - *Cause:* The function in `pages/data_loader.py` is named `load_data()`, not `load_or_generate_data()`.
   - *Resolution:* Corrected import to `from pages.data_loader import load_data`.
2. **Dataclass Attribute Access (`AttributeError: 'CalibrationResult' object has no attribute 'get'`):**
   - *Cause:* `CalibrationResult` is a Python `@dataclass`, not a dictionary.
   - *Resolution:* Accessed fields via standard dataclass attribute syntax (e.g., `cal['context'].val_metrics`).
3. **Module Path Resolution (`ModuleNotFoundError: No module named 'src.calibration'`):**
   - *Cause:* The module is located at `src/analysis/calibration.py`.
   - *Resolution:* Corrected import path or imported via `pages/data_loader.py`.
4. **Dynamic Feature Derivation (`KeyError: "['is_night'] not in index"`):**
   - *Cause:* In `pairs_strict`, the raw categorical column is `daynight` (`'D'` or `'N'`). In `src/analysis/calibration.py`, the binary feature `is_night` is engineered dynamically within `_build_features(df)` as `(df['daynight'] == 'N').astype(float)`.
   - *Resolution:* Created dedicated standalone audit script `scripts/audit_calibration_flow.py` that mirrors the exact feature pipeline.

### 2.2 Final Execution Evidence
Running `python scripts/audit_calibration_flow.py` completed with **exit code 0**:
```text
=== DATA LOADER EXPORT AUDIT ===
Keys in data: ['cal_results', 'combined', 'combined_assoc', 'disagree', 'grid_summary', 'modis', 'n_modis', 'n_viirs', 'pairs', 'pairs_strict', 'reliability', 'using_real_data', 'viirs']
data['is_synthetic']: None (Real data loaded)
data['pairs'] length: 2,560 (Exploratory archive)
data['pairs_strict'] length: 2,554 (Strict calibration cohort)
pairs_strict total: 2,554
2022 training partition: 1,312
2023 comparative evaluation partition: 1,242

=== INDEPENDENT RE-CALCULATION OF MODEL C PREDICTIONS & METRICS ===
Independent Train MAE:  30.4185 (matches stored 30.4185)
Independent Train RMSE: 43.2077 (matches stored 43.2077)
Independent Train Bias: -0.00% (matches stored -0.00%)
Independent Eval MAE:   26.1863 (matches stored 26.1863)
Independent Eval RMSE:  36.6653 (matches stored 36.6653)
Independent Eval Bias:  +8.06% (matches stored +8.06%)
```

---

## 3. Strict Calibration Data Flow & Population Isolation

The repository strictly separates two observational populations with distinct analytical purposes:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │             Raw FIRMS Ingestion (24 CSVs)               │
                  │         MODIS: 8,472 records · VIIRS: 33,853 records    │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
         ┌───────────────────────────┐                   ┌───────────────────────────┐
         │    Exploratory Archive    │                   │ Strict Calibration Cohort │
         │   (All Ingested Records)  │                   │  (Nov 1–10, 2022 & 2023)  │
         └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                       │                                               │
                       ▼                                               ▼
         ┌───────────────────────────┐                   ┌───────────────────────────┐
         │ 6,772 Diurnal Cell Obs    │                   │ 20 Synchronized Daily CSVs│
         │ (6,751 unique cell-dates) │                   │ (4 probe files excluded)  │
         │ 2,560 Co-Active Pairs     │                   │ 2,554 Co-Active Cell Obs  │
         │ 488 MODIS-only / 3,724 V-o│                   │ 1,312 Train / 1,242 Eval  │
         └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                       │                                               │
                       ▼                                               ▼
             Used Exclusively in:                            Used Exclusively in:
          • Overview Disagreement Breakdown              • Calibration Engine (Models A, B, C)
          • Disagreement Atlas Geospatial Maps           • Calibration Lab Performance Table
          • 9-Cell Sensitivity Matrix                    • Calibration Lab Before/After Plot
          • Fire Activity Calendar Baseline              • Empirical Error Envelopes (94.6%)
```

### Verification in Code:
- In `pages/data_loader.py` (lines 64–72): `pairs_strict` is derived by filtering `combined` strictly to `strict_dates` (Nov 1–10 in 2022 and 2023). The calibration engine `run_all_calibrations(pairs_strict)` receives only `pairs_strict`.
- In `pages/calibration_lab.py` (line 47): `pairs = data.get("pairs_strict", data["pairs"])` guarantees that all downstream calibration metrics, scorecards, and scatterplots use the strict 2,554 cohort.

---

## 4. Model C Estimator & Equation Verification

### 4.1 Estimator Parameters
Extracted directly from the fitted `LinearRegression` model object (`cal_results['context'].model_obj`):
- **Model Class:** `sklearn.linear_model.LinearRegression`
- **Features (`feature_names_in_`):** `['frp_viirs', 'count_viirs', 'is_night']`
- **Intercept ($\beta_0$):** `28.190453 MW`
- **Coefficients ($\beta_1, \beta_2, \beta_3$):**
  - $\beta_1$ (VIIRS FRP): `+0.225290`
  - $\beta_2$ (VIIRS Detection Count): `+1.086667`
  - $\beta_3$ (Is Night flag): `+2.356393`

### 4.2 Exact Mathematical Equation
$$\widehat{\text{FRP}}_{\text{MODIS\_ref}} = 28.19 + 0.225 \times \text{FRP}_{\text{VIIRS}} + 1.087 \times \text{Count}_{\text{VIIRS}} + 2.356 \times \text{Night}$$

- **Feature Order & Units:**
  1. `frp_viirs`: Summed observed VIIRS Fire Radiative Power per 0.1° cell-day ($MW$).
  2. `count_viirs`: Total number of VIIRS hotspot point detections in that cell-day (hotspot density).
  3. `is_night`: Binary overpass indicator ($1$ if Night pass, $0$ if Day pass).
- **Preprocessing:** No scaling or normalization is applied; features enter the regression in their natural physical units.
- **UI Rendering:** In `pages/calibration_lab.py` (line 175), the equation string is dynamically generated directly from `model_obj.intercept_` and `model_obj.coef_`, guaranteeing zero risk of manual transcription error.

### 4.3 Benchmark Metric Comparison (Strict November 1–10 Cohort)

| Model | Methodology | Train MAE (2022) | Eval MAE (2023) | Eval RMSE | Eval Bias % | Spearman $\rho$ | Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Model A: Identity** | Baseline (Raw VIIRS) | 40.28 MW | 30.9304 MW | 45.48 MW | +6.88% | 0.4654 | 🟢 Baseline |
| **Model B: Global RMA** | Reduced Major Axis | 34.93 MW | 27.2526 MW | 40.69 MW | -10.55% | 0.4654 | 🟢 Supported |
| **Model C: Context-Aware** | Predictor-side OLS | **30.42 MW** | **26.1863 MW** | **36.67 MW** | **+8.06%** | **0.4675** | 🟢 **Best Model** |

---

## 5. Source Population & 14-Record MODIS Reconciliation

An exhaustive audit of every CSV file in `data/raw/modis/` was conducted via `scripts/audit_modis_discrepancy.py` (exit code 0):

### 5.1 Platform Breakdown
- **Broad Exploratory Archive ($n=8,472$ records):**
  - Aqua: $8,294$ records ($97.90\%$)
  - Terra: $178$ records ($2.10\%$)
  - Total CSV files: 24 files
- **Strict November 1–10 Cohort ($n=8,458$ records):**
  - Aqua: $8,284$ records ($97.94\%$)
  - Terra: $174$ records ($2.06\%$)
  - Core synchronized daily CSV files: 20 files
- **Exact Difference:** $8,472 - 8,458 = 14$ records ($10$ Aqua, $4$ Terra).

### 5.2 Itemization of the 14 Excluded Records
The 14 records originate exclusively from 4 exploratory single-day API probe files downloaded outside the synchronized 10-day intensive study windows:

| File Name | Date | Time (UTC) | Latitude | Longitude | Platform | FRP (MW) | Day/Night | Reason for Exclusion |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| `MODIS_SP_2022-05-31_d1.csv` | 2022-05-31 | 06:07 | 32.1193 | 75.2161 | Terra | 93.3 | D | Exploratory spring probe date |
| `MODIS_SP_2022-05-31_d1.csv` | 2022-05-31 | 06:07 | 32.1237 | 75.1947 | Terra | 38.4 | D | Exploratory spring probe date |
| `MODIS_SP_2022-11-30_d1.csv` | 2022-11-30 | 08:40 | 29.6870 | 75.3998 | Aqua | 13.3 | D | Late-November probe date |
| `MODIS_SP_2022-11-30_d1.csv` | 2022-11-30 | 08:40 | 30.3290 | 74.6164 | Aqua | 100.2 | D | Late-November probe date |
| `MODIS_SP_2022-11-30_d1.csv` | 2022-11-30 | 08:40 | 30.3306 | 74.6302 | Aqua | 5.7 | D | Late-November probe date |
| `MODIS_SP_2022-11-30_d1.csv` | 2022-11-30 | 08:40 | 31.4863 | 75.6952 | Aqua | 10.7 | D | Late-November probe date |
| `MODIS_SP_2023-05-31_d1.csv` | 2023-05-31 | — | — | — | — | — | — | Zero records in pass |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 04:59 | 29.7241 | 75.7223 | Terra | 8.4 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 04:59 | 29.7257 | 75.7094 | Terra | 16.5 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 09:10 | 29.5832 | 74.4181 | Aqua | 14.5 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 09:10 | 29.7256 | 75.7132 | Aqua | 17.1 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 09:10 | 29.7295 | 75.7046 | Aqua | 18.4 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 09:10 | 30.3169 | 74.2276 | Aqua | 12.4 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 09:10 | 30.3554 | 74.3663 | Aqua | 14.8 | D | Late-November probe date |
| `MODIS_SP_2023-11-30_d1.csv` | 2023-11-30 | 21:15 | 29.7353 | 75.7136 | Aqua | 7.3 | N | Late-November probe date |

### 5.3 Terra Records in the Strict Calibration Cohort
The 20 core daily files in the strict calibration cohort contain **174 morning Terra records** ($2.06\%$). Because `build_grid_summary` aggregates standard FIRMS MODIS active fire products by grid-cell, day, and day/night pass, these 174 records contribute to the MODIS cell-day sums for those specific cells. When strictly filtering out Terra (`satellite == 'Aqua'` only), co-active observations drop from 2,554 to 2,472. SensorScope documents this transparently in `pages/methodology.py` and `README.md`.

---

## 6. Scientific Terminology Alignment

Every reference to the strict November 1–10 cohort across code, UI, and documentation has been reviewed and standardized:
1. **Replacement of "Kharif":** The phrase `Kharif` has been replaced with **`Strict November 1–10 calibration cohort`** when designating the calibration dataset.
2. **Seasonal Demarcation:** The term **`post-monsoon`** is used exclusively for the regional October–November seasonal grouping.
3. **Unit of Observation:** The 2,554 samples are explicitly defined as **`co-active cell/date/diurnal observations`** within 0.1° grid cells, not confirmed physical fire pairs.
4. **Evaluation Role:** November 2023 is described as a **`held-out comparative evaluation set`** across models, not an untouched multi-year final test set.

---

## 7. Application Health & Browser Verification

### 7.1 Server Process Status
- **Host/Port:** `http://localhost:8501/`
- **Health Check Endpoint:** `/_stcore/health`
- **Response:** `HTTP 200 OK`, body: `ok` (latency $< 10\text{ ms}$).

### 7.2 5-Page UI Inspection Summary

| Page | Header / Key Components | Observed State | Status |
|:---|:---|:---|:---:|
| **1. Overview** | Headline KPI Cards (1,312 / 1,242 / 2,554), Mapbox Hotspot Viewer, Observation Window dropdown | All metrics render cleanly; dropdown includes "Strict November 1–10 Cohort"; interactive map displays both point centroids and density surface. | **PASS** |
| **2. Disagreement Atlas** | Cross-sensor breakdown (2,560 both, 488 MODIS, 3,724 VIIRS), 9-cell sensitivity matrix | Breakdown cards display exact exploratory figures; 9-cell matrix caption explicitly discloses search neighbourhood; no render exceptions. | **PASS** |
| **3. Calibration Lab** | Population banner, Model C equation, Performance scorecard table, Before/After scatterplot | Banner confirms 2,554 strict observations; dynamic equation displays $28.19 + 0.225 \cdot \text{FRP} + 1.087 \cdot \text{Count} + 2.356 \cdot \text{Night}$; scatterplot renders green diamonds vs. blue circles vs. 1:1 dashed line. | **PASS** |
| **4. Fire Activity Calendar** | Monthly timeline, metric selector ("Summed FRP (MW)" vs "Detection count"), seasonal caption | Calibrated line is displayed only when FRP is selected and toggle is enabled; calibrated line is suppressed for detection count; regional burning seasons caption displayed. | **PASS** |
| **5. Methodology & Evidence** | 5 structured tabs, data sources table, 14-record MODIS reconciliation note, academic references | Tab navigation functional; full 14-row reconciliation table and platform breakdown visible; Li et al. (2018) reference verified. | **PASS** |

---

## 8. Automated Test Suite Results

Full pytest execution output (`pytest tests -v`):
```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.7.0
cachedir: .pytest_cache
rootdir: D:\hackathon\nasa\sensorscope
plugins: anyio-4.14.2
collecting ... collected 10 items

tests/test_calibration.py::test_reliability_abstention_on_sparse_data PASSED [ 10%]
tests/test_calibration.py::test_reliability_gate_green_threshold PASSED  [ 20%]
tests/test_calibration.py::test_input_domain_bounds_check PASSED         [ 30%]
tests/test_calibration.py::test_empirical_error_envelope_non_negative PASSED [ 40%]
tests/test_calibration.py::test_no_target_leakage_in_model_context PASSED [ 50%]
tests/test_calibration.py::test_temporal_subgroup_reliability_check PASSED [ 60%]
tests/test_pipeline.py::test_haversine_distance PASSED                   [ 70%]
tests/test_pipeline.py::test_normalize_schema_compliance PASSED          [ 80%]
tests/test_pipeline.py::test_association_candidate_logic PASSED          [ 90%]
tests/test_pipeline.py::test_cell_day_accounting_reconciliation PASSED   [100%]

============================= 10 passed in 4.86s ==============================
```

---

## 9. Git Repository State

```text
Current Branch: master
Local Commit:   b53c686 (fix(calibration): separate strict vs exploratory datasets, align README metrics, and update methodology documentation)
Remote Tracking: origin/master at 395d1ff
Checkpoint:     pre-event-mvp-checkpoint at e59bb49 (matched locally and remotely)
Working Tree:   Modified files prepared for review; NO unauthorized commits or pushes executed.
```

---

## 10. Verdict & Recommendation

- **Verdict:** **ALL 8 CRITICAL RELEASE-BLOCKER CHECKS HAVE PASSED.**
- **Recommendation:** Commit the terminology, population wording, and 14-row documentation updates to local Git, and await user review. **DO NOT PUSH** until explicit approval is granted.
