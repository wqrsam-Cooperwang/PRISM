"""Deterministic reporting and CI gate projection for promotion decisions."""

from __future__ import annotations

import json
from typing import Any

from src.evaluation.promotion import PromotionResult

PROMOTION_REPORT_VERSION = "1.0.0"


def release_gate_exit_code(result: PromotionResult) -> int:
    """Return the stable process exit code for a governed promotion decision."""

    if result.decision == "promote":
        return 0
    if result.decision == "hold":
        return 2
    return 3


def promotion_report_payload(result: PromotionResult) -> dict[str, Any]:
    """Build the deterministic machine-readable promotion report payload."""

    exit_code = release_gate_exit_code(result)
    return {
        "promotion_report_version": PROMOTION_REPORT_VERSION,
        "policy_version": result.policy_version,
        "decision": result.decision,
        "case_count": result.case_count,
        "required_metrics": list(result.required_metrics),
        "brier_improvement": result.brier_improvement,
        "reasons": list(result.reasons),
        "release_gate": {
            "allowed": exit_code == 0,
            "exit_code": exit_code,
        },
    }


def render_promotion_json(result: PromotionResult) -> str:
    """Render a stable JSON promotion report."""

    return json.dumps(
        promotion_report_payload(result),
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def render_promotion_markdown(result: PromotionResult) -> str:
    """Render a stable human-readable promotion report."""

    payload = promotion_report_payload(result)
    improvement = payload["brier_improvement"]
    improvement_text = "N/A" if improvement is None else f"{improvement:.6f}"
    allowed = "YES" if payload["release_gate"]["allowed"] else "NO"
    required = ", ".join(payload["required_metrics"])
    reasons = "\n".join(f"- {reason}" for reason in payload["reasons"])
    return (
        "# PRISM Benchmark Promotion Decision\n\n"
        f"Decision: **{result.decision.upper()}**\n\n"
        f"Policy version: `{result.policy_version}`  \n"
        f"Cases: **{result.case_count}**  \n"
        f"Required metrics: `{required}`  \n"
        f"Brier improvement: **{improvement_text}**  \n"
        f"Release allowed: **{allowed}**  \n"
        f"Release gate exit code: **{payload['release_gate']['exit_code']}**\n\n"
        "## Reasons\n\n"
        f"{reasons}\n"
    )
