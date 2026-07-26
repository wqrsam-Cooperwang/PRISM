# Live Provider Smoke Test V1

## Objective

Provide a manual, read-only, fail-closed entry point that performs one real The Odds API V4 market acquisition for a specific football match and emits a secret-free diagnostic summary.

## Scope

The smoke test validates only the live provider boundary:

```text
MatchTarget
→ secure runtime configuration
→ TheOddsApiV4MarketClient
→ real HTTP acquisition
→ SourceEnvelope
→ secret-free smoke summary
```

It does not execute betting actions, promotion, or release decisions.

## Inputs

The manual smoke test requires:

- home team name;
- away team name;
- competition label;
- timezone-aware kickoff timestamp;
- optional sport key override;
- optional bookmaker key override.

The API key is supplied only through the `THE_ODDS_API_KEY` runtime secret.

## Governance

- Missing or blank API credentials fail closed before HTTP execution.
- Provider HTTP/schema failures fail closed.
- No synthetic odds or fallback values are generated.
- API credentials must never appear in stdout, summary payloads, artifacts, repr output, or committed fixtures.
- The smoke test is manual and read-only.

## Output

The smoke summary may include:

- request and match identity;
- provider/source identity;
- retrieval and observation timestamps;
- home/draw/away decimal odds;
- configured sport and bookmaker keys.

It must not include credentials or raw authenticated request URLs.

## Acceptance

V1 is complete when:

1. a reusable smoke-test function returns a secret-free summary from a provider client;
2. a CLI can construct a match target and runtime configuration from safe inputs;
3. a manual GitHub Actions workflow can run the CLI with a repository secret;
4. fixture-backed tests prove output shape, fail-closed behavior, and secret redaction; and
5. CI does not require a real API key or live network access.
