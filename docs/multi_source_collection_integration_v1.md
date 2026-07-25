# PRISM Multi-Source Collection Integration V1

## Objective

Prove and expose one governed path that combines multiple independent provider adapters for the same match and feeds their observations into the existing automated prediction stack.

## Pipeline

```text
MatchTarget + ObservationAdapter[] + SourceEnvelope[]
        ↓
collect_observations()
        ↓
Observation[]
        ↓
build_intelligence_bundle()
        ↓
run_baseline_prediction_path()
        ↓
FeatureVector + ModelOutput[] + Consensus
```

## V1 adapter set

The integration acceptance path uses the currently implemented provider-neutral adapters:

- `MarketOdds1X2Adapter`;
- `TeamStrengthFormAdapter`;
- `AvailabilityScheduleAdapter`;
- `WeatherLineupAdapter`.

## Governance principles

1. The integration layer orchestrates existing modules; it does not duplicate verification, feature, model, or consensus logic.
2. Collection remains deterministic regardless of envelope ordering.
3. Duplicate observation identifiers and missing adapter configuration continue to fail closed in the collection runner.
4. The bundle collection timestamp must be explicit and timezone-aware.
5. The bundle must not be created before any collected observation timestamp.
6. Source provenance and intelligence/feature fingerprints must survive through model outputs.
7. Re-running the same frozen inputs must return identical observations, bundle fingerprint, feature fingerprint, model outputs, and consensus.
8. Missing or conflicted upstream claims remain governed by the existing verification and readiness rules rather than being repaired by the integration layer.

## Output contract

`run_collected_prediction_path()` returns one auditable result containing:

- collected observations;
- the verified `IntelligenceBundle`;
- the existing `PredictionPathResult` produced by the baseline prediction path.

The helper is intentionally provider-neutral and remains compatible with future adapters that implement the existing `ObservationAdapter` protocol.
