# API-Football Team Statistics Provider V1

## Objective

Add API-Football as PRISM's second real football-data provider for non-market team information. V1 focuses on team statistics for the target competition and season.

## Source contract

The provider calls the official API-Football V3 `teams/statistics` endpoint separately for the target home and away teams using explicit provider team IDs, league ID, season, and the target kickoff date.

Authentication uses the `x-apisports-key` request header. The secret must never appear in request reprs, source envelopes, reports, ledger records, fixtures, or test output.

## Provider responsibilities

The provider may:

- retrieve the current pre-match team-statistics snapshots;
- validate top-level API-Football response structure;
- validate that each response describes the configured provider team, league and season;
- preserve factual fields such as fixture counts, results, goals and form text;
- emit deterministic provider-neutral `SourceEnvelope` objects.

The provider must not:

- fabricate or relabel a team-statistics score as Elo;
- calculate PRISM probabilities;
- perform consensus or governance;
- silently substitute missing data;
- downgrade provider/schema failures into synthetic observations.

## Architecture

```text
API-Football /teams/statistics
        ↓
ApiFootballTeamStatisticsClient
        ↓
provider-neutral team statistics SourceEnvelope
        ↓
Team Statistics Adapter (next layer)
        ↓
Team Statistics Features / Strength Baseline
        ↓
existing PRISM production pipeline
```

## Baseline governance

API-Football does not supply Elo. PRISM therefore must not populate the existing `elo_rating` claim with a derived statistic merely to satisfy the current gate. A later Team Statistics Strength Baseline will be introduced explicitly and the collection gate will accept either a genuine Elo baseline or the governed Team Statistics baseline, together with the market baseline.

## Cost governance

The connector should use the smallest practical number of requests. V1 requires two `teams/statistics` calls per target match, one per team, and must remain compatible with the free API-Football quota during development.
