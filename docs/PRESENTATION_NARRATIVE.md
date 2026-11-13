# SensorScope — Presentation Script & Slide Structure

**Target Audience:** NASA Space Apps Challenge Judges, Remote Sensing Researchers & Land Managers  
**Presentation Formats Supported:** 7-Slide Deck OR Short Video Walkthrough  

---

## 📽️ 7-Slide Presentation Structure

### Slide 1: Title & The Core Problem
- **Headline:** Two Satellites See the Same Earth Differently.
- **The Observation Gap:**
  - MODIS (1 km) provides 20+ years of historical baseline observations (2000–present).
  - VIIRS (375 m) provides finer spatial resolution and detects smaller, lower-intensity fires (2012–present).
- **The Core Scientific Trap:**
  *MODIS and VIIRS have different spatial resolutions and detection characteristics, which can produce inconsistent fire-activity measurements.*
  A land manager looking at post-2012 data risks confusing instrument sensitivity with an actual surge in real-world burning.

### Slide 2: The Data Disagreement Atlas
- **The Question:** Where and under what conditions do the instruments diverge?
- **Empirical Demonstration (Punjab & Haryana Agricultural Belt):**
  - In our real NASA FIRMS dataset (Nov 1–10, 2022 & 2023):
    - **9,332** sensor-specific grid records
    - **6,772** distinct active cell-days ($0.1^\circ$ geographic grid)
    - **2,560** co-active cell-days
    - **3,724** VIIRS-only cell-days vs. **488** MODIS-only cell-days
- **The Takeaway:** VIIRS detects widespread low-intensity agricultural stubble fires ($FRP < 10\text{ MW}$) that MODIS's 1 km footprint averages out.

### Slide 3: Cross-Sensor Association & Orbital Physics
- **The Sensitivity Finding:**
  - Aqua and Suomi-NPP share afternoon sun-synchronous orbits, but their actual overpasses vary continuously (observed mean delta-t ranges from 1.5 to 13.4 minutes).
  - Candidate matches scale strongly with tolerance thresholds (6.6% at 5 min / 5 km up to 51.2% at 30 min / 20 km).
- **The Scientific Boundary:**
  Candidate associations are exploratory observation opportunities, *not* confirmed ground-truth single fire events.

### Slide 4: SensorShift Calibration Engine
- **Three Progressive Models Tested on Held-Out Future Data (Train: Nov 2022 -> Held-Out Test: Nov 2023):**
  1. **Model A (Raw Identity Baseline):** MAE = 30.89 MW, Spearman $\rho = 0.4653$
  2. **Model B (Global RMA Regression):** MAE = 27.22 MW, Spearman $\rho = 0.4653$
  3. **Model C (Context-Aware Predictor-Side OLS):** MAE = **26.22 MW**, Spearman $\rho = \mathbf{0.4674}$
- **Predictor Integrity:** Zero target leakage; uses only inference-time features ($FRP_{\text{VIIRS}}$, hotspot cluster density).

### Slide 5: The Signature Innovation — The Reliability Gate
- **The Philosophy:** *Knowing when to calibrate, and having the scientific integrity to abstain when evidence is insufficient.*
- **The Traffic Light Gate:**
  - 🟢 **Green (Reliable in evaluated pilot conditions):** $\ge 50$ co-active cell-days, held-out validation bias $\le \pm 15\%$, and inputs in-domain.
  - 🟡 **Yellow (Use with caution):** $20 \le N < 50$ co-active cell-days or borderline validation error.
  - 🔴 **Red (Abstain):** $< 20$ cell-days or inputs outside historical training distribution ($Q_{0.01} - Q_{0.99}$).
- **The Demonstration Climax:** Show a cell with insufficient data where the system refuses to produce a fictitious correction and preserves the raw record.

### Slide 6: Historical Fire Activity Calendar
- **Transparent Multi-Layer View:**
  - Raw sensor-specific observations (MODIS native vs. VIIRS native).
  - Supported calibrated estimates with descriptive empirical error envelopes ($e_{0.05} = -48.5\text{ MW}, e_{0.95} = +77.4\text{ MW}$, achieving 93.3% empirical coverage on untouched validation data).
  - Clearly identified cases where calibration is unavailable.
- **Absence Disclaimer:** Missing satellite records are explicitly treated as unobserved / non-detected, never as zero fire.

### Slide 7: Scientific Provenance & Open Resources
- **Data:** NASA FIRMS Standard Processing (MODIS C6.1 SP, VIIRS C2 SP).
- **Literature:** Informed by *Li et al. (2018)* (RMA regression) and *Sofiev & Kouznetsov (2026)* (detection limits).
- **Software Stack:** Python 3.11+, Pandas, Scikit-learn, SciPy, Streamlit, Plotly, Pytest.
- **AI Tool Disclosure:** Google Antigravity / Gemini was used for code scaffolding, testing, and documentation formatting; all scientific logic, data handling, and models were reviewed and validated by the team.
- **Open Source:** MIT License on public GitHub.
