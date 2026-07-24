# GitHub CI Promotion Enforcement V1

## Purpose

Enforce the governed PRISM Benchmark Promotion Gate in a dedicated GitHub Actions workflow without changing ordinary CI behavior.

## Boundaries

- Existing CI remains responsible for lint, formatting, typing, tests and coverage.
- Promotion enforcement is a separate manually triggered workflow in V1.
- The workflow consumes two frozen JSONL evaluation datasets available in the checked-out workspace: baseline and candidate.
- Dataset comparison must use the existing importer, benchmark comparator and promotion gate. The workflow must not duplicate governance logic.

## CLI contract

`scripts/promotion_gate.py BASELINE CANDIDATE OUTPUT_DIR`

Optional arguments:

- `--minimum-case-count` (default `100`)
- `--minimum-brier-improvement` (default `0.001`)

Outputs written before returning the governed exit code:

- `comparison.json`
- `comparison.md`
- `promotion-decision.json`
- `promotion-decision.md`

Exit codes:

- `0`: PROMOTE
- `2`: HOLD
- `3`: REJECT
- `1`: execution/configuration/input failure

## Workflow contract

The workflow:

1. checks out the selected ref;
2. installs PRISM;
3. executes the promotion CLI while capturing its governed exit code;
4. always uploads the report directory as an artifact;
5. performs a final enforcement step that exits with the captured code.

This ordering guarantees that HOLD/REJECT decisions remain auditable even though the workflow ultimately fails.

## Security and evolution

V1 accepts repository/workspace paths only. Remote URLs and arbitrary network fetching are explicitly out of scope. External benchmark storage can later be integrated by a trusted download step without changing the CLI or governance logic.
