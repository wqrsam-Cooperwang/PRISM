# PRISM Consensus Engine V1 Specification

## Purpose

The Consensus Engine combines multiple model probability distributions into one
auditable consensus distribution and measures model agreement. It does not make
a betting decision, infer market value, or apply hidden model weights.

## Scientific policy

V1 uses an equal-weight arithmetic mean because PRISM does not yet have a
validated historical calibration set that justifies differential model weights.
Any future weighted ensemble must be introduced through a new specification and
validated out of sample.

## Inputs

The engine reads `MatchContext.model_outputs`.

Each model must provide a valid home/draw/away probability distribution. Model
identifiers must be unique within one analysis context so that one model cannot
be accidentally counted more than once.

## Preconditions

- At least one model output is required.
- Duplicate `model_id` values are rejected.
- Probabilities are already validated by the canonical `ModelOutput` model.

## Consensus probabilities

For N models, each consensus probability is the arithmetic mean of that outcome
across all N models:

`P_consensus(outcome) = sum(P_model_i(outcome)) / N`

The resulting home/draw/away probabilities must sum to 1 within floating-point
tolerance.

## Agreement

For two probability vectors p and q, total variation distance is:

`TV(p, q) = 0.5 * sum(abs(p_i - q_i))`

For two or more models:

`agreement = 1 - mean(pairwise TV distance)`

Agreement therefore lies in [0, 1], where 1 means identical model probability
vectors.

For exactly one model, V1 reports agreement = 0.50 rather than 1.00. A single
model cannot demonstrate inter-model agreement, so PRISM preserves a neutral
uncertainty value instead of manufacturing certainty.

## Dispersion diagnostics

V1 records:

- `max_spread`: largest max-minus-min probability range among home/draw/away.
- `mean_pairwise_distance`: mean pairwise total variation distance; 0.50 for a
  single model to represent unavailable inter-model comparison.
- `margin`: difference between the highest and second-highest consensus
  probabilities.
- `leading_outcome`: home, draw, away, or tie.

## Output

The engine writes immutable `ConsensusOutput` to `MatchContext.consensus` with:

- model_count
- model_ids
- method (`equal_weight_mean`)
- home_probability
- draw_probability
- away_probability
- agreement
- mean_pairwise_distance
- max_spread
- leading_outcome
- margin
- rationale

## Confidence integration

When `MatchContext.consensus` is present, Confidence Engine must use
`consensus.agreement` as its consensus component. It may retain its previous
pairwise calculation only as a backward-compatible fallback for contexts that
have not yet run Consensus Engine.

The preferred production pipeline is:

`Evidence -> Consensus -> Confidence -> Rules -> Adjustment -> Decision`

## Non-goals

V1 does not:

- assign performance-based model weights;
- discard disagreeing models;
- use market odds as a model weight;
- infer scorelines;
- calculate expected value;
- make final decisions.

## Acceptance criteria

- Identical model distributions yield agreement 1.0.
- Strongly disagreeing models reduce agreement deterministically.
- A single model produces its own distribution with agreement 0.50.
- Duplicate model ids are rejected.
- Input context remains immutable.
- Confidence Engine consumes ConsensusOutput when available.
- Ruff, MyPy, unit tests, integration tests, and repository coverage gates pass.
