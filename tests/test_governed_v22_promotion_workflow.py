"""Contract tests for the governed V2.2 promotion enforcement workflow."""

from __future__ import annotations

from pathlib import Path


WORKFLOW = Path(".github/workflows/governed-v22-promotion-enforcement.yml")


def test_governed_v22_workflow_preserves_enforcement_contract() -> None:
    payload = WORKFLOW.read_text(encoding="utf-8")

    required_fragments = (
        "name: Governed V2.2 Promotion Enforcement",
        "python scripts/governed_v22_promotion_gate.py",
        '"$PREDICTION_ROOT"',
        '"$OUTCOME_ROOT"',
        "governed-v22-promotion/governed-v22-promotion.json",
        'echo "exit_code=$gate_exit_code" >> "$GITHUB_OUTPUT"',
        "uses: actions/upload-artifact@v4",
        "name: governed-v22-promotion-decision",
        "if: always()",
        'GATE_EXIT_CODE: ${{ steps.gate.outputs.exit_code }}',
        'exit "$GATE_EXIT_CODE"',
    )
    for fragment in required_fragments:
        assert fragment in payload


def test_governed_v22_workflow_defaults_to_formal_ledger_paths_and_30_cases() -> None:
    payload = WORKFLOW.read_text(encoding="utf-8")

    assert "default: data/performance-ledger" in payload
    assert "default: data/outcome-ledger" in payload
    assert payload.count('default: "30"') == 2
