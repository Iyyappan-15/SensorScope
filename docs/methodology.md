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

### 1.3 Calibration Formulations
Following **Li et al. (2018)**:
- **Baseline A (Identity):** $\widehat{FRP}_{\text{MODIS, ref}} = FRP_{\text{VIIRS}}$
- **Baseline B (Global RMA):**
  $$\widehat{FRP}_{\text{MODIS, ref}} = \alpha + \beta \cdot FRP_{\text{VIIRS}}, \quad \beta = \frac{\sigma(FRP_{\text{MODIS}})}{\sigma(FRP_{\text{VIIRS}})} \text{sgn}(\rho)$$
  *Exact fitted coefficients on 2022 training split ($n=1,314$):* $\beta = 0.80559$, $\alpha = 1.53251\text{ MW}$.
- **Model C (Context-Aware OLS):**
  $$\widehat{FRP}_{\text{MODIS, ref}} = \beta_0 + \beta_1 FRP_{\text{VIIRS}} + \beta_2 N_{\text{VIIRS}} + \beta_3 \mathbb{I}_{\text{Night}}$$
  Predictor features are strictly sensor-side observables ($FRP_{\text{VIIRS}}$, hotspot cluster count $N_{\text{VIIRS}}$, and diurnal pass indicator $\mathbb{I}_{\text{Night}}$). Zero target leakage.

### 1.4 Cross-Validation & Evaluation Strategy
- **Five-Fold Date-Grouped Cross-Validation (2022 Training Window):**
  - Observations from the same acquisition date are kept strictly within either train or validation folds using `GroupKFold(n_splits=5)` across 1,314 paired records.
  - *Methodological Disclosure:* This is **date-grouped** cross-validation, not chronological blocking. Observations on adjacent calendar dates may still share atmospheric or burning conditions.
  - **Pooled Out-Of-Fold MAE:** Direct sample-weighted pooled error across all 1,314 out-of-fold predictions is **$31.6024\text{ MW}$** (vs $32.0137\text{ MW}$ unweighted fold average).
- **November 2023 Evaluation Window ($n=1,246$):**
  - Reclassified formally as a **held-out comparative evaluation period** (rather than an untouched test set), because its results were used to compare Model A, B, and C.
  - Empirical error envelope coverage ($\approx 93.3\% - 94.6\%$) carries this qualification.

### 1.5 Calibration Observation Acquisition Timing
For the 2,560 co-active diurnal cell observations:
- Satellites do not observe grid cells simultaneously; Aqua and Suomi-NPP have nominal 13:30 equator crossings but differing swaths and orbits.
- **Minimum Pairwise Detection Time Delta:** Median $= 24.0\text{ min}$, Mean $= 32.8\text{ min}$, 95th percentile $= 82.0\text{ min}$.
  - $\le 15\text{ min}$: $29.53\%$ ($756/2,560$)
  - $\le 30\text{ min}$: $52.38\%$ ($1,341/2,560$)
  - $> 60\text{ min}$: $7.27\%$ ($186/2,560$)
- Rapid stubble fire evolution over 30–60 minutes is an inherent source of measurement divergence, justifying the Reliability Gate's empirical uncertainty bands.


## 3. License & AI Tool Disclosure

### Software License & Data Terms
- **Software License:** MIT License. Applies strictly to the SensorScope application source code.
- **NASA Data Terms:** NASA FIRMS active fire datasets retain their respective NASA Open Data Terms of Use and scientific public-domain attribution.

### AI Tool Usage Disclosure
In accordance with NASA Space Apps Challenge disclosure guidelines:
- **ChatGPT (OpenAI):** Used for background challenge exploration, literature search and analysis (Li et al. 2018, Sofiev & Kouznetsov 2026), and proposal drafting.
- **Google Antigravity / Gemini:** Used as an agentic AI coding environment for repository scaffolding, unit test implementation, and documentation formatting.
- All code, data handling, and scientific conclusions were audited, reviewed, and empirically verified by the team.
