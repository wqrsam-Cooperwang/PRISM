# Historical Benchmark Comparison Report V1

## Purpose

Project a frozen `BenchmarkComparison` into deterministic human-readable Markdown and machine-readable JSON without changing comparison semantics.

## Requirements

1. Reporting is read-only. Renderers MUST NOT recompute benchmark metrics or verdicts.
2. Markdown and JSON MUST preserve:
   - case count;
   - baseline and candidate PRISM/runtime/git provenance;
   - every metric name, baseline value, candidate value, delta, direction, and status;
   - overall verdict.
3. JSON output MUST be deterministic and versioned with `comparison_report_version = "1.0.0"`.
4. Markdown output MUST be deterministic and contain a compact metric table.
5. `None` values MUST remain explicit (`null` in JSON and `N/A` in Markdown).
6. Confidence remains descriptive and MUST NOT be presented as a winning metric.
7. Renderers MUST accept only an already-governed `BenchmarkComparison`; they do not accept raw evaluation records.

## Markdown shape

The report contains:

- title and report version;
- baseline/candidate provenance;
- case count;
- metric table with baseline, candidate, delta, direction and status;
- overall verdict.

## JSON shape

Top-level keys:

- `comparison_report_version`
- `case_count`
- `baseline`
- `candidate`
- `metrics`
- `overall_verdict`

`baseline` and `candidate` contain sorted arrays for `prism_versions`, `runtime_versions`, and `git_commits` as supplied by the comparison object.
