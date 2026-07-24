# PRISM Availability / Schedule Provider Adapter V1

## Objective

Translate provider-supplied pre-match availability and rest information into existing PRISM `Observation` objects without performing prediction or impact scoring.

## Input contract

One source envelope represents one match snapshot and must contain:

- `observed_at`: timezone-aware ISO-8601 timestamp;
- `home`: mapping containing `missing_starters` and `rest_days`;
- `away`: mapping containing `missing_starters` and `rest_days`.

Optional `home_team_id` and `away_team_id` fields may be supplied and, when present, must match the `MatchTarget`.

## Output contract

The adapter emits exactly four observations:

- `AVAILABILITY / home / missing_starters`;
- `AVAILABILITY / away / missing_starters`;
- `SCHEDULE / home / rest_days`;
- `SCHEDULE / away / rest_days`.

All observations preserve source identity, provider observation time, and collection time.

## Validation

- `missing_starters` must be an integer from 0 through 11 inclusive.
- `rest_days` must be a non-negative integer.
- Boolean values are not accepted as integers.
- Missing required home/away mappings or fields fail closed.
- Optional provider team identifiers must match the target.
- The adapter does not infer injury severity, replacement quality, fatigue, congestion, or tactical impact.

## Downstream compatibility

The emitted claim keys intentionally match Feature Construction V1. Verified claims therefore produce `missing_starters_difference` and `rest_days_difference` without changes to verification, normalization, or feature construction.
