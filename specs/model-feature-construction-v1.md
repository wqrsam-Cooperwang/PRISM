# PRISM Model Feature Construction V1

## Purpose

Convert normalized, verified match intelligence into deterministic numeric model inputs without making predictions or changing existing PRISM runtime engines.

## Position in the pipeline

`IntelligenceBundle -> NormalizedMatchInput -> FeatureVector -> prediction models -> ModelOutput -> existing PRISM runtime`

The feature layer is an adapter. It does not estimate match probabilities, create synthetic facts, or override intelligence verification outcomes.

## Input contract

V1 consumes `NormalizedMatchInput` from the intelligence normalization bridge.

Only facts already admitted by normalization may contribute to features. Conflicted and unsupported claims are therefore excluded upstream.

## Output contract

`FeatureVector` contains:

- `schema_version`
- immutable numeric `values`
- sorted `missing_features`
- `intelligence_fingerprint`
- `readiness`
- deterministic `fingerprint`

A missing feature is omitted from `values` and named in `missing_features`. V1 never substitutes zero for unknown data.

## Core V1 features

Team-relative features:

- `elo_difference`: home ELO minus away ELO
- `recent_points_difference`: home `points_last_5` minus away `points_last_5`
- `missing_starters_difference`: home missing starters minus away missing starters
- `rest_days_difference`: home rest days minus away rest days

Market features when decimal odds are available:

- `market_home_implied_probability`
- `market_draw_implied_probability`
- `market_away_implied_probability`
- `market_overround`

Single-context features when available:

- `temperature_c`

Quality metadata:

- `intelligence_readiness_score` using fixed mapping REJECTED=0.0, LIMITED=1/3, STANDARD=2/3, DEEP=1.0
- evidence completeness values prefixed with `evidence_`, for example `evidence_lineup`

## Numeric validation

Feature inputs must be finite numbers. Booleans are not accepted as numeric values. Invalid numeric facts fail closed with `ValueError` rather than being silently coerced.

Decimal odds used for implied probabilities must be strictly greater than 1.0.

## Market normalization

When all three 1X2 decimal odds are present, raw implied probabilities are `1 / odds`.

`market_overround` is the sum of raw implied probabilities minus 1.

The three exported market probabilities are normalized by their raw sum so they total 1.0.

Partial 1X2 odds do not produce implied-probability features; all four market-derived features are marked missing.

## Determinism and auditability

Feature construction must be independent of mapping insertion order. The feature fingerprint is SHA-256 over canonical JSON containing:

- schema version
- sorted feature values
- sorted missing features
- intelligence fingerprint
- readiness

Changing an admitted fact or the intelligence fingerprint must change the feature fingerprint.

## V1 boundaries

Out of scope:

- model training or inference
- feature standardization learned from historical datasets
- opponent-strength-adjusted form
- xG-derived features
- tactical embeddings or LLM-derived numeric scores
- automatic feature selection
- imputation

Those may be added later under benchmark and promotion governance.