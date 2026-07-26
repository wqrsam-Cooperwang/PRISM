# Acquisition → Full Production Path Integration V1

## Objective

Provide one governed application entry point that accepts a match-scoped
`ProviderFetchRequest` plus provider clients and observation adapters, acquires
source envelopes deterministically, and delegates those envelopes to the
existing Full Automated Production Prediction Path.

## Architecture

```text
ProviderFetchRequest + ProviderClient[]
                ↓
      acquire_source_envelopes()
                ↓
          SourceEnvelope[]
                ↓
run_full_automated_prediction_path()
                ↓
      FullAutomatedPredictionResult
                ↓
          PredictionReport
```

The integration layer is orchestration only. It must not duplicate collection,
verification, readiness, feature, model, consensus, governance, decision,
scoreline, or report logic.

## Contract

The public entry point receives:

- one immutable `ProviderFetchRequest`;
- provider clients implementing `ProviderClient`;
- observation adapters;
- the same production provenance/configuration arguments accepted by the
  existing full production path.

It returns the existing `FullAutomatedPredictionResult` unchanged so downstream
consumers retain one canonical production result type.

## Governance

- Acquisition failures remain fail-closed through `ProviderAcquisitionError`.
- Duplicate client IDs, request mismatches, and duplicate envelope identities
  remain governed by the acquisition runner.
- Collection readiness rejection remains governed by the existing production
  path.
- DEGRADED collection governance continues to flow through the canonical
  runtime and decision engines.
- No fallback or synthetic provider data is introduced by this integration.

## Determinism

For equivalent provider outputs, changing provider-client input order must not
change the acquired envelope ordering or downstream production artifacts.

## Acceptance

V1 is complete when fixture-backed integration tests prove that:

1. callers can supply clients instead of pre-built envelopes;
2. acquisition output enters the existing production path without glue code;
3. READY data reaches a final prediction report;
4. DEGRADED governance survives through the production runtime;
5. provider failure stops the path before prediction; and
6. provider-client ordering does not change canonical downstream artifacts.
