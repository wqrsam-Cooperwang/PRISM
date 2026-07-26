# Live Market → Full Production Path V1

## Objective

Connect the real The Odds API V4 market client to PRISM's existing provider-to-report production path without bypassing collection governance.

## Architecture

```text
ProviderFetchRequest
        ↓
OddsProviderRuntimeConfig
        ↓
TheOddsApiV4MarketClient
        ↓
real market SourceEnvelope
        +
supplemental ProviderClient[]
        ↓
run_acquired_prediction_path()
        ↓
Verification / Readiness / Features / Models
        ↓
Consensus / Governance / Scoreline / PredictionReport
```

## Governance

The live market connector is not sufficient by itself to authorize a production prediction. Existing collection readiness rules remain authoritative.

- Real market data + required team-strength data may proceed.
- Missing required baseline inputs must fail closed.
- No synthetic Elo, form, injury, schedule, lineup, weather, or other facts may be invented to make a live run pass.
- Secrets remain runtime-only and are never copied into prediction artifacts.

## Contract

`run_live_market_prediction_path()` builds the real market client from validated runtime configuration, adds it to any supplemental provider clients, ensures the canonical market adapter is present, then delegates to `run_acquired_prediction_path()`.

The returned object is the existing `FullAutomatedPredictionResult`; no parallel report model is introduced.

## Acceptance

V1 is complete when tests prove:

1. a real-market fixture response can enter the complete production path when supplemental required inputs are present;
2. the real market odds are present in the canonical observations/features;
3. the final prediction report is generated through the existing runtime;
4. market-only live execution is rejected by the existing collection gate; and
5. the provider secret is absent from returned production artifacts.
