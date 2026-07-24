# Benchmark Promotion Gate V1

## Purpose

Convert an already-governed `BenchmarkComparison` into a deterministic release-governance decision. The gate does not recompute benchmark metrics.

## Decisions

- `promote`: candidate satisfies every required promotion condition.
- `hold`: evidence is insufficient or improvement is not yet demonstrated, but no hard regression is present.
- `reject`: a hard governance condition fails.

## Default policy

- Minimum matched cases: 100.
- Required comparable metrics: `mean_brier_score`, `mean_log_loss`, `top1_accuracy`.
- No required metric may regress.
- `mean_brier_score` must improve by at least `0.001` in the favorable direction (baseline - candidate).
- The governed comparison overall verdict must be `improved`.
- Descriptive metrics, including confidence, never qualify a candidate for promotion and never reject it by themselves.
- Optional metrics such as scoreline/candidate accuracy may contribute evidence when comparable, but V1 does not require them.

## Evaluation order

1. Validate policy.
2. Reject if a required metric is missing from the comparison.
3. Hold if case count is below the policy minimum.
4. Hold if a required metric is `not_comparable`.
5. Reject if any required metric is `regressed`.
6. Hold if Brier improvement is below the minimum threshold.
7. Hold unless the comparison overall verdict is `improved`.
8. Otherwise `promote`.

## Result

The immutable result contains:

- `decision`;
- `case_count`;
- `reasons` in deterministic evaluation order;
- `required_metrics`;
- `brier_improvement` when comparable;
- `policy_version = "1.0.0"`.

Every non-promote result must contain at least one explicit reason. Promotion also records a positive reason so audit output is self-explanatory.
