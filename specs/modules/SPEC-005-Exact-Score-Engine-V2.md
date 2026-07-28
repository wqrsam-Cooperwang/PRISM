# SPEC-005 — Exact Score Engine V2

Status: Draft  
Target release: PRISM Enterprise V3.1

## 1. Objective

Produce calibrated exact-score probabilities while preserving consistency with the broader match-outcome, totals and BTTS distributions.

## 2. Baseline

The engine begins with expected-goal distributions for the home and away teams, including uncertainty intervals and scenario weights.

## 3. Required model components

- independent Poisson baseline;
- Dixon-Coles low-score correction;
- draw and low-event calibration;
- over-dispersion or alternative count distributions where validated;
- home/away and league-specific parameters;
- lineup and player-availability scenario mixtures;
- aggregate-incentive adjustment for two-legged ties;
- competition-priority and rotation scenarios;
- goalkeeper and set-piece contributions;
- tactical-matchup interactions;
- calibrated market latent-strength input.

## 4. Scenario mixture

Unconfirmed events must be represented through probability-weighted scenarios. Example:

- strongest expected lineup;
- moderate rotation;
- heavy rotation;
- key-player available;
- key-player absent.

The final score matrix is the weighted mixture of scenario-specific matrices.

## 5. Output requirements

The engine must output:

- full score probability matrix to a configurable goal cap;
- top exact-score candidates;
- cumulative probability covered by ranked candidates;
- home/draw/away probabilities derived from the matrix;
- totals probabilities derived from the matrix;
- BTTS probabilities derived from the matrix;
- expected home, away and total goals;
- confidence and uncertainty indicators;
- model and data timestamps.

## 6. Consistency checks

The following identities must hold within numerical tolerance:

- score-matrix probabilities sum to 1;
- 1X2 probabilities equal aggregation of the score matrix;
- totals probabilities equal aggregation of the score matrix;
- BTTS probability equals aggregation of scores where both teams score;
- displayed top-score probabilities match matrix values.

## 7. Validation

Evaluate using:

- exact-score top-1 and top-k hit rate;
- score probability log loss;
- ranked probability score;
- 1X2 Brier score;
- totals and BTTS calibration;
- calibration by score family, league and goal environment;
- comparison against simple Poisson and current production baselines.

## 8. Output policy

PRISM may present two primary exact scores when operating in dual-score mode. The system must still retain the full probability matrix and may provide additional scores for research or diagnostics.

Ranked scores are model candidates, not certainties. Confidence must decrease when data reliability, lineup certainty or league reliability is low.
