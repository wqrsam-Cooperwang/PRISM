# docs/models/fusion.md

# Evidence Fusion Mathematics (Implementation Reference)

This document accompanies the EvidenceFusionEngine implementation and
records the exact formulas, variable definitions, and numerical strategies
used by the code.

## 1. Observation model

We represent latent vector \(\Theta \in \mathbb{R}^d\) (e.g., \(\lambda_{home}, \lambda_{away}, tempo, ...\)). Evidence items produce observations
\(Y \in \mathbb{R}^n\) via a linear observation model:

\[ Y = H \Theta + \varepsilon, \quad \varepsilon \sim \mathcal{N}(0, V) \]

- \(H\) is the observation matrix (\(n \times d\)), with rows mapping each observation to the latent(s) it targets.
- \(V\) is the observation covariance (\(n \times n\)), constructed from per-observation variances and pairwise correlations derived from the Evidence Dependency Matrix.

## 2. Normal-Normal posterior update

Given prior \(\Theta \sim \mathcal{N}(\mu_0, \Sigma_0)\) and observations \(Y\) per the model above,

Posterior precision and mean follow:

\[ \Lambda_{post} = \Sigma_0^{-1} + H^T V^{-1} H \]
\[ \Sigma_{post} = \Lambda_{post}^{-1} \]
\[ \mu_{post} = \Sigma_{post} \left( \Sigma_0^{-1} \mu_0 + H^T V^{-1} Y \right) \]

Implementation notes:
- Numerical stability: all inversions use robust linear algebra (Cholesky when possible, pseudo-inverse fallback). A small diagonal jitter \(\epsilon\) is added to matrices before attempting Cholesky.
- PSD enforcement: after computing \(\Sigma_{post}\), eigendecompose and clip any small negative eigenvalues to zero before reconstructing.

## 3. Observation covariance construction

For observations with per-observation variances \(v_i\) and provider correlation coefficients \(\rho_{ij}\):

\[ V_{ii} = v_i, \quad V_{ij} = \rho_{ij} \sqrt{v_i v_j} \]

where \(\rho_{ij}\) is obtained from the symmetrized Evidence Dependency Matrix and scaled by a global \(\kappa\).

## 4. Evidence aging

Decline of reliability with age uses exponential or linear decay per-provider:

Exponential: \( r(t) = r_0 2^{-\Delta t / T_{half}} \)
Linear:      \( r(t) = r_0 \max(0, 1 - \Delta t / (k T_{half})) \)

Decayed reliability scales observation variance by

\[ v_i^{eff} = v_i / (r_i + \epsilon) \]

## 5. Duplicate collapse

For identical observations (same provider, target, value, variance), the combined precision-weighted mean is

\[ y^* = \frac{\sum_i y_i / v_i}{\sum_i 1 / v_i}, \quad v^* = \frac{1}{\sum_i 1 / v_i} \]

## 6. Conflict metric

Per-latent conflict metric:

\[ C_j = \frac{\max_i y_{i,j} - \min_i y_{i,j}}{\sqrt{\mathrm{mean}_i v_{i,j}}} \]

If \(C_j > \tau\) (threshold), we inflate prior variance for latent \(j\) by factor \(\alpha_{conflict}\) and down-weight low-reliability evidence.

## References
- Bishop, C. M., *Pattern Recognition and Machine Learning*, 2006. Section on Bayesian linear regression.
- Standard formula for Normal-Normal conjugacy.
