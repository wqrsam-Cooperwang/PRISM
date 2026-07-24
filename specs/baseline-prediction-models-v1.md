# PRISM Baseline Prediction Models V1

## Purpose

Introduce the first concrete independent prediction models that consume the governed `FeatureVector` contract and emit canonical `ModelOutput` objects.

These models are transparent baselines. Their purpose is to establish an auditable end-to-end prediction path before more complex statistical or machine-learning models are introduced.

## Market Probability Model V1

Model identity: `market_probability`

Required features:

- `market_home_implied_probability`
- `market_draw_implied_probability`
- `market_away_implied_probability`

The feature builder already removes the 1X2 bookmaker overround and normalizes the three probabilities. Market V1 therefore returns those probabilities directly and performs no second de-vig or hidden adjustment.

The model must reject non-finite values, values outside `[0, 1]`, or probabilities that do not sum to 1 within canonical `ModelOutput` tolerance.

## Elo Probability Model V1

Model identity: `elo_probability`

Required feature:

- `elo_difference`

V1 uses a three-outcome Davidson-style Bradley-Terry construction.

Let:

- `d` be home Elo minus away Elo;
- `h` be the configured home-advantage Elo constant;
- `s = 10 ** ((d + h) / 400)` be the home-vs-away strength ratio;
- away quality be `1`;
- home quality be `s`;
- draw quality be `draw_scale * sqrt(s)`.

The three qualities are normalized to sum to 1.

V1 configuration defaults:

- `home_advantage_elo = 60.0`
- `draw_scale = 0.65`

These defaults are versioned baseline parameters, not claims of global optimality. Any future parameter change must be evaluated as a candidate through the existing historical benchmark and promotion gate.

The model must reject non-finite Elo differences and invalid configuration values.

## Governance

Both models implement the existing `PredictionModel` interface and must run through `run_prediction_model` / `run_model_suite` so required-feature enforcement and provenance diagnostics remain centralized.

No baseline model may:

- fetch data;
- impute missing features;
- alter feature provenance;
- bypass canonical `ModelOutput` validation;
- call another prediction model internally.

## Acceptance

V1 is accepted when tests prove:

1. Market V1 reproduces the governed normalized market probabilities exactly.
2. Elo V1 probabilities are deterministic, finite and sum to 1.
3. Increasing `elo_difference` increases home-win probability and decreases away-win probability.
4. The configured home advantage moves an otherwise equal matchup toward the home team.
5. Both models execute through the governed model runner and receive provenance diagnostics.
6. Missing required features fail before model execution through the existing runner contract.
7. A suite containing both models produces two canonical independent `ModelOutput` objects suitable for the existing Consensus Engine.
