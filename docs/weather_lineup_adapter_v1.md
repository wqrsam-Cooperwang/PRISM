# PRISM Weather / Lineup Provider Adapter V1

## Objective

Translate provider-neutral pre-match weather and lineup facts into existing PRISM `Observation` objects without embedding prediction logic in the collection layer.

## Input contract

A source envelope must contain:

- `observed_at`: timezone-aware ISO-8601 timestamp;
- `weather.temperature_c`: finite numeric temperature;
- `home.formation`: non-empty formation string;
- `away.formation`: non-empty formation string.

Optional `home_team_id` and `away_team_id` values may be supplied and, when present, must match the `MatchTarget`.

## Output contract

The adapter emits exactly three observations:

- `WEATHER / temperature_c`;
- `LINEUP / home / formation`;
- `LINEUP / away / formation`.

All observations preserve source provenance, use the provider snapshot timestamp as `observed_at`, and use the envelope retrieval timestamp as `collected_at`.

## Validation and governance

- Temperature must be finite numeric data; booleans are rejected.
- Formation values must be non-empty strings.
- Missing weather/home/away mappings fail closed.
- Optional team identifiers must match the target.
- The adapter does not rate formations, infer tactical quality, or impute missing weather.
- Lineup observations remain factual runtime intelligence; model interpretation belongs downstream.

## Downstream compatibility

`temperature_c` is already consumed by Feature Construction V1. `formation` claims are already mapped into the existing runtime lineup context and contribute to lineup evidence completeness without requiring changes to the core runtime.
