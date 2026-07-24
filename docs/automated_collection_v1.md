# PRISM Automated Data Source Adapter / Collection V1

## Status

Initial contract for the next stage after the green end-to-end baseline prediction path.

## Objective

Replace manually constructed intelligence observations with deterministic, source-attributed observations produced by external data-source adapters, without changing verification, feature construction, prediction models, consensus, or downstream governance.

## Pipeline position

```text
External source payloads
        ↓
DataSourceAdapter
        ↓
Observation[]
        ↓
Existing verification pipeline
        ↓
IntelligenceBundle
        ↓
Existing end-to-end prediction path
```

## V1 principles

1. Adapters translate source payloads; they do not make prediction decisions.
2. Every emitted observation must preserve source identity and retrieval provenance.
3. Missing source fields remain missing; adapters must not invent or silently impute values.
4. Source-specific parsing is isolated behind a common adapter contract.
5. Adapter output must use the existing intelligence observation domain rather than a parallel data model.
6. Verification remains responsible for deciding whether collected claims are verified, provisional, conflicted, or unusable.
7. Deterministic source fixtures must be sufficient to test adapters without live network access.
8. Collection failures must fail explicitly and must not be converted into fabricated observations.

## Initial V1 scope

The first implementation should establish:

- a typed adapter protocol;
- a source payload/envelope carrying retrieval metadata;
- deterministic adapter execution helpers;
- fixture-backed tests;
- at least one simple reference adapter that maps source data into existing Observation objects;
- explicit duplicate/source identity governance.

Live provider credentials, scraping, scheduling, retry policy, and provider-specific production integrations are intentionally outside the first contract and can be added after the adapter boundary is stable.
