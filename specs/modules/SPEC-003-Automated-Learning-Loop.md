# SPEC-003 — Automated Learning Loop

Status: Draft  
Target release: PRISM Enterprise V3.1

## 1. Purpose

Define the complete automated pre-match, post-match and learning loop for PRISM.

## 2. Prediction Archive

Each prediction record must store:

- match and competition identifiers;
- prediction timestamp and data cutoff;
- model and configuration version;
- expected goals for both teams and uncertainty intervals;
- 1X2, totals, BTTS and exact-score probabilities;
- ranked exact-score outputs;
- feature snapshot and missing-data flags;
- scenario mixture assumptions;
- market snapshot and source timestamps;
- confidence score;
- explanation and dominant drivers.

A prediction is immutable after kickoff. Corrections must create a new revision with a new timestamp.

## 3. Prediction Memory

Prediction Memory preserves the decision context of every match:

- why the prediction was made;
- which features materially influenced it;
- which assumptions were confirmed or rejected;
- whether the prediction succeeded by each evaluation metric;
- recurring error patterns for teams, coaches, leagues and feature groups.

Prediction Memory is an audit and learning dataset, not free-form chat history.

## 4. Result Collector

The Result Collector should obtain and reconcile:

- final and half-time score;
- xG and xGA where available;
- shots and shots on target;
- possession and PPDA where available;
- cards, penalties and VAR events;
- substitutions and official lineups;
- goalkeeper changes;
- post-match market data;
- weather and referee observations.

Conflicting sources must be recorded with source-level confidence. The reconciled value must retain provenance.

## 5. Auto Review Engine

For every completed match calculate:

- score-distance error;
- home-goal and away-goal error;
- 1X2 correctness;
- totals correctness;
- BTTS correctness;
- probability calibration;
- Brier score;
- log loss;
- ranked probability score where applicable.

The review engine assigns probabilistic error causes rather than a single absolute cause.

Possible attribution groups:

- lineup or availability error;
- red-card or penalty shock;
- goalkeeper over/under-performance;
- finishing variance relative to xG;
- tactical mismatch;
- rotation or competition-priority error;
- aggregate-incentive error;
- market-calibration error;
- weather or pitch effect;
- data quality or missing-data issue;
- ordinary irreducible variance.

## 6. Learning Engine

The Learning Engine aggregates reviews across rolling windows and produces:

- feature contribution reports;
- league-specific calibration reports;
- team and coach regime alerts;
- parameter-change proposals;
- candidate model versions;
- rollback recommendations.

It must not directly overwrite the production model.

## 7. Feature contribution scoring

Feature performance must be assessed through out-of-sample tests and ablation comparisons. Example outputs:

- contribution to log-loss improvement;
- contribution to Brier-score improvement;
- calibration impact;
- stability by league and season;
- interaction and redundancy indicators.

Simple correlation with successful predictions is insufficient evidence.

## 8. Drift detection

Monitor feature and model behaviour across configurable windows, including recent 50, 100, 250 and 1,000-match samples where data volume permits.

Detect:

- feature distribution drift;
- target relationship drift;
- calibration drift;
- league or season regime change;
- source-quality deterioration;
- missing-data increase.

A drift alert may reduce confidence, trigger retraining or freeze automatic promotion.

## 9. Model promotion gates

A candidate may be promoted only when it:

1. beats the production model on locked out-of-sample data;
2. does not materially degrade major leagues or key metrics;
3. passes leakage and reproducibility checks;
4. passes calibration thresholds;
5. includes a rollback package;
6. receives explicit approval.

## 10. Required outputs

For every evaluation cycle generate:

- accuracy and calibration report;
- feature promotion/retirement recommendations;
- drift report;
- candidate-versus-production comparison;
- change log;
- approval status.
