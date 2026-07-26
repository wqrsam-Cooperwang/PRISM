# PRISM Exact Score Engine Specification

Status: Draft
Version: 2.1.0

## 1. Purpose

PRISM Exact Score V2.1 converts governed model outputs into an auditable exact-score distribution while controlling correlated evidence, static-score assumptions, and duplicated scoreline recommendations.

The scoreline layer remains downstream of Decision. It must never promote or change a betting decision.

## 2. Scientific Boundary

A 1X2 vector does not uniquely determine an exact-score distribution. V2.1 therefore requires one or more model outputs that supply both home and away expected goals.

Projected events are not confirmed events. Scenario components are modelling branches, not claims that a specific match state will occur.

## 3. Correlated Evidence Control

Models may share the same evidence family or latent assumption. V2.1 must prevent multiple highly correlated models from receiving the same voting power as independent evidence.

1. Every model belongs to an evidence family.
2. A model may declare `evidence_family` in diagnostics.
3. Otherwise deterministic fallbacks classify market, Elo, team-statistics, or model-specific families.
4. Each family receives at most one unit of aggregate voting mass before normalization.
5. Models inside a family divide that family mass.
6. Market-derived models therefore cannot multiply market evidence by appearing under multiple model IDs.
7. Effective family weights must be recorded in consensus rationale.

This implements the governance principle: evidence cannot vote twice.

## 4. Shared-Assumption Penalty for xG Sources

Expected-goal sources may also share a latent assumption. V2.1 applies the same family-cap principle when combining xG inputs.

A model may declare `assumption_family` in diagnostics. Otherwise its evidence family is used. This prevents several xG models built from substantially the same information from dominating the scoreline distribution.

## 5. Scenario-Mixture Scoreline Engine

V2.1 replaces the single static Poisson world with a deterministic mixture of conditional game-state scenarios.

The default scenario mixture is:

- balanced state: 54%;
- home scores first / away chases: 12%;
- away scores first / home chases: 12%;
- early-open game: 14%;
- symmetric defensive-tail floor: 8%.

Each scenario uses transparent Poisson marginals with scenario-specific rate adjustments. The final scoreline probability for each cell is the weighted sum across scenarios.

The symmetric defensive-tail component uses a minimum scoring rate for either team. Its purpose is not to assert that a weak attack is strong; it prevents the model from collapsing reverse-score tails to unrealistically negligible values.

Scenario weights and transforms are fixed, versioned defaults. They may only be changed through out-of-sample validation and a version change.

## 6. Dual-Score Diversity Selector

V2.1 distinguishes analytical Top 3 scorelines from the two formal recommended scorelines.

1. `top_scorelines` keeps the three highest raw mixture probabilities for audit and backward compatibility.
2. The first recommended score is the highest-probability scoreline.
3. The second score is chosen from remaining candidates using a diversity-adjusted score.
4. Candidates sharing the same result direction as the first score receive a shared-assumption penalty.
5. Candidates sharing the same clean-sheet structure receive an additional penalty.
6. The selector remains deterministic and never changes the underlying probability distribution.

The objective is coverage of a genuinely different match path rather than two adjacent scores supported by the same latent story.

## 7. Output Contract

`ScorelineOutput` contains:

- `available`
- `method`
- `source_model_ids`
- `expected_home_goals`
- `expected_away_goals`
- `top_scorelines`
- `recommended_scorelines`
- `grid_probability_mass`
- `tail_mass`
- `rationale`

When xG inputs are unavailable, the engine returns `available = false` and does not fabricate scoreline probabilities.

## 8. Governance

The V2.1 scoreline system:

- runs only after Decision;
- never changes DecisionAction;
- never infers xG from 1X2 probabilities alone;
- caps correlated evidence families;
- penalizes shared xG assumptions;
- preserves a symmetric defensive tail;
- treats game-state scenarios as probabilistic branches rather than confirmed events;
- preserves raw Top 3 probabilities for audit;
- emits exactly two diversified recommended scorelines;
- remains deterministic for identical inputs.

## 9. Acceptance Criteria

Automated tests must verify:

1. correlated model families have capped aggregate voting mass;
2. independent evidence families retain independent voting mass;
3. correlated xG sources cannot dominate xG aggregation by duplication;
4. scenario probabilities are normalized and deterministic;
5. reverse-score tails remain non-zero under highly asymmetric base xG;
6. Top 3 remains probability-ranked;
7. exactly two recommended scores are produced;
8. the second recommendation receives a penalty when it shares the first score's result direction or clean-sheet assumption;
9. grid mass plus tail mass equals one within tolerance;
10. missing xG remains fail-closed;
11. Decision and upstream governed outputs remain unchanged.
