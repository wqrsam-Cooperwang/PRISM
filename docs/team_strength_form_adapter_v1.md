# PRISM Team Strength / Recent Form Provider Adapter V1

## Objective

Define a provider-neutral adapter that translates externally supplied team strength and recent-form data into existing PRISM `Observation` objects.

## Input contract

One source envelope represents one match snapshot and must contain:

- `observed_at`: timezone-aware ISO-8601 timestamp;
- `home`: mapping containing `elo_rating` and `points_last_5`;
- `away`: mapping containing `elo_rating` and `points_last_5`.

Optional `home_team_id` and `away_team_id` fields may be supplied and, when present, must match the `MatchTarget`.

## Output contract

The adapter emits exactly four observations:

- `TEAM_STRENGTH / home / elo_rating`;
- `TEAM_STRENGTH / away / elo_rating`;
- `RECENT_FORM / home / points_last_5`;
- `RECENT_FORM / away / points_last_5`.

All observations preserve the envelope source, use the provider snapshot timestamp as `observed_at`, and use the envelope retrieval timestamp as `collected_at`.

## Validation

- Elo ratings must be finite numeric values.
- `points_last_5` must be an integer from 0 through 15 inclusive.
- Missing home/away mappings or required values fail closed.
- Boolean values are not accepted as numbers.
- Optional team identifiers must match the target.
- The adapter does not calculate Elo, infer form, impute missing matches, or make prediction decisions.

## Downstream compatibility

The output claim keys intentionally match the existing Feature Construction V1 contract. Verified observations therefore produce `elo_difference` and `recent_points_difference` without changes to verification, normalization, feature construction, or prediction models.
