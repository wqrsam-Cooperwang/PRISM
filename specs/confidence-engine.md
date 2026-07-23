# Confidence Engine Specification

## Purpose

The Confidence Engine quantifies how much trust PRISM should place in the current analysis state. It does not predict match outcomes and does not issue betting or trading decisions.

## Responsibilities

- Convert evidence quality into an evidence-confidence component.
- Incorporate model availability as a model-confidence component.
- Incorporate contextual completeness as a context-confidence component.
- Incorporate model agreement as a consensus-confidence component when model outputs exist.
- Produce a bounded overall confidence score and a categorical confidence band.
- Apply conservative penalties when evidence is limited or rejected.
- Return a new immutable `MatchContext` with `confidence` attached.

## Inputs

The engine accepts a `MatchContext`.

Required input:

- `context.evidence`

Optional inputs:

- `context.model_outputs`
- contextual sections: `lineups`, `injuries`, `market`, `weather`, `schedule`, `tactical`

## Outputs

The engine returns a new `MatchContext` containing `ConfidenceOutput`:

- `evidence`: 0.0 to 1.0
- `model`: 0.0 to 1.0
- `context`: 0.0 to 1.0
- `consensus`: 0.0 to 1.0
- `overall`: 0.0 to 1.0
- `band`: one of `very_low`, `low`, `medium`, `high`, `very_high`
- `penalties`: applied conservative penalties
- `rationale`: auditable explanation strings

## Processing Flow

1. Require an existing `EvidenceOutput`.
2. Evidence component = `evidence.score / 100`.
3. Model component:
   - no models: 0.50 neutral baseline
   - one model: 0.65
   - two or more models: min(0.95, 0.70 + 0.05 * number_of_models)
4. Context component = share of six contextual sections that are non-empty.
5. Consensus component:
   - fewer than two models: 0.50 neutral baseline
   - otherwise measure average pairwise distance between each model's 1X2 probability vector and convert disagreement to confidence.
6. Weighted overall score:
   - evidence 45%
   - model 20%
   - context 20%
   - consensus 15%
7. Apply evidence-gate caps:
   - `deep`: no cap
   - `standard`: max 0.84
   - `limited`: max 0.64
   - `rejected`: max 0.34
8. Map overall score to band:
   - >= 0.85: very_high
   - >= 0.70: high
   - >= 0.50: medium
   - >= 0.35: low
   - otherwise: very_low

## Constraints

- All component and overall values must remain within [0.0, 1.0].
- The engine must not mutate the supplied `MatchContext`.
- The engine must not issue a decision.
- Rejected evidence must never produce medium-or-higher confidence.
- Confidence is an audit/control signal, not a probability that a prediction will be correct.

## Error Handling

- Missing evidence raises `ValueError`.
- Invalid domain objects are rejected by the canonical domain model.

## Acceptance Criteria

- High-quality evidence and complete context can produce high confidence.
- Limited evidence caps overall confidence at 0.64.
- Rejected evidence caps overall confidence at 0.34.
- More agreeing models increase consensus confidence.
- Strong model disagreement decreases consensus confidence.
- The original context remains unchanged.
- Engine conforms to the shared `Engine` protocol.
