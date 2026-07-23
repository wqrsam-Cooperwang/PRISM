# PRISM Orchestrator V1 Specification

## Purpose

The PRISM Orchestrator is the governed runtime entry point for one complete
analysis. It owns execution order, preflight validation, engine-version trace,
and failure boundaries. It does not replace individual engines and it does not
contain prediction logic.

The generic `Pipeline` remains available as a low-level composition utility.
The Orchestrator is the canonical application-level runtime.

## Canonical V1 order

1. Evidence
2. Consensus
3. Confidence
4. Rules
5. Adjustment
6. Decision

The order is fixed because downstream contracts depend on upstream outputs.

## Inputs

- An immutable `MatchContext`.
- A configured Evidence Engine instance.
- Optional engine overrides for testing or controlled runtime substitution.

V1 assumes `MatchContext.model_outputs` are already populated before the
runtime begins. Model generation is outside this orchestrator version.

## Preflight validation

Before executing any engine, V1 must reject a context when:

- no model outputs are available;
- engine names are duplicated;
- configured engines do not match the canonical V1 sequence;
- an engine does not expose a non-empty name or version.

Preflight failure must occur before any engine executes.

## Runtime result

A successful run returns a `RuntimeResult` containing:

- final immutable `MatchContext`;
- runtime version;
- ordered engine trace.

Each trace entry contains:

- engine name;
- engine version;
- status (`completed`).

V1 intentionally does not record wall-clock duration in the deterministic
result object.

## Failure boundary

If an engine raises an exception, the Orchestrator raises
`OrchestrationError` and preserves:

- failing engine name;
- failing engine version;
- completed engine trace;
- partial `MatchContext` produced by all successfully completed engines;
- original exception through Python exception chaining.

The Orchestrator must never silently skip a failed engine.

## Immutability

The input context is never mutated. Engines remain responsible for returning a
new context. The runtime result references the final context only after all
engines complete successfully.

## Non-goals for V1

- Model execution or model selection.
- Network/data acquisition.
- Retry policies.
- Parallel engine execution.
- Wall-clock performance telemetry.
- Persistence to a database.
- Automatic fallback after a failed engine.

These may be added only through later specifications.

## Acceptance criteria

1. Canonical six-engine execution succeeds end to end.
2. Engine trace records names and versions in exact execution order.
3. Preflight rejects missing model outputs before Evidence runs.
4. Invalid or duplicate engine configuration is rejected.
5. Engine failures produce an `OrchestrationError` with partial context and
   completed trace.
6. Original context remains unchanged.
7. Ruff, MyPy, tests, and coverage remain green.
