"""Human- and machine-readable reporting for PRISM V2.2 A/B governance."""

from __future__ import annotations

import json
from dataclasses import asdict

from src.regression.v22_ab import V22ScorelineABSummary
from src.regression.v22_promotion import V22PromotionResult

V22_AB_REPORT_VERSION = "1.0.0"


def v22_ab_report_payload(
    summary: V22ScorelineABSummary,
    promotion: V22PromotionResult,
) -> dict[str, object]:
    """Return a stable JSON-ready report payload."""

    return {
        "report_version": V22_AB_REPORT_VERSION,
        "comparison": asdict(summary),
        "promotion": promotion.to_dict(),
    }


def render_v22_ab_json(
    summary: V22ScorelineABSummary,
    promotion: V22PromotionResult,
) -> str:
    """Render deterministic pretty JSON."""

    return json.dumps(
        v22_ab_report_payload(summary, promotion),
        indent=2,
        sort_keys=True,
    )


def render_v22_ab_markdown(
    summary: V22ScorelineABSummary,
    promotion: V22PromotionResult,
) -> str:
    """Render concise governance-oriented Markdown."""

    lines = [
        "# PRISM Exact Score V2.2 Candidate A/B Report",
        "",
        f"Report version: `{V22_AB_REPORT_VERSION}`",
        f"Promotion policy: `{promotion.policy_version}`",
        "",
        "## Scoreline-layer benchmark",
        "",
        "| Metric | V2.1 | V2.2 candidate |",
        "| --- | ---: | ---: |",
        f"| Replay cases | {summary.case_count} | {summary.case_count} |",
        f"| Primary exact hits | {summary.v21_primary_hits} | {summary.v22_primary_hits} |",
        f"| Dual exact hits | {summary.v21_dual_hits} | {summary.v22_dual_hits} |",
        (
            "| Mean minimum score distance | "
            f"{summary.v21_mean_minimum_distance:.6f} | "
            f"{summary.v22_mean_minimum_distance:.6f} |"
        ),
        (
            "| Shared-story pairs | "
            f"{summary.v21_shared_story_pairs} | {summary.v22_shared_story_pairs} |"
        ),
        "",
        "## Case movement",
        "",
        f"- Improved distance: {summary.v22_distance_improved_cases}",
        f"- Worsened distance: {summary.v22_distance_worsened_cases}",
        f"- Tied distance: {summary.distance_tied_cases}",
        "",
        "## Promotion decision",
        "",
        f"**{promotion.decision.upper()}**",
        "",
        f"- Scoreline layer passed: {promotion.scoreline_layer_passed}",
        f"- Full-stack validation passed: {promotion.full_stack_validation_passed}",
        f"- Full-stack cases: {promotion.full_stack_case_count}",
    ]
    lines.extend(f"- Reason: {reason}" for reason in promotion.reasons)
    return "\n".join(lines) + "\n"
