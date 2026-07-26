# Real Provider Runtime Configuration V1

## Objective

Allow PRISM to construct the real The Odds API V4 market provider from runtime
configuration without embedding secrets in source code, fixtures, reports, or
artifacts.

## Environment contract

Required:

- `THE_ODDS_API_KEY`

Optional:

- `PRISM_ODDS_SPORT_KEY`
- `PRISM_ODDS_BOOKMAKER_KEY`

The API key is secret-bearing configuration. It must be read only at runtime and
must not be copied into PRISM domain objects or prediction reports.

## Defaults

V1 provides explicit defaults suitable for the current K League 1 integration:

- sport key: `soccer_korea_kleague1`
- bookmaker key: `pinnacle`

Callers may override either value through the environment or explicit factory
arguments.

## Fail-closed rules

- missing `THE_ODDS_API_KEY` is an error;
- blank secret or configuration values are errors;
- environment values are stripped before use;
- the created provider client must keep the API key out of `repr`;
- tests must not require a real network call or real secret.

## Architecture

```text
process environment
      ↓
OddsProviderRuntimeConfig.from_environment()
      ↓
build_the_odds_api_market_client()
      ↓
TheOddsApiV4MarketClient
      ↓
existing acquisition and production path
```

The configuration layer contains no football-model logic and performs no HTTP
request itself.
