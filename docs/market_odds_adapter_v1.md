# PRISM Provider-Neutral 1X2 Market Odds Adapter V1

## Objective

Translate a retrieved provider payload containing one pre-match 1X2 decimal-odds snapshot into the existing PRISM `Observation` domain without changing verification, feature construction, prediction models, or consensus.

## Input contract

The adapter consumes a `SourceEnvelope` whose payload contains:

- `observed_at`: timezone-aware ISO-8601 timestamp for the quoted market snapshot;
- `home_decimal_odds`: decimal odds strictly greater than 1.0;
- `draw_decimal_odds`: decimal odds strictly greater than 1.0;
- `away_decimal_odds`: decimal odds strictly greater than 1.0.

Optional identity fields:

- `provider_event_id`;
- `home_team_id`;
- `away_team_id`.

When optional team ids are present they must match the supplied `MatchTarget`. A mismatch fails closed.

## Output contract

Exactly three `IntelligenceCategory.MARKET` observations are emitted with claim keys already consumed by Feature Construction V1:

- `home_decimal_odds`;
- `draw_decimal_odds`;
- `away_decimal_odds`.

All observations:

- retain the `SourceEnvelope.source`;
- use the provider snapshot time as `observed_at`;
- use the envelope retrieval time as `collected_at`;
- receive deterministic observation ids derived from source, match, snapshot time, and claim key.

## Governance

1. The adapter does not de-vig, average, interpolate, or predict.
2. Missing prices are not imputed.
3. Invalid/non-finite prices fail closed.
4. Team identity conflicts fail closed when provider ids are supplied.
5. Verification remains responsible for reconciling multiple provider snapshots/sources.
6. Feature Construction remains responsible for deriving de-vigged market probabilities.
7. Provider-specific HTTP clients and credentials remain outside this adapter contract.
