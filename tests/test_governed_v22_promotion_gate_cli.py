"""CLI enforcement tests for the governed V2.2 promotion gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import governed_v22_promotion_gate as gate
from src.regression.v22_promotion import V22PromotionResult


def _result(decision: str) -> V22PromotionResult:
    return V22PromotionResult(
        decision=decision,
        scoreline_case_count=30,
        full_stack_case_count=30,
        scoreline_layer_passed=decision == "promote",
        full_stack_validation_passed=decision == "promote",
        reasons=() if decision == "promote" else (f"governed decision: {decision}",),
    )


@pytest.mark.parametrize(
    ("decision", "expected_exit_code"),
    (("promote", 0), ("hold", 2), ("reject", 3)),
)
def test_run_gate_persists_decision_before_returning_governed_exit_code(
    tmp_path: Path,
    monkeypatch,
    decision: str,
    expected_exit_code: int,
) -> None:
    prediction_root = tmp_path / "performance-ledger"
    outcome_root = tmp_path / "outcome-ledger"
    output_path = tmp_path / "reports" / "governed-v22-promotion.json"
    captured = {}

    def _evaluate(predictions, outcomes, *, policy):
        captured["predictions"] = predictions
        captured["outcomes"] = outcomes
        captured["policy"] = policy
        return _result(decision)

    monkeypatch.setattr(gate, "evaluate_governed_v22_promotion", _evaluate)

    exit_code = gate.run_gate(
        prediction_root,
        outcome_root,
        output_path,
        minimum_scoreline_cases=31,
        minimum_full_stack_cases=32,
    )

    assert exit_code == expected_exit_code
    assert captured["predictions"] == prediction_root
    assert captured["outcomes"] == outcome_root
    assert captured["policy"].minimum_scoreline_case_count == 31
    assert captured["policy"].minimum_full_stack_case_count == 32

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_version"] == "1.0.0"
    assert payload["decision"] == decision
    assert payload["gate"] == "governed_v22_promotion"
    assert payload["policy"] == {
        "version": "1.0.0",
        "minimum_scoreline_case_count": 31,
        "minimum_full_stack_case_count": 32,
        "require_full_stack_validation": True,
    }
    assert payload["provenance"] == {
        "prediction_root": str(prediction_root),
        "outcome_root": str(outcome_root),
    }
    assert payload["release_gate"] == {
        "allowed": decision == "promote",
        "exit_code": expected_exit_code,
    }
