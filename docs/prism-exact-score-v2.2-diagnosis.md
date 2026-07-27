# PRISM Exact Score V2.2 — Architecture Diagnosis

## Evidence boundary

This diagnosis is based on two distinct historical evidence layers:

1. **40-case outcome benchmark** — recovered pre-match PRISM exact-score candidates plus unambiguous 90-minute outcomes. This supports observable error-signature analysis, not reconstruction of missing upstream model state.
2. **12-case replay cohort** — frozen aggregate pre-match xG plus outcomes. This supports scoreline-engine V1-vs-V2.1 replay, but not full upstream evidence-weight reconstruction.

No missing xG, market probability, lineup information, or model weights are inferred from hindsight.

## 40-case benchmark signals

- Primary exact-score hit: 10/40 (25.0%).
- Any candidate exact-score hit: 17/40 (42.5%).
- Primary result-direction hit: 22/40 (55.0%).
- Any candidate result-direction hit: 28/40 (70.0%).
- Mean minimum Manhattan score distance: 0.875 goals.
- Primary direction misses: 18/40 (45.0%).
- Portfolio direction misses: 12/40 (30.0%).
- Primary total-goals underprediction: 18/40 (45.0%).
- Primary total-goals overprediction: 8/40 (20.0%).
- Primary total-goals exact: 14/40 (35.0%).
- Same-result-story candidate clusters: 13/40 (32.5%).
- Direct clean-sheet overconfidence signature: 1/40 (2.5%).
- Explicitly tagged path-changing events: 2/40 (5.0%).

## What the evidence does and does not support

### Strongly supported

1. **Direction calibration is the first bottleneck.**
   - A scoreline engine cannot recover reliably when the primary match direction is wrong in 45% of the benchmark.
   - Even multi-score portfolios fail to cover the correct result family in 30% of cases.

2. **The historical system under-covered open/high-scoring paths.**
   - Primary total-goals underprediction (45%) materially exceeds overprediction (20%).
   - This is broader than a clean-sheet problem; the direct clean-sheet signature is only 2.5%.

3. **Candidate portfolios historically lacked sufficient scenario diversity.**
   - 32.5% of multi-score sets remain in one result-family story.
   - V2.1 diversity controls are therefore directionally justified, even though the 12-case replay cohort has not yet demonstrated a net exact-hit lift.

4. **Path-changing events require attribution rather than model blame or credit.**
   - Red cards and similar shocks must remain explicitly tagged and excluded from naive model-quality conclusions.

### Not yet supported

- Re-tuning exact numerical scenario weights from this 40-case sample.
- Learning new upstream evidence weights from outcome-only records.
- Reconstructing missing pre-match xG or market probabilities from final scores.
- Declaring V2.1 superior to V1 on exact-score accuracy from the current 12-case replay cohort.

## V2.2 architecture priorities

### Priority 1 — Direction-First Calibration Layer

Introduce an explicit result-family calibration stage before exact-score generation.

Responsibilities:

- consume governed consensus home/draw/away probabilities;
- detect excessive concentration unsupported by independent evidence families;
- retain a calibrated result-family distribution separate from raw consensus;
- expose uncertainty/entropy to the scoreline engine;
- prevent the scoreline generator from treating a weakly supported favourite as a near-certain directional regime.

The scoreline engine should receive both expected goals and the calibrated direction distribution.

### Priority 2 — Regime-Conditioned Scoreline Scenarios

Replace one global fixed scenario mixture with regime-conditioned scenario weights.

Candidate regimes:

- strong-home but uncertain;
- strong-away but uncertain;
- balanced/low-separation;
- low-total defensive;
- open/high-variance;
- readiness mismatch / early-season uncertainty.

The historical underprediction asymmetry argues for a specific open/high-variance route rather than simply raising every lambda.

### Priority 3 — Portfolio Optimisation Across Result Families

Upgrade the dual-score selector from a penalty-only heuristic to a portfolio objective.

The selector should trade off:

- raw score probability;
- result-family coverage;
- clean-sheet-story overlap;
- total-goals-band overlap;
- scenario-path overlap;
- calibrated direction probability.

The goal is not artificial diversity. A second score may remain in the same result family when the calibrated direction probability is genuinely dominant, but this must be an explicit optimisation decision.

### Priority 4 — Shock Attribution Metadata

Prediction and outcome ledgers should preserve path-changing-event metadata:

- red card timing;
- penalty timing;
- major goalkeeper/injury event;
- extra time;
- abandonment or exceptional weather where relevant.

Historical evaluation should report both all-case performance and pre-match-attributable performance.

## V2.2 implementation order

1. Direction Calibration data contract and deterministic calibrator.
2. Calibrated-direction regression tests.
3. Regime classifier driven only by frozen pre-match features.
4. Regime-conditioned scenario-mixture interface.
5. Portfolio objective selector.
6. Shock-aware benchmark reporting.
7. Prospective validation on newly frozen matches before any parameter optimisation.

## Promotion rule

V2.2 must not replace V2.1 merely because its architecture is more elaborate.

Promotion requires prospective or properly frozen out-of-sample evidence showing improvement in at least:

- result-direction calibration;
- dual-score exact-hit rate or score distance;
- without material degradation in another major regime.

Historical recovered data remains a diagnostic set. New fully frozen Prediction + Outcome Ledger cases are the promotion set.
