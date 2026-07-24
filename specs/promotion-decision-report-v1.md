# Promotion Decision Report & Release Gate V1

## Purpose

Project an immutable `PromotionResult` into deterministic human-readable and machine-readable release-governance output.

## Outputs

### JSON

The JSON payload contains:

- `promotion_report_version = "1.0.0"`;
- `policy_version`;
- `decision`;
- `case_count`;
- `required_metrics`;
- `brier_improvement`;
- `reasons`;
- `release_gate` containing `allowed` and `exit_code`.

### Markdown

The Markdown report exposes the same governed facts for audit/review. Rendering must be deterministic.

## Release gate contract

- `promote` => allowed, exit code `0`.
- `hold` => blocked, exit code `2`.
- `reject` => blocked, exit code `3`.

Exit code `1` is intentionally reserved for execution/configuration errors outside the governed promotion decision.

The release gate never recomputes benchmark metrics and never overrides the Promotion Gate decision.
