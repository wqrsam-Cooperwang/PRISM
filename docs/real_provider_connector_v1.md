# PRISM Real Provider Connector V1

## Objective

Introduce a real HTTP boundary between provider-specific clients and the existing acquisition layer without changing collection, verification, modeling, governance, or reporting.

## Architecture

```text
Provider Connector
      ↓
HTTP Transport
      ↓
Remote API
      ↓
HTTP Response
      ↓
Provider Connector
      ↓
SourceEnvelope[]
      ↓
Existing Acquisition / Production Path
```

## V1 contract

- `HttpRequest` and `HttpResponse` are immutable transport-domain objects.
- `HttpTransport` is a provider-neutral protocol.
- `StdlibHttpTransport` performs real network I/O using Python 3.12 standard library only.
- Retry behavior is deterministic and explicit; only configured retryable transport/status failures may be retried.
- Provider connectors remain responsible for endpoint construction, authentication headers, response schema validation, and translation into `SourceEnvelope` objects.
- Secrets are injected at runtime and must never be persisted into envelopes, logs, fixtures, or repository files.
- Non-success HTTP status, timeout/network errors, and invalid JSON/schema are fail-closed.
- No connector may fabricate or silently impute provider data.

## Error classes

V1 distinguishes:

- transport/network failure;
- HTTP status failure;
- response decoding failure;
- provider schema failure.

This classification is intended for auditability and later retry/monitoring policy, not for silent fallback.

## Retry policy

The retry wrapper may retry only:

- transport failures; and
- explicitly configured status codes such as 429, 500, 502, 503, and 504.

Client errors such as 400, 401, 403, and 404 fail immediately.

V1 uses attempt counts only; scheduling/backoff sleeps belong to a later operational layer.

## Acceptance

V1 is complete when offline tests prove request validation, real transport construction behavior, retry classification, JSON decoding, fail-closed errors, and deterministic fixture transport behavior without requiring live credentials or internet access.
