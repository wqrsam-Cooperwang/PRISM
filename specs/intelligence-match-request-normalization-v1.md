# Intelligence to MatchRequest Normalization V1

## Purpose

Bridge verified Automated Match Intelligence into the existing PRISM runtime without redesigning the runtime, evidence engine, or orchestrator.

The normalizer converts one frozen `IntelligenceBundle` plus externally produced `ModelOutput` values into a runtime-ready application input.

## Boundary

The intelligence layer owns factual collection, verification, freshness, conflict handling, and readiness.

The normalizer does not:

- collect remote data;
- resolve conflicts that remain unresolved in the bundle;
- fabricate missing values;
- generate predictive model outputs;
- run the PRISM orchestrator;
- change canonical runtime engine order.

At least one `ModelOutput` must still be supplied by the prediction-model layer because the existing runtime preflight requires model output.

## Output contract

Normalization returns a `NormalizedMatchInput` containing:

- `request`: the existing `MatchRequest` consumed by `build_match_context`;
- `evidence_completeness`: the existing Evidence Engine completeness payload consumed by `build_runtime`;
- `model_feature_data`: all usable verified/provisional intelligence organized by intelligence category for later model generation and diagnostics;
- `intelligence_fingerprint`: the source bundle fingerprint for reproducibility;
- `readiness`: the source bundle readiness level.

No existing runtime type is replaced.

## Claim eligibility

Only claims with status `VERIFIED` or `PROVISIONAL` and non-null values may enter normalized runtime inputs.

`CONFLICTED` and `UNSUPPORTED` claims remain visible in the source `IntelligenceBundle` but must not silently become runtime facts.

## MatchRequest mapping

Target identity maps directly:

- match identity, competition, kickoff, venue, season and stage;
- home and away team identifiers and names.

Special strength mapping:

- `team_strength / elo_rating / subject=home` -> `home_elo_rating`;
- `team_strength / elo_rating / subject=away` -> `away_elo_rating`;
- only finite numeric ELO values are accepted.

Compatible context categories map as follows:

- `lineup` -> `MatchRequest.lineups`;
- `availability` -> `MatchRequest.injuries`;
- `market` -> `MatchRequest.market`;
- `weather` -> `MatchRequest.weather`;
- `schedule` -> `MatchRequest.schedule`;
- `tactical` -> `MatchRequest.tactical`.

Subject-scoped claims are nested under their subject. Unscoped claims remain at category root. Duplicate normalized paths are rejected rather than overwritten.

Categories that do not have a dedicated legacy `MatchRequest` field are retained in `model_feature_data`; they are not forced into an unrelated runtime mapping.

## Evidence completeness translation

The normalizer translates intelligence category assessments into the existing Evidence Engine categories:

- `lineup` <- lineup score;
- `injuries` <- availability score;
- `odds` <- market score;
- `weather` <- weather score;
- `tactical_data` <- tactical score;
- `historical_data` <- mean of team strength, recent form and head-to-head scores;
- `market_data` <- market score;
- `motivation` <- motivation/context score.

This translation changes no Evidence Engine thresholds or weights.

## Determinism and auditability

For an equivalent `IntelligenceBundle` and equivalent ordered/unordered model output tuple, normalized factual mappings and evidence completeness must be deterministic.

The bundle fingerprint is carried unchanged so downstream prediction artifacts can identify exactly which intelligence snapshot produced the request.

## V1 acceptance

Tests must prove:

1. verified/provisional claims map to the expected runtime fields;
2. conflicted claims never enter runtime facts;
3. ELO ratings map only from valid usable strength claims;
4. all usable categories remain available in model feature data;
5. evidence completeness matches the documented translation;
6. missing intelligence stays missing rather than receiving defaults;
7. duplicate normalized paths fail closed;
8. the resulting request can be converted by the existing `build_match_context` without changing runtime code.
