# SensorScope Methodology & Scientific Contract

## 1. Mathematical Formulation

### 1.1 Spatial Grid Discretization
Satellite observations are mapped into equal-area geographic cells $\mathcal{C}_{i,j}$ defined by a resolution of $\Delta \lambda = \Delta \phi \approx 0.1^\circ$ (~11 km):

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

## 2. Reliability Gate Decision Rules

$$\text{Status}(\mathcal{C}) = \begin{cases} 
\text{GREEN (Reliable)}, & \text{if } N_{\text{pairs}} \ge 50 \text{ and } |\text{Bias}_{\%}| \le 15\% \\
\text{YELLOW (Caution)}, & \text{if } 20 \le N_{\text{pairs}} < 50 \text{ or } 15\% < |\text{Bias}_{\%}| \le 25\% \\
\text{RED (Abstain)}, & \text{if } N_{\text{pairs}} < 20 \text{ or out-of-domain}
\end{cases}$$
