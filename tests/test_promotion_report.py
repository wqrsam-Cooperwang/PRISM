import json

from src.evaluation import (
    PromotionResult,
    promotion_report_payload,
    release_gate_exit_code,
    render_promotion_json,
    render_promotion_markdown,
)


def _result(decision: str) -> PromotionResult:
    reasons = {
        "promote": ("candidate satisfies Benchmark Promotion Gate V1",),
        "hold": ("case count 50 is below minimum 100",),
        "reject": ("required metrics regressed: mean_log_loss",),
    }
    return PromotionResult(  # type: ignore[arg-type]
        decision=decision,
        case_count=500 if decision != "hold" else 50,
        reasons=reasons[decision],
        required_metrics=("mean_brier_score", "mean_log_loss", "top1_accuracy"),
        brier_improvement=0.01 if decision != "hold" else None,
    )


def test_release_gate_exit_codes_are_stable() -> None:
    assert release_gate_exit_code(_result("promote")) == 0
    assert release_gate_exit_code(_result("hold")) == 2
    assert release_gate_exit_code(_result("reject")) == 3


def test_promotion_report_payload_contains_machine_gate_contract() -> None:
    payload = promotion_report_payload(_result("promote"))

    assert payload["promotion_report_version"] == "1.0.0"
    assert payload["policy_version"] == "1.0.0"
    assert payload["decision"] == "promote"
    assert payload["brier_improvement"] == 0.01
    assert payload["release_gate"] == {"allowed": True, "exit_code": 0}


def test_hold_and_reject_are_blocking() -> None:
    hold = promotion_report_payload(_result("hold"))
    reject = promotion_report_payload(_result("reject"))

    assert hold["release_gate"] == {"allowed": False, "exit_code": 2}
    assert reject["release_gate"] == {"allowed": False, "exit_code": 3}


def test_promotion_json_is_deterministic_and_machine_readable() -> None:
    first = render_promotion_json(_result("reject"))
    second = render_promotion_json(_result("reject"))

    assert first == second
    parsed = json.loads(first)
    assert parsed["decision"] == "reject"
    assert parsed["release_gate"]["exit_code"] == 3


def test_promotion_markdown_contains_decision_gate_and_reasons() -> None:
    rendered = render_promotion_markdown(_result("promote"))

    assert "# PRISM Benchmark Promotion Decision" in rendered
    assert "Decision: **PROMOTE**" in rendered
    assert "Cases: **500**" in rendered
    assert "Brier improvement: **0.010000**" in rendered
    assert "Release allowed: **YES**" in rendered
    assert "Release gate exit code: **0**" in rendered
    assert "- candidate satisfies Benchmark Promotion Gate V1" in rendered


def test_promotion_markdown_renders_missing_brier_as_na() -> None:
    rendered = render_promotion_markdown(_result("hold"))

    assert "Decision: **HOLD**" in rendered
    assert "Brier improvement: **N/A**" in rendered
    assert "Release allowed: **NO**" in rendered
    assert "Release gate exit code: **2**" in rendered
