# PRISM Live Provider Acquisition Layer V1

## Objective

Introduce a provider-neutral acquisition boundary that can retrieve external match payloads and emit existing `SourceEnvelope` objects without changing adapters, verification, prediction models, governance, or reporting.

## Pipeline position

```text
MatchTarget
    ↓
ProviderClient
    ↓
SourceEnvelope[]
    ↓
Existing ObservationAdapter[]
    ↓
Full Automated Production Prediction Path
```

## V1 principles

1. Provider clients retrieve data; they do not interpret football meaning or make prediction decisions.
2. Every successful fetch must return an existing immutable `SourceEnvelope` with source identity, retrieval timestamp, adapter identity, and request identity preserved.
3. Provider-specific networking and authentication remain behind a common client protocol.
4. Missing or malformed provider responses fail closed and are never converted into fabricated payloads.
5. Client execution must be deterministic for the same fixture-backed responses.
6. Duplicate client identifiers and duplicate emitted envelope identities fail closed.
7. Acquisition does not retry silently in V1. Retry/backoff policy is an explicit later concern so failures remain observable.
8. Tests must not require live network access or secrets.

## Initial contract

V1 establishes:

- `ProviderFetchRequest`: immutable match-scoped acquisition request;
- `ProviderClient`: typed protocol implemented by provider-specific clients;
- `acquire_source_envelopes()`: deterministic multi-client acquisition runner;
- explicit `ProviderAcquisitionError` preserving provider/client identity;
- a fixture-backed provider client for offline acceptance tests;
- integration proof that acquired envelopes can enter the existing collection and prediction path without translation glue.

## Out of scope

- provider credentials and secret storage;
- HTTP libraries or SDK selection;
- retries, exponential backoff, and circuit breakers;
- rate-limit scheduling;
- provider-specific production endpoints;
- caching and persistence.
