# Historical Benchmark Comparison V1

## Purpose

Compare two frozen PRISM historical benchmark datasets on the same evaluation cases.
The comparator is read-only: it must never re-run PRISM, mutate records, tune rules, or recalibrate models.

## Inputs

Two non-empty collections of `EvaluationRecord`:

- baseline records
- candidate records

Each collection represents one frozen PRISM evaluation run.

## Pairing invariant

The baseline and candidate datasets MUST contain exactly the same `case_id` set.
Duplicate `case_id` values within either dataset are invalid.
Comparison fails closed if the case sets differ.

## Metrics

V1 compares:

- mean Brier score (lower is better)
- mean Log Loss (lower is better)
- Top-1 accuracy (higher is better)
- Top-3 scoreline hit rate (higher is better, only when both datasets have the metric available)
- Candidate accuracy (higher is better, only when both datasets have the metric available)
- mean overall confidence (descriptive only; no winner is declared)

## Delta convention

For every metric:

`delta = candidate_value - baseline_value`

This convention is always preserved even for lower-is-better metrics.

## Winner semantics

Metric status is one of:

- `improved`
- `regressed`
- `tie`
- `not_comparable`
- `descriptive`

A configurable non-negative absolute tolerance is applied to avoid declaring meaningless floating-point differences as improvements.

For higher-is-better metrics:

- delta > tolerance => improved
- delta < -tolerance => regressed
- otherwise => tie

For lower-is-better metrics:

- delta < -tolerance => improved
- delta > tolerance => regressed
- otherwise => tie

Mean confidence is always `descriptive`.

## Overall verdict

V1 overall verdict is conservative and deterministic:

- `regressed` if any core scoring metric regresses
- `improved` if no core metric regresses and at least one improves
- `tie` if all comparable core metrics tie

Core scoring metrics are Brier, Log Loss, Top-1 accuracy, Top-3 scoreline hit rate, and Candidate accuracy.
Metrics marked `not_comparable` are ignored for the overall verdict.

## Output

`BenchmarkComparison` contains:

- shared case count
- baseline PRISM/runtime/git provenance sets
- candidate PRISM/runtime/git provenance sets
- ordered metric comparisons
- overall verdict

Each `MetricComparison` contains:

- metric name
- baseline value
- candidate value
- delta
- direction (`higher`, `lower`, or `descriptive`)
- status

## Constraints

1. Comparator never re-runs predictions.
2. Comparator never aligns datasets by row position; pairing identity is `case_id`.
3. Duplicate case IDs fail closed.
4. Different case ID sets fail closed.
5. Optional hit-rate metrics are comparable only if both datasets have a value.
6. Tolerance must be finite and non-negative.
7. Output is immutable and deterministic.
