# PRISM Scoreline Engine Specification

Status: Draft
Version: 1.0.0

## 1. Purpose

The Scoreline Engine converts model-provided expected-goal estimates into a transparent scoreline probability distribution for presentation and downstream reporting.

It is an output layer, not a decision authority. It must run after the Decision Engine and must not modify consensus, confidence, rules, adjustment, or decision outputs.

## 2. Scientific Boundary

A 1X2 probability vector does not uniquely determine an exact-score distribution. Therefore PRISM V1 must not infer scorelines from 1X2 probabilities alone.

Scoreline prediction is available only when at least one model output provides both `expected_home_goals` and `expected_away_goals`.

## 3. V1 Method

1. Select model outputs that provide both expected-goal values.
2. Compute the equal-weight arithmetic mean of home expected goals and away expected goals.
3. Use independent Poisson distributions for home and away goals.
4. Evaluate the joint score grid from 0 through 10 goals for each team.
5. Rank scorelines by joint probability using deterministic tie-breaking: lower total goals, then lower home goals, then lower away goals.
6. Return the three highest-probability scorelines.
7. Report probability mass outside the evaluated grid as `tail_mass`.

The independent Poisson assumption is a baseline modelling assumption and must be identified in the output method and rationale. It is not treated as a proven description of football scoring dependence.

## 4. Output Contract

`ScorelineOutput` contains:

- `available`
- `method`
- `source_model_ids`
- `expected_home_goals`
- `expected_away_goals`
- `top_scorelines`
- `grid_probability_mass`
- `tail_mass`
- `rationale`

Each `ScorelineCandidate` contains:

- `home_goals`
- `away_goals`
- `probability`

When expected-goal inputs are unavailable, the engine returns `available = false`, empty candidates, and an explicit rationale rather than fabricating scoreline probabilities.

## 5. Governance

The Scoreline Engine:

- runs after Decision;
- never changes DecisionAction;
- never promotes `NO_BET`, `WATCH`, or `NO_DECISION` to `CANDIDATE`;
- never creates expected-goal values from odds or 1X2 consensus;
- remains deterministic for identical inputs.

## 6. Acceptance Criteria

The engine is accepted when automated tests verify:

1. missing xG produces an unavailable output;
2. one or more valid xG sources produce Top 3 scorelines;
3. source model IDs are auditable;
4. probabilities are finite and bounded;
5. grid mass plus tail mass equals one within tolerance;
6. input MatchContext remains immutable;
7. Scoreline runs after Decision in the canonical orchestrator.
