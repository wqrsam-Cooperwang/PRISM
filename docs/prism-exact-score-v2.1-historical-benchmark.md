# PRISM Exact Score V2.1 — Historical Outcome Benchmark

## Dataset

This benchmark uses 40 recovered historical PRISM prediction cases with independently recoverable exact-score candidates and unambiguous 90-minute outcomes.

It is distinct from the 12-case xG replay cohort:

- **40-case outcome benchmark** evaluates historical PRISM score-selection performance and error families.
- **12-case replay cohort** compares legacy V1 and V2.1 scoreline engines under frozen aggregate pre-match xG.

No missing xG or probabilities are reconstructed for the 40-case benchmark.

## Baseline results

| Metric | Result |
| --- | ---: |
| Cases | 40 |
| Primary exact-score hits | 10 / 40 (25.0%) |
| Any recommended exact-score hit | 17 / 40 (42.5%) |
| Primary result-direction hits | 22 / 40 (55.0%) |
| Any recommendation covering actual result direction | 28 / 40 (70.0%) |
| Mean minimum Manhattan score distance | 0.875 |
| Mean absolute primary total-goals error | 0.975 |
| Same-result-story clusters | 13 / 40 (32.5%) |
| Explicit path-changing-event cases | 2 / 40 (5.0%) |

## Interpretation

### 1. Score diversity has real historical value

The gap between primary exact hits (25.0%) and any-candidate exact hits (42.5%) is large. Multiple score candidates materially improved historical coverage.

However, 13 of 40 historical candidate sets remained concentrated in one result family. This supports the V2.1 Dual-score Diversity Selector: the second score should represent a genuinely different plausible match path rather than a cosmetic neighboring score.

### 2. Direction accuracy is not sufficient for Exact Score

Primary result direction was correct in only 55% of the benchmark, while at least one candidate covered the actual direction in 70%. Exact-score performance therefore depends both on upstream direction calibration and on score-distribution shape.

A scoreline engine cannot repair a strongly wrong match-direction prior by itself.

### 3. Static score assumptions remain a structural risk

Recovered reviews contain examples where red cards or late-game state changes materially altered the scoring path. These cases should remain tagged instead of being treated as clean evidence that the pre-match model was correct or wrong.

This supports scenario-mixture modelling and post-match path-event attribution.

### 4. V2.1 should not yet be tuned aggressively from the 12-case replay set

The 12-case replay cohort is still too small to estimate scenario weights reliably. Its current result shows diversity improvement but no clear aggregate distance improvement over V1.

Therefore V2.1 parameters should remain governed rather than fitted to these 12 cases.

## Architecture implications for the next version

The historical evidence supports four priorities for the next Exact Score iteration:

1. **Direction-first calibration:** scoreline generation should inherit a calibrated match-result distribution rather than allowing xG alone to imply an overconfident direction.
2. **Regime-conditioned scenario weights:** game-state mixture weights should eventually vary by home/away regime, favorite strength, competition format, and readiness instead of using one global mixture.
3. **Candidate portfolio optimization:** dual-score recommendations should optimize joint coverage, not simply probability rank plus a fixed diversity penalty.
4. **Explicit shock attribution:** early red cards, penalties, goalkeeper anomalies, and extra-time effects must be tagged so they do not contaminate model-learning targets.

## Governance decision

Do **not** promote V2.2 parameters by fitting this 40-case outcome corpus directly. Outcome-only cases lack the complete frozen upstream feature/model state required for causal parameter estimation.

Use this corpus to:

- validate error taxonomy;
- identify structural failure modes;
- evaluate historical exact-score coverage;
- design future metrics;
- and define what must be frozen automatically for every new formal prediction.

Parameter calibration should rely primarily on future fully replayable Prediction Ledger + Outcome Ledger samples as their count grows.
