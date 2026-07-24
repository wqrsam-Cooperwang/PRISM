# PRISM Real Match Evaluation Harness V1

## Purpose

Real Match Evaluation Harness evaluates completed historical matches without changing the prediction runtime.
It consumes only pre-match PRISM inputs plus the final observed result, executes the normal governed prediction path, and scores the prediction after the fact.

## Non-leakage rule

Observed final scores and any post-match information must never be passed into `MatchRequest`, model outputs, evidence completeness, rules, confidence, decision, or scoreline generation.
The observed result is supplied only to the evaluation layer after the governed prediction has completed.

## Evaluation case

Each `EvaluationCase` contains:

- `case_id`
- pre-match `MatchRequest`
- evidence completeness mapping
- PRISM version
- observed home goals
- observed away goals
- optional deterministic session/provenance metadata

Observed goals must be non-negative integers.

## Single-match metrics

### Actual outcome

- `home` when home goals > away goals
- `draw` when home goals == away goals
- `away` when home goals < away goals

### Multiclass Brier score

For consensus probabilities `(p_home, p_draw, p_away)` and one-hot observed outcome `(y_home, y_draw, y_away)`:

`Brier = Σ (p_i - y_i)^2`

Range is `[0, 2]`; lower is better.

### Log loss

`LogLoss = -ln(p_actual)`

For numerical safety only, `p_actual` is clipped to `[1e-15, 1]` during scoring. This clipping does not change the underlying PRISM prediction.

### Top-1 correctness

`True` when consensus `leading_outcome` equals the observed outcome. A consensus tie is never counted as correct.

### Scoreline Top-3 hit

- `True` when the observed exact score appears in the governed Top 3 scorelines.
- `False` when scorelines are available but the observed score is absent.
- `None` when governed scoreline output is unavailable.

### Candidate decision correctness

Only `DecisionAction.CANDIDATE` cases are scored.

- `True` when `selected_market` equals the observed `home`, `draw`, or `away` outcome.
- `False` when a candidate market is present but differs from the observed outcome.
- `None` for non-candidate decisions or missing/non-1X2 selected markets.

No betting return, stake sizing, or bankroll metric is introduced in V1.

## Evaluation result

Each `EvaluationResult` retains:

- case id and match id
- actual score and actual outcome
- consensus probabilities
- leading outcome and leading probability
- Brier score
- log loss
- Top-1 correctness
- scoreline Top-3 hit
- decision action
- selected market
- candidate correctness
- confidence and evidence gate
- the immutable governed `PredictionReport`

The retained leading probability plus correctness flag is calibration-ready data for later calibration analysis.

## Batch summary

`EvaluationSummary` contains:

- case count
- mean Brier score
- mean log loss
- Top-1 accuracy
- scoreline available count
- scoreline Top-3 hit rate over available scoreline cases only
- candidate count
- candidate accuracy over scorable candidate cases only
- mean overall confidence
- per-case immutable results

Rates with zero eligible cases are represented as `None`, never silently as zero.

## V1 API

```python
RealMatchEvaluationHarness.evaluate(case: EvaluationCase) -> EvaluationResult
RealMatchEvaluationHarness.evaluate_many(cases: Iterable[EvaluationCase]) -> EvaluationSummary
```

## Governance invariants

1. Harness calls the same production `analyze_match_report()` path used by normal PRISM analysis.
2. Harness must not instantiate alternative analytical engines or recalculate prediction values.
3. Actual results are inaccessible to the prediction path.
4. Evaluation is deterministic for deterministic inputs and session metadata.
5. Batch evaluation preserves input case order.
6. Empty batches are rejected.
7. Metrics are descriptive evaluation outputs, not automatic model or rule updates.
8. V1 performs no calibration fitting, threshold tuning, hyperparameter search, or rule mutation.
