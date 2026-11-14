# 🛰️ SensorScope: Explainable MODIS–VIIRS Harmonization & Calibration Audit

> **Tagline:** *Two satellites see the same Earth differently. We explain why, measure the difference, and build a more reliable historical fire-activity record.*

[![Live App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://sensorscope.streamlit.app)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Iyyappan--15%2FSensorScope-181717.svg?logo=github)](https://github.com/Iyyappan-15/SensorScope)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![NASA FIRMS](https://img.shields.io/badge/data-NASA%20FIRMS%20SP-red.svg)](https://firms.modaps.eosdis.nasa.gov/)
[![Tests Passing](https://img.shields.io/badge/tests-10%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

### 🌐 Live Public Deployment
- 🔗 **Interactive Web Application:** **[https://sensorscope.streamlit.app](https://sensorscope.streamlit.app)**
- 💻 **Public GitHub Repository:** **[https://github.com/Iyyappan-15/SensorScope](https://github.com/Iyyappan-15/SensorScope)**
- 🏷️ **Pre-Event Checkpoint Branch:** **[pre-event-mvp-checkpoint](https://github.com/Iyyappan-15/SensorScope/tree/pre-event-mvp-checkpoint)**

---

## 🎯 The Real-World Problem

NASA has collected satellite active-fire observations for over two decades using two critical instruments:
- **MODIS (Terra & Aqua):** Nominal 1 km pixel resolution (2000–present)
- **VIIRS (Suomi-NPP & NOAA-20/21):** Nominal 375 m pixel resolution (2012–present)

Because MODIS and VIIRS have different spatial resolutions (1 km vs 375 m), differing observation timing, and distinct sensor detection characteristics, they produce differences in reported active-fire hotspots. Comparing raw hotspot counts across sensor transition periods risks confusing satellite instrument sensitivity with real-world changes in burning.

```
Long-Term Satellite Observation Transition:
  2000 ───────────── 2011 │ 2012 ────────────────────────── 2024
     [ MODIS Native ]     │     [ VIIRS Introduced ]
     (1 km nominal)       │     (375 m - sees smaller fires)
                          │
                          └──> Risk: Inconsistent measurements
                               confused with real burning trends
```

### 3 Core Distortions
1. **Inconsistent historical measurements:** Long-term fire trends mislead policy, land management, and emission inventories.
2. **Detection disparity:** The same burning region appears more active simply due to sensor sensitivity.
3. **Observation ambiguity:** A missing FIRMS record does not mean "zero fires" — it may reflect orbit gaps or cloud obstruction.

---

## 💡 SensorScope Solution & Core Innovation

Rather than naively merging hotspots or applying a black-box model everywhere, **SensorScope introduces an auditable, coverage-aware calibration transferability engine with an evidence-based reliability gate**:

> **Our Signature Differentiator — The Reliability Gate:**  
> The system evaluates local evidence on held-out historical data. If training evidence or overlap is insufficient, **it visibly abstains from producing an unsupported correction** and reports raw observations with explicit uncertainty rationales.

```
                  ┌──────────────────────────────────────────────┐
                  │          MODIS & VIIRS Observations          │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │             Disagreement Atlas               │
                  │  (Spatial Δ, FRP shifts, Day/Night, Seasons) │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       SensorShift Calibration Engine         │
                  │   Model A: Raw Identity (No correction)      │
                  │   Model B: Global Reduced Major Axis (RMA)   │
                  │   Model C: Predictor-Side OLS (FRP + Count)  │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                             ┌───────────────────────┐
                             │   RELIABILITY GATE    │
                             └───────────┬───────────┘
               ┌─────────────────────────┼────────────────────────┐
               ▼                         ▼                        ▼
       🟢 GREEN STATUS           🟡 YELLOW STATUS          🔴 RED STATUS
     Supported (Pilot)          Borderline Coverage     Insufficient Evidence
  Apply validated correction     Show caution banner       ABSTAIN from correction
   Empirical error envelope      Preserve raw values      Report missing evidence
```

---

## 🧪 Validated Empirical Results (Real NASA FIRMS Data)

Tested on real NASA FIRMS Standard Processing data over **Punjab & Haryana, India** (analytical rectangular bounding box `[73.8°E, 29.5°N, 77.5°E, 32.5°N]`):

### 1. Exploratory Archive Population (2022–2023 Pilot Ingestion)
- **Sensor-specific grid records:** 9,332
- **Diurnal cell observations (`grid_id`, `acq_date`, `daynight`):** 6,772 (6,655 Day, 117 Night)
- **Unique calendar cell-dates (`grid_id`, `acq_date`):** 6,751 (21 cell-dates observed in both Day and Night: $6,751 + 21 = 6,772$)
- **Co-active exploratory observations:** 2,560 (2,556 Day, 4 Night) | **MODIS-only:** 488 | **VIIRS-only:** 3,724
- **Raw MODIS records:** 8,472 (8,294 Aqua [97.9%], 178 Terra [2.1%]) across 24 CSV files.

### 2. Strict Scientific Calibration Cohort (Strict November 1–10 Calibration Cohort)
Evaluated strictly on the synchronized November 1–10 agricultural burning window across 20 core daily files ($N=2,554$ strict co-active cell/date/diurnal observations; 1,312 training and 1,242 comparative-evaluation observations):
- **Raw MODIS records in strict cohort:** 8,458 (8,284 Aqua [97.9%], 174 Terra [2.1%]) across 20 files.
- **The 14-record MODIS difference ($8,472 - 8,458 = 14$):** Exactly 14 records (10 Aqua, 4 Terra) originate from 4 exploratory single-day API probe files outside the Nov 1–10 window (`2022-05-31_d1`: 2 Terra; `2022-11-30_d1`: 4 Aqua; `2023-05-31_d1`: 0; `2023-11-30_d1`: 6 Aqua + 2 Terra) and are excluded from the strict calibration cohort.
- **Training partition (Nov 1–10, 2022):** 1,312 strict co-active cell/date/diurnal observations
- **Comparative evaluation partition (Nov 1–10, 2023):** 1,242 strict co-active cell/date/diurnal observations

| Model | Methodology | Train MAE | Comparative Eval MAE | Eval Bias % | Spearman $\rho$ | Reliability Status |
|---|---|---|---|---|---|:---:|
| **Model A: Identity** | Raw VIIRS (No correction) | 40.28 MW | 30.9304 MW | +6.88% | 0.465431 | 🟢 Baseline |
| **Model B: Global RMA** | Reduced Major Axis ($\text{slope}=0.80528$, $\text{intercept}=1.4247\text{ MW}$) | 34.93 MW | 27.2526 MW | -10.55% | 0.465432 | 🟢 Supported |
| **Model C: Context-Aware** | Predictor-side OLS (VIIRS FRP + Count + Night) | 30.42 MW | **26.1863 MW** | **+8.06%** | **0.467452** | 🟢 **Best Model** |

> **Scientific Finding:** On the strict November 1–10 calibration cohort ($N=2,554$ co-active cell/date/diurnal observations), context-aware calibration reduces comparative evaluation period Mean Absolute Error from **30.93 MW down to 26.19 MW** (an error reduction of 15.3% over identity) without target leakage. In 5-fold date-grouped cross-validation across acquisition dates, pooled out-of-fold MAE is **31.5128 MW**. Descriptive empirical residual envelopes achieve **94.6% coverage** (1,175/1,242) on the held-out November 2023 comparative evaluation period.

*Methodological Note: November 2023 was evaluated as a comparative evaluation period across models, not an untouched multi-year final test set. The 2,554 observations represent co-active cell/date/diurnal observations within 0.1° grid cells, not confirmed physical fire pairs. Regional calibration results do not establish independent cell-level validation for every individual grid cell.*


---

## 🖥️ 5-Screen Interactive Architecture

1. **🏠 Overview:** Regional KPI cards, interactive Mapbox satellite hotspot viewer, monthly time series, and overall reliability stats.
2. **🗺️ Disagreement Atlas:** Geospatial divergence maps ($\Delta \text{count}$, $\Delta \text{FRP}$), day vs. night divergence, candidate association status, and a full 9-cell spatial/temporal sensitivity matrix.
3. **🔬 Calibration Lab:** Paired scatter plots, 1:1 reference comparisons, before-and-after calibration shifts, and high-precision model evaluation scorecards.
4. **📅 Fire Activity Calendar:** Raw sensor-specific observations, calibrated estimates with descriptive empirical error envelopes where supported, and clearly identified cases where calibration is unavailable.
5. **📋 Methodology & Evidence:** Academic citations, processing assumptions, limitations, and CSV data export buttons.

---

## 🚀 Quickstart & Setup

### 1. Clone & Install
```bash
git clone https://github.com/Iyyappan-15/SensorScope.git
cd sensorscope
pip install -r requirements.txt
```

### 2. Configure Environment (Optional for Live API Downloads)
Copy `.env.example` to `.env` and insert your NASA FIRMS `MAP_KEY`:
```env
FIRMS_MAP_KEY=your_key_here
AOI_BBOX=73.8,29.5,77.5,32.5
DATA_START_YEAR=2022
DATA_END_YEAR=2024
```
*(If `.env` is omitted, the application automatically runs in **no-API sample-data mode**).*

### 3. Run the App
```bash
streamlit run app.py
```

### 4. Run Pytest Suite
```bash
pytest tests -v
```

---

## 🔬 Scientific Foundations & References

- **Li, F., Zhang, X., Kondragunta, S., & Csiszar, I. (2018).** *Comparison of Fire Radiative Power Estimates From VIIRS and MODIS Observations.* Journal of Geophysical Research: Atmospheres, 123, 4545–4563. [DOI: 10.1029/2017JD027823](https://doi.org/10.1029/2017JD027823)
- **Sofiev, M., & Kouznetsov, R. (2026).** *Observation operator and detection limits for MODIS and VIIRS Fire Radiative Power products.* Geoscientific Model Development, 19, 10123–10145. [DOI: 10.5194/gmd-19-10123-2026](https://doi.org/10.5194/gmd-19-10123-2026)
- **NASA FIRMS (Fire Information for Resource Management System):** MODIS Collection 6.1 SP & VIIRS S-NPP Collection 2 SP. [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/)

---

## ⚖️ License, Data Attribution & Disclaimer
- **Software License:** MIT License. See [LICENSE](LICENSE). This license applies strictly to the SensorScope software source code written by the team.
- **NASA FIRMS & LANCE Attribution & Disclaimer:** We acknowledge the use of data from NASA's Fire Information for Resource Management System (FIRMS) ([earthdata.nasa.gov/firms](https://earthdata.nasa.gov/firms)), part of the Land, Atmosphere Near real-time Capability for EOS (LANCE). NASA active fire products (MODIS Collection 6.1 SP and VIIRS Collection 2 SP) are provided under NASA Open Data policies. NASA makes no warranties, express or implied, regarding the data's accuracy, completeness, or fitness for any particular purpose. Standard Processing (SP) science data are produced by the MODIS Adaptive Processing System (MODAPS) and Land SIPS.
- **AI Tool Disclosure:** In accordance with NASA Space Apps Challenge disclosure rules, AI tools were utilized during project preparation and development:
  - **ChatGPT (OpenAI):** Utilized for challenge background research, literature analysis (*Li et al. 2018*, *Sofiev & Kouznetsov 2026*), competitive review, and proposal synthesis.
  - **Google Antigravity / Gemini (DeepMind):** Utilized as an agentic coding assistant for code scaffolding, automated testing, data pipeline integration, and documentation formatting.
  - All scientific claims, mathematical definitions, data processing logic, and validation results were independently reviewed, audited, and verified by the team.
