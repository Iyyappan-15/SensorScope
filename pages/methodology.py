"""Page 5 — Methodology & Evidence: scientific basis, limitations, citations."""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pages.data_loader import load_data, data_source_banner


def render() -> None:
    st.title("📋 Methodology & Evidence")
    st.caption("Scientific basis, processing assumptions, limitations and data provenance")

    data = load_data()
    data_source_banner(data["using_real_data"])

    # ── Tabs ───────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📡 Data Sources",
        "⚙️ Processing",
        "📐 Calibration",
        "⚠️ Limitations",
        "📚 References",
    ])

    with tab1:
        st.markdown("""
## Data Sources & Provenance

### Primary NASA FIRMS Data Products
| Product Identifier | Sensor | Platform | Collection | Nominal Resolution | Product Coverage | Pilot Role |
|:---|:---|:---|:---|:---|:---|:---|
| `MODIS_SP` | MODIS | Aqua | C6.1 SP | 1 km at nadir | July 2002 – present | **Selected** (Primary baseline) |
| `MODIS_SP` | MODIS | Terra | C6.1 SP | 1 km at nadir | Nov 2000 – present | *Excluded from calibration* (Morning orbit) |
| `VIIRS_SNPP_SP` | VIIRS | Suomi-NPP | C2 SP | 375 m at nadir | Jan 20, 2012 – present | **Selected** (Primary comparison) |
| `VIIRS_NOAA20_SP` | VIIRS | NOAA-20 / JPSS-1 | C2 SP | 375 m at nadir | 2018 – present | *Excluded from pilot* |
| `VIIRS_NOAA21_SP` | VIIRS | NOAA-21 / JPSS-2 | C2 SP | 375 m at nadir | 2023 – present | *Excluded from pilot* |

**Source:** [NASA FIRMS — Fire Information for Resource Management System](https://firms.modaps.eosdis.nasa.gov)

### Standard Processing (SP) Quality Standard
We use **Standard Processing (SP)** data because it provides an internally consistent, science-quality record for historical analysis. SP products typically become available after approximately 2–3 months, although processing delays can sometimes extend to 5 months. Near-Real-Time (NRT) and SP records are not mixed within this analysis.

### Study Region
**Punjab & Haryana, India**
- **Bounding coordinates:** 73.8°E – 77.5°E, 29.5°N – 32.5°N
- **Selection rationale:** Selected for its regional agricultural crop-residue burning relevance, documented seasonal burning patterns and availability of historical satellite observations. Published seasonal crop-residue burning references provide contextual interpretation, not pixel-level ground truth.
- **Pilot boundary:** Pilot study only — results are not generalizable to other global biomes or fuel complexes without local recalibration.

### Platform Selection & Overpass Dynamics
- **Selected Pilot Pair:** **Aqua MODIS C6.1 SP** and **Suomi-NPP VIIRS C2 SP** were selected as the consistent satellite comparison pair.
- **Excluded Platforms:** Terra MODIS (morning overpass ~10:30 local time), NOAA-20 VIIRS, and NOAA-21 VIIRS were excluded from the calibration engine to maintain orbital and observation-time consistency.
- **Overpass Timing Note:** Aqua MODIS and Suomi-NPP VIIRS share afternoon sun-synchronous orbits, but actual acquisition times vary continuously due to differing orbital swaths. Time differences are evaluated empirically from observation timestamps rather than assumed to be identical.
        """)

        # ── Data-Processing Scope & Flow ──────────────────────────────────────
        st.divider()
        st.markdown("### 🔄 Data-Processing Scope & Pipeline Flow")
        st.markdown("""
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. Raw NASA FIRMS SP CSVs                                                       │
│    • Aqua MODIS C6.1 SP (8,294 records) + Suomi-NPP VIIRS C2 SP (33,853 records)│
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 2. Normalization & Quality Assurance                                            │
│    • Coordinate bounds [29.5°–32.5°N, 73.8°–77.5°E], UTC datetime, native conf. │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 3. 0.1° Geographic Grid Aggregation (~11 km)                                   │
│    • Diurnal pass separation (Day/Night), cell detection counts, and summed FRP │
│    • 6,772 diurnal cell observations across 6,751 unique calendar cell-dates    │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 4. Co-Active Cell-Day Pairing (Strict Kharif Peak Window)                       │
│    • Training (Nov 1–10, 2022): N = 1,312 pairs                                 │
│    • Evaluation (Nov 1–10, 2023): N = 1,242 pairs | Total strict N = 2,554      │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 5. Calibration Engine & Reliability Gate                                        │
│    • Model C (Context OLS): held-out MAE = 26.19 MW (+8.1% validation bias)     │
│    • Reliability Gate: In-domain (Green) / Subgroup Caution (Yellow) / Abstain  │
└─────────────────────────────────────────────────────────────────────────────────┘
```
        """)

        # ── Data provenance & Observation Accounting ──────────────────────────
        st.divider()
        st.markdown("### 📊 Data Provenance & Observation Accounting")
        modis = data["modis"]
        viirs = data["viirs"]

        col1, col2 = st.columns(2)
        col1.metric("MODIS Records Loaded", f"{len(modis):,}", "8,294 Aqua · 178 Terra")
        col2.metric("VIIRS Records Loaded", f"{len(viirs):,}", "33,853 Suomi-NPP")

        st.markdown("#### Complete Exploratory Archive Accounting (2022–2023 Pilot Ingestion)")
        st.markdown("""
| Unit Level | Count | Definition & Discrepancy Reconciliation |
|:---|:---:|:---|
| **Sensor-Specific Rows** | **9,332** | `(grid_id, acq_date, daynight, sensor)` entries in `grid_summary` ($2 \\times 2,560 + 488 + 3,724 = 9,332$) |
| **Diurnal Cell Observations** | **6,772** | `(grid_id, acq_date, daynight)` entries in `disagreement` (6,655 Day, 117 Night) |
| **Unique Calendar Cell-Days** | **6,751** | Unique `(grid_id, acq_date)` combinations ($6,655 + 117 - 21\\text{ both} = 6,751$) |
| **Co-Active Exploratory Diurnal Observations** | **2,560** | Both sensors detected fire in cell on that pass (2,556 Day, 4 Night; includes exploratory API-probe dates) |
| **MODIS-Only Observations** | **488** | MODIS-only: no corresponding VIIRS detection recorded in the same diurnal grid-cell aggregation (488 Day, 0 Night) |
| **VIIRS-Only Observations** | **3,724** | VIIRS-only: no corresponding MODIS detection recorded in the same diurnal grid-cell aggregation (3,611 Day, 113 Night) |
        """)

        st.markdown("#### Strict Scientific Evaluation Population (Strict Nov 1–10 Kharif Peak)")
        st.markdown("""
| Cohort / Split | Dates | Co-Active Observations | Role in Scientific Evaluation |
|:---|:---|:---:|:---|
| **2022 Training Window** | Nov 1–10, 2022 | **1,312** | Model parameter estimation & date-grouped cross-validation |
| **2023 Evaluation Window** | Nov 1–10, 2023 | **1,242** | Held-out comparative evaluation (MAE = 26.19 MW, bias = +8.1%) |
| **Total Strict Pilot Population** | *Both Nov windows* | **2,554** | Strict Kharif peak observations (API-probe dates excluded) |
        """)

        if data["using_real_data"]:
            if not modis.empty and not viirs.empty:
                st.caption(
                    "📁 **Source Files Audit:** MODIS ingested across 23 non-empty CSV files "
                    "(8,294 Aqua records [97.9%], 178 Terra records [2.1%]); "
                    "VIIRS ingested across 24 CSV files (33,853 Suomi-NPP records [100.0%]). "
                    "Terra records in exploratory files are excluded from the Aqua–VIIRS calibration pipeline."
                )
        else:
            st.warning(
                "Currently using **synthetic demonstration data**. "
                "Download real NASA data with the data download script before submission."
            )

        # ── Key Data Limitations ──────────────────────────────────────────────
        st.divider()
        st.markdown("### ⚠️ Key Data Limitations")
        st.markdown(r"""
- **Thermal Anomalies, Not Ground Truth:** NASA FIRMS active-fire detections represent satellite-observed thermal radiometric anomalies, not field-verified wildfire or burn perimeter events.
- **Footprint Enlargement:** Nominal pixel resolution (375 m for VIIRS, 1 km for MODIS) applies at nadir. At off-nadir scan angles, geometric projection expands the actual ground footprint substantially.
- **Overpass Asynchrony:** Aqua and Suomi-NPP orbits do not coincide exactly in time; observed orbital time differences ($\Delta t \approx 1.5\text{--}13.4\text{ min}$) capture real-world agricultural fire growth and decay.
- **Analytical Bounding Box:** The study bounding box ($73.8^\circ\text{--}77.5^\circ\text{E}, 29.5^\circ\text{--}32.5^\circ\text{N}$) represents an analytical rectangular envelope, not an administrative state boundary.
- **Domain-Specific Validity:** Harmonization parameters and empirical error envelopes are valid strictly for the evaluated pilot conditions (Punjab & Haryana, post-monsoon Kharif peak) and must be recalibrated for other ecosystems.
        """)

    with tab2:
        st.markdown("""
## Processing pipeline

### Step 1 — Normalization
Raw FIRMS CSV files are parsed into a common internal schema preserving all original values:
- `latitude`, `longitude`, `acq_date`, `acq_time` (UTC), `frp_mw`
- `confidence_raw` — the original native confidence value (not converted to a common scale)
- `daynight`, `scan`, `track`, `satellite`, `source_file`

Native confidence scales for MODIS and VIIRS differ and are **not** combined into a
single probability score without a validated crosswalk.

### Step 2 — Spatial grid
Detections are aggregated into a **0.1° × 0.1° analysis grid** (≈ 11 km × 11 km at the pilot latitude).
This is an engineering choice to create a common spatial reference — it is not a scientifically
prescribed universal resolution.

The grid size was selected to be:
- Large enough to associate nearby MODIS (1 km) and VIIRS (375 m) detections
- Small enough to preserve meaningful spatial variation across the study region

**Sensitivity note:** Results should be tested against a finer (0.05°) and coarser (0.2°) grid.

### Step 3 — Temporal grouping
Detections are grouped by UTC acquisition date and day/night flag.
Day and night observations are kept separate throughout the analysis.

### Step 4 — Candidate association
For the association analysis, records are compared using:
- **Temporal window:** ±15 minutes (also tested: ±5 and ±30 minutes)
- **Spatial tolerance:** 11 km (≈ 1 MODIS pixel diagonal + buffer)
- **Many-to-many matching** — one MODIS pixel may associate with multiple VIIRS pixels

**Important:** These are *candidate* associations, not confirmed fire identity.
An unmatched record does not automatically imply that the other sensor missed a real fire.

### Step 5 — Disagreement metrics
Per grid-cell-day disagreement:
- Δ count = VIIRS count − MODIS count
- Δ FRP = VIIRS FRP sum − MODIS FRP sum

These are differences in *reported measurements*, not estimates of differences in *true fire activity*.
        """)

    with tab3:
        st.markdown("""
## Calibration methodology

### Scientific basis
Our calibration methodology follows **Li et al. (2018)** who studied MODIS–VIIRS FRP
comparison using Reduced Major Axis (RMA) regression — a symmetric regression method
appropriate when both variables contain measurement error.

We also use findings from **Sofiev & Kouznetsov (2026)** regarding detection-limit
variation with observation conditions.

### Three models

**Model A — Identity (baseline)**
No correction applied. VIIRS FRP used directly.
Equivalent to assuming sensors are perfectly comparable.

**Model B — Global RMA calibration**
Reduced Major Axis regression across all matched pairs:
$$\\hat{FRP}_{MODIS} = a + b \\cdot FRP_{VIIRS}$$

RMA slope: $b = \\text{std}(FRP_{MODIS}) / \\text{std}(FRP_{VIIRS}) \\times \\text{sign}(r)$

**Model C — Context-aware calibration**
OLS multi-feature linear regression utilizing strictly predictor-side observations:
$$\\hat{FRP}_{MODIS} = \\beta_0 + \\beta_1 \\cdot FRP_{VIIRS} + \\beta_2 \\cdot Count_{VIIRS} + \\beta_3 \\cdot Is\\_Night$$

Features include summed VIIRS FRP (MW), cluster detection count, and a binary day/night flag ($1$ if Night, $0$ if Day). Zero-variance seasonal features (such as cyclic month in a single-season Kharif pilot) are excluded to maintain statistical validity.

### Split Design & Evaluation Strategy
| Split / Cohort | Window | Co-Active Pairs | Purpose & Evaluation Role |
|---|---|:---:|---|
| **Training Split** | Nov 1–10, 2022 | **1,312** | Model parameter estimation & 5-fold date-grouped cross-validation |
| **Held-Out Evaluation Split** | Nov 1–10, 2023 | **1,242** | Held-out comparative model evaluation & Reliability Gate threshold assessment |

*Methodological Note:* November 2023 was used for comparative model evaluation across Models A, B, and C; cross-validation across acquisition dates is performed via GroupKFold (unweighted mean fold MAE = 32.01 MW). The pilot archive focuses on the 2022 and 2023 Kharif agricultural burning windows.

### Reliability gate
The reliability gate operates independently of model training.
A trained model may still receive a **red** (abstain) status if:
- Fewer than 20 paired observations exist for the target region
- Validation bias exceeds ±15%
- Input conditions fall outside the training distribution

| Status | Condition | Action |
|--------|-----------|--------|
| 🟢 Green | ≥50 pairs AND validation bias ≤±15% | Show calibrated estimate |
| 🟡 Yellow | 20–50 pairs OR borderline validation | Show with caution warning |
| 🔴 Red | <20 pairs OR out-of-domain | Show raw data only |

### Calibration scope
The calibration operates on **paired grid-cell samples** where both sensors reported activity.
It does **not** correct:
- VIIRS-only detections (fires MODIS did not detect)
- MODIS-only detections
- Coverage gaps

Unmatched detections are shown as a separate layer, not corrected.
        """)

    with tab4:
        st.markdown("""
## Important limitations

### 1. Missing observation ≠ zero detection
FIRMS CSV files contain *detected* hotspots only.
A missing record may mean:
- The satellite did not observe that location on that day
- Cloud cover prevented detection
- The fire was below the detection threshold for that sensor

**We do not interpret missing records as zero fire activity.**

### 2. Calibration scope
Our calibration operates on **co-located, contemporaneous paired observations** only.
This is a subset of all observations:
- Pairs require both sensors to report activity in the same grid cell on the same day
- Sparse contemporaneous matches are expected (following Li et al. 2018 who found
  only ~1 overlapping day per 8 days in some regions)
- The calibration relationship learned from pairs may not hold for single-sensor observations

### 3. Detection limits (Sofiev & Kouznetsov 2026)
Detection thresholds vary with:
- Pixel size (MODIS 1 km >> VIIRS 375 m)
- Observation angle (nadir vs. side view)
- Daytime vs. nighttime conditions
- Cloud cover and atmospheric conditions

A complete cloud-aware correction would require Level-2 satellite products with
observation flags and cloud masks — not available in FIRMS hotspot CSVs.

### 4. Temporal coverage
SP data for 2022–2024 may have a ~3-month lag for recent months.
The pilot analysis should be treated as a methodological demonstration,
not a complete historical record.

### 5. Spatial scale
The 0.1° analysis grid is an engineering choice.
Results at different scales may differ.

### 6. Regional scope
Results from Punjab & Haryana cannot be automatically applied to other regions
with different vegetation types, burning conditions, or cloud climatology.
        """)

    with tab5:
        st.markdown("""
## References

**Li, F., Zhang, X., Kondragunta, S., & Csiszar, I. (2018).**
Comparison of Fire Radiative Power Estimates From VIIRS and MODIS Observations.
*Journal of Geophysical Research: Atmospheres*, 123, 4545–4563.
[https://doi.org/10.1029/2017JD027823](https://doi.org/10.1029/2017JD027823)

> This study informed our use of Reduced Major Axis regression for FRP comparison
> and our understanding of how the MODIS–VIIRS relationship varies with scale and ecosystem.

---

**Sofiev, M., & Kouznetsov, R. (2026).**
Observation operator and detection limits for MODIS and VIIRS Fire Radiative Power products.
*Geoscientific Model Development*, 19, 10123–10145.
[https://doi.org/10.5194/gmd-19-10123-2026](https://doi.org/10.5194/gmd-19-10123-2026)

> This study informed our understanding of detection-limit variation with observation
> conditions and the importance of accounting for geometry in fire satellite comparisons.

---

**NASA FIRMS (Fire Information for Resource Management System)**
[https://firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov)

> MODIS SP Collection 6.1 and VIIRS S-NPP SP Collection 2 active fire data products.

---

**AI tools disclosure**
This project was developed with AI coding assistance (Google Antigravity / Gemini).
All scientific claims, model choices and validation methodology were reviewed by the team.
Synthetic demonstration data is clearly labelled and not mixed with real data in any analysis.
        """)

        # Downloadable data export
        st.divider()
        st.subheader("📥 Export")
        col1, col2 = st.columns(2)

        disagree = data["disagree"]
        if not disagree.empty:
            csv_disagree = disagree.to_csv(index=False)
            col1.download_button(
                "⬇️ Download disagreement dataset",
                data=csv_disagree,
                file_name="sensorscope_disagreement.csv",
                mime="text/csv",
            )

        reliability = data["reliability"]
        if not reliability.empty:
            csv_rel = reliability.to_csv(index=False)
            col2.download_button(
                "⬇️ Download reliability table",
                data=csv_rel,
                file_name="sensorscope_reliability.csv",
                mime="text/csv",
            )
