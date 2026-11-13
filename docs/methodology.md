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
- **Model C (Context-Aware OLS):**
  $$\widehat{FRP}_{\text{MODIS, ref}} = \beta_0 + \beta_1 FRP_{\text{VIIRS}} + \beta_2 \sin\left(\frac{2\pi m}{12}\right) + \beta_3 \cos\left(\frac{2\pi m}{12}\right) + \beta_4 \mathbb{I}_{\text{Night}}$$

## 3. License & AI Tool Disclosure

### Software License & Data Terms
- **Software License:** MIT License. Applies strictly to the SensorScope application source code.
- **NASA Data Terms:** NASA FIRMS active fire datasets retain their respective NASA Open Data Terms of Use and scientific public-domain attribution.

### AI Tool Usage Disclosure
In accordance with NASA Space Apps Challenge disclosure guidelines:
- **ChatGPT (OpenAI):** Used for background challenge exploration, literature search and analysis (Li et al. 2018, Sofiev & Kouznetsov 2026), and proposal drafting.
- **Google Antigravity / Gemini:** Used as an agentic AI coding environment for repository scaffolding, unit test implementation, and documentation formatting.
- All code, data handling, and scientific conclusions were audited, reviewed, and empirically verified by the team.
