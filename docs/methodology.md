# SensorScope Methodology & Scientific Contract

## 1. Mathematical Formulation

### 1.1 Spatial Grid Discretization
Satellite observations are mapped into a regular geographic grid $\mathcal{C}_{i,j}$ defined by a resolution of $\Delta \lambda = \Delta \phi = 0.1^\circ$ ($\approx 11.1\text{ km latitude} \times 9.6\text{ km longitude}$ at 30°N):

$$\mathcal{C}_{i,j} = \left\{ (\phi, \lambda) \mid \phi \in [\phi_i, \phi_i + \Delta \phi), \lambda \in [\lambda_j, \lambda_j + \Delta \lambda) \right\}$$

Within each cell and observation window (day $t$, condition $d \in \{\text{Day}, \text{Night}\}$), we compute:
- Total detections: $N_{\text{MODIS}}, N_{\text{VIIRS}}$
- Integrated Fire Radiative Power (MW):
  $$FRP_{\text{MODIS}} = \sum_{k \in \mathcal{C}_{i,j}} FRP_k^{(\text{MODIS})}, \quad FRP_{\text{VIIRS}} = \sum_{m \in \mathcal{C}_{i,j}} FRP_m^{(\text{VIIRS})}$$

### 1.2 Disagreement Metrics
$$\Delta N = N_{\text{VIIRS}} - N_{\text{MODIS}}$$
$$\Delta FRP = FRP_{\text{VIIRS}} - FRP_{\text{MODIS}}$$

### 1.3 Calibration Formulations & Scientific Nature
Following **Li et al. (2018)**:
- **Baseline A (Identity):** $\widehat{FRP}_{\text{MODIS, ref}} = FRP_{\text{VIIRS}}$
- **Baseline B (Global RMA):**
  $$\widehat{FRP}_{\text{MODIS, ref}} = \alpha + \beta \cdot FRP_{\text{VIIRS}}, \quad \beta = \frac{\sigma(FRP_{\text{MODIS}})}{\sigma(FRP_{\text{VIIRS}})} \text{sgn}(\rho)$$
  *Fitted coefficients on 2022 training window:*
  - All loaded files ($n=1,314$): $\beta = 0.80559, \alpha = 1.53251\text{ MW}$
  - Strict Nov 1–10 window ($n=1,312$): $\beta = 0.80528, \alpha = 1.42468\text{ MW}$
- **Model C (Context-Aware OLS):**
  $$\widehat{FRP}_{\text{MODIS, ref}} = \beta_0 + \beta_1 FRP_{\text{VIIRS}} + \beta_2 N_{\text{VIIRS}} + \beta_3 \mathbb{I}_{\text{Night}}$$
  Predictor features are strictly sensor-side observables ($FRP_{\text{VIIRS}}$, hotspot cluster count $N_{\text{VIIRS}}$, and diurnal pass indicator $\mathbb{I}_{\text{Night}}$). Zero target leakage.

> **Definitive Scientific Scope:** SensorScope does **NOT** claim a "pure instrument calibration" that isolates sensor optics from physical reality. Because satellite overpasses over agricultural fires are separated by a median of 24 to 34 minutes, differences in observed FRP reflect a mixture of instrument characteristics, atmospheric transmission, and real fire evolution (stubble fires often die out in 30–60 minutes). SensorScope is therefore defined as an **empirical statistical harmonization of co-active grid-cell-day observations**.

### 1.4 Training-Period Reconciliation & Cross-Validation Strategy
- **Training Window Definition:**
  - The core scientific training window is the **peak Kharif burning period: November 1 to November 10, 2022** ($n=1,312$).
  - Initial MAP_KEY API test probe files (`2022-05-31_d1.csv` [1 pair] and `2022-11-30_d1.csv` [1 pair]) contributed 2 extraneous records (0.15% of data). Whether evaluated with ($n=1,314$) or without ($n=1,312$) these probe records, model coefficients and validation MAE change by less than $0.05\text{ MW}$.
- **Five-Fold Date-Grouped Cross-Validation:**
  - Observations from the same acquisition date are kept strictly within either train or validation folds using `GroupKFold(n_splits=5)`.
  - *Methodological Disclosure:* This is **date-grouped** cross-validation, not chronological blocking. Observations on adjacent calendar dates may still share atmospheric or burning conditions.
  - **Pooled Out-Of-Fold MAE:** Direct sample-weighted concatenated error across all out-of-fold predictions is **$31.5128\text{ MW}$** (strict Nov 1–10) and **$31.6024\text{ MW}$** (all loaded). Earlier mentions of 24.09 MW were preliminary fold-level unweighted estimates prior to full concatenated array pooling.
- **November 2023 Evaluation Window:**
  - Reclassified formally as a **held-out comparative evaluation period** (rather than an untouched test set), because its results were used to compare Model A, B, and C.
  - Empirical error envelope coverage ($\approx 93.3\% - 94.6\%$) carries this qualification.

### 1.5 Calibration Sensitivity to Acquisition Timing
For the 2,560 co-active diurnal cell observations, timing delta sensitivity demonstrates the physical nature of the harmonization:

| Timing Subset ($\min \Delta t$) | Total $n$ | Val $n$ | Model A (Identity) MAE | Model C (Harmonized) MAE | $\Delta \text{MAE}$ Improvement |
|:---|:---:|:---:|:---:|:---:|:---:|
| **$\le 5$ min (Contemporaneous)** | 385 | 274 | 38.46 MW | **26.64 MW** (28.80 in-bin) | **+30.7%** (+25.1%) |
| **$\le 15$ min (Near-Contemporaneous)** | 756 | 274 | 38.46 MW | **26.64 MW** (24.53 in-bin) | **+30.7%** (+36.2%) |
| **$\le 30$ min (Broader Window)** | 1,341 | 661 | 33.76 MW | **27.23 MW** (25.66 in-bin) | **+19.3%** (+24.0%) |
| **$> 30$ min (Temporally Separated)** | 1,219 | 585 | 27.64 MW | **25.07 MW** (27.55 in-bin) | **+9.3%** (+0.3%) |

**Physical Insight:** When satellites observe fires within 15 minutes, harmonization achieves its largest error reduction ($+30.7\%$ to $+36.2\%$). When observations are separated by $>30$ minutes, in-bin calibration provides almost no improvement over raw data ($+0.3\%$), because differences are dominated by rapid agricultural fire burnout rather than sensor response.



## 3. License & AI Tool Disclosure

### Software License & Data Terms
- **Software License:** MIT License. Applies strictly to the SensorScope application source code.
- **NASA Data Terms:** NASA FIRMS active fire datasets retain their respective NASA Open Data Terms of Use and scientific public-domain attribution.

### AI Tool Usage Disclosure
In accordance with NASA Space Apps Challenge disclosure guidelines:
- **ChatGPT (OpenAI):** Used for background challenge exploration, literature search and analysis (Li et al. 2018, Sofiev & Kouznetsov 2026), and proposal drafting.
- **Google Antigravity / Gemini:** Used as an agentic AI coding environment for repository scaffolding, unit test implementation, and documentation formatting.
- All code, data handling, and scientific conclusions were audited, reviewed, and empirically verified by the team.
