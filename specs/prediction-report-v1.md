# PRISM Prediction Report V1

## Purpose

Prediction Report is the read-only presentation boundary for a completed PRISM runtime.
It must not recalculate probabilities, confidence, expected value, rule effects, or scorelines.
Every report field is a projection of an already-governed canonical output.

## Input

A successful `RuntimeResult` produced by the application service after Scoreline Engine attachment.

## Required sections

### Match

- match id
- competition
- kickoff
- home team
- away team

### Consensus

- home probability
- draw probability
- away probability
- leading outcome
- model agreement
- model count

### Confidence

- overall confidence
- confidence band
- penalties

### Evidence

- evidence score
- evidence gate
- warnings
- missing categories
- critical caps applied

### Decision

- action
- selected market
- expected value
- risk level
- rationale

### Adjustment and rules

- base confidence
- adjusted confidence
- confidence cap
- decision blocked
- applied effects
- observed effects
- rule outputs exactly as emitted by the governed rule engine

### Scoreline

- availability
- method
- expected home goals
- expected away goals
- top three exact-score candidates and their probabilities
- source model ids
- grid probability mass
- tail mass

### Provenance

- PRISM version
- schema version
- runtime version
- session id
- git commit
- data version
- rule version
- model version
- prompt version
- AI models
- completed engine trace

## Governance invariants

1. Report generation is deterministic and side-effect free.
2. Report generation never invokes an analytical engine.
3. Report generation never changes ranking, probability, confidence, EV, or decision semantics.
4. Missing optional canonical outputs remain `null` or empty; the report must not infer replacements.
5. Enum values are serialized using their canonical string values.
6. Datetimes are serialized as ISO-8601 strings.
7. Rule outputs are copied as data and are not interpreted by the report layer.
8. Scoreline output is copied from `RuntimeResult.scoreline`; it is never regenerated.
9. Provenance must be sufficient to identify the runtime and analytical versions that produced the report.

## V1 API

```python
build_prediction_report(result: RuntimeResult) -> PredictionReport
build_prediction_report_dict(result: RuntimeResult) -> dict[str, Any]
```

`PredictionReport` is immutable. The dictionary representation is JSON-compatible.
