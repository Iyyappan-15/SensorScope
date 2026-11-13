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
## Data Sources

### Primary data
| Product | Sensor | Platform | Collection | Resolution | Period |
|---------|--------|----------|------------|------------|--------|
| MODIS Active Fire | MODIS | Aqua & Terra | C6.1 SP | 1 km nominal | 2000–present |
| VIIRS Active Fire | VIIRS | Suomi-NPP | C2 SP | 375 m nominal | 2012–present |

**Source:** [NASA FIRMS — Fire Information for Resource Management System](https://firms.modaps.eosdis.nasa.gov)

We use **Standard Processing (SP)** data — the internally consistent, well-calibrated record
intended for scientific analysis. SP data has a ~3-month availability lag compared to
Near-Real-Time (NRT) data. We do not mix SP and NRT in the same analysis.

### Study region
**Punjab & Haryana, India**
- Bounding box: 73.8°E – 77.5°E, 29.5°N – 32.5°N
- Selected for: high agricultural burning intensity, clear seasonal signal,
  well-documented ground-truth burning calendar
- **Pilot study only** — results are not generalizable without further validation

### Platforms analysed (pilot)
- **MODIS Aqua** (primary — similar overpass time to Suomi-NPP)
- **VIIRS Suomi-NPP** (primary comparison partner)

Terra MODIS and NOAA-20/21 VIIRS are excluded from the pilot calibration
to maintain a consistent platform pair.
        """)

        # Data provenance
        st.divider()
        st.markdown("### Data provenance & Observation Accounting")
        modis = data["modis"]
        viirs = data["viirs"]

        col1, col2 = st.columns(2)
        col1.metric("MODIS records loaded", f"{len(modis):,}")
        col2.metric("VIIRS records loaded", f"{len(viirs):,}")

        st.markdown("""
| Unit Level | Count | Definition & Discrepancy Reconciliation |
|:---|:---:|:---|
| **Sensor-Specific Rows** | **9,332** | `(grid_id, acq_date, daynight, sensor)` entries in `grid_summary` ($2 \\times 2,560 + 488 + 3,724 = 9,332$) |
| **Diurnal Cell Observations** | **6,772** | `(grid_id, acq_date, daynight)` entries in `disagreement` (6,655 Day, 117 Night) |
| **Unique Calendar Cell-Days** | **6,751** | Unique `(grid_id, acq_date)` combinations ($6,655 + 117 - 21\\text{ both} = 6,751$) |
| **Co-Active Calibration Pairs** | **2,560** | Both sensors detected fire in cell on that pass (2,556 Day, 4 Night) |
| **MODIS-Only Observations** | **488** | MODIS detected fire, VIIRS reported none (488 Day, 0 Night) |
| **VIIRS-Only Observations** | **3,724** | VIIRS detected fire, MODIS reported none (3,611 Day, 113 Night) |
        """)


        if data["using_real_data"]:
            if not modis.empty:
                files = modis["source_file"].unique()
                col1.caption(f"From {len(files)} files")
            if not viirs.empty:
                files = viirs["source_file"].unique()
                col2.caption(f"From {len(files)} files")
        else:
            st.warning(
                "Currently using **synthetic demonstration data**. "
                "Download real NASA data with the data download script before submission."
            )

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
OLS regression with additional features:
$$\\hat{FRP}_{MODIS} = f(FRP_{VIIRS},\\ \\text{month\\_sin},\\ \\text{month\\_cos},\\ \\text{is\\_night})$$

Cyclic month encoding preserves seasonal continuity.

### Chronological split (no data leakage)
| Split | Period | Purpose |
|-------|--------|---------|
| Training | 2022 | Model fitting |
| Validation | 2023 | Hyperparameter selection & reliability gate |
| Test | 2024 | Final honest evaluation |

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
