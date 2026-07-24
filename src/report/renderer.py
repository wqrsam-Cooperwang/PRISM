"""Deterministic Markdown rendering for governed PRISM prediction reports."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from src.report.models import PredictionReport


def _percent(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if signed:
        return f"{value:+.1%}"
    return f"{value:.1%}"


def _number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _text(value: str | None) -> str:
    return "N/A" if value is None else value


def _lines(values: Iterable[str]) -> str:
    items = tuple(values)
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _rule_lines(rule_outputs: tuple[Mapping[str, Any], ...]) -> str:
    if not rule_outputs:
        return "- None"
    return "\n".join(
        f"- {json.dumps(dict(item), sort_keys=True, ensure_ascii=False)}" for item in rule_outputs
    )


def render_prediction_report_markdown(report: PredictionReport) -> str:
    """Render a report without recalculating or changing analytical values."""

    sections: list[str] = [
        "# PRISM Prediction Report",
        "",
        "## Match",
        f"- Match ID: {report.match.match_id}",
        f"- Competition: {report.match.competition}",
        f"- Kickoff: {report.match.kickoff.isoformat()}",
        f"- Fixture: {report.match.home_team} vs {report.match.away_team}",
    ]

    sections.extend(["", "## 1X2 Consensus"])
    if report.consensus is None:
        sections.append("- Unavailable")
    else:
        consensus = report.consensus
        sections.extend(
            [
                f"- Home: {_percent(consensus.home_probability)}",
                f"- Draw: {_percent(consensus.draw_probability)}",
                f"- Away: {_percent(consensus.away_probability)}",
                f"- Leading outcome: {consensus.leading_outcome}",
                f"- Model agreement: {_percent(consensus.agreement)}",
                f"- Model count: {consensus.model_count}",
            ]
        )

    sections.extend(["", "## Confidence and Evidence"])
    if report.confidence is None:
        sections.append("- Confidence: Unavailable")
    else:
        sections.extend(
            [
                f"- Overall confidence: {_percent(report.confidence.overall)}",
                f"- Confidence band: {report.confidence.band}",
                "- Penalties:",
                _lines(report.confidence.penalties),
            ]
        )
    if report.evidence is None:
        sections.append("- Evidence: Unavailable")
    else:
        sections.extend(
            [
                f"- Evidence score: {report.evidence.score}/100",
                f"- Evidence gate: {report.evidence.gate}",
                "- Evidence warnings:",
                _lines(report.evidence.warnings),
                "- Missing categories:",
                _lines(report.evidence.missing_categories),
                "- Critical caps applied:",
                _lines(report.evidence.critical_caps_applied),
            ]
        )

    sections.extend(["", "## Decision"])
    if report.decision is None:
        sections.append("- Unavailable")
    else:
        expected_value = _percent(report.decision.expected_value, signed=True)
        sections.extend(
            [
                f"- Action: {report.decision.action}",
                f"- Selected market: {_text(report.decision.selected_market)}",
                f"- Expected value: {expected_value}",
                f"- Risk level: {_text(report.decision.risk_level)}",
                "- Rationale:",
                _lines(report.decision.rationale),
            ]
        )

    sections.extend(["", "## Top 3 Scorelines"])
    if report.scoreline is None or not report.scoreline.available:
        sections.append("- Unavailable")
    else:
        scoreline = report.scoreline
        sections.extend(
            [
                f"- Method: {scoreline.method}",
                f"- Expected goals: {_number(scoreline.expected_home_goals)} - "
                f"{_number(scoreline.expected_away_goals)}",
            ]
        )
        for index, candidate in enumerate(scoreline.top_scorelines, start=1):
            sections.append(
                f"- #{index}: {candidate.home_goals}-{candidate.away_goals} "
                f"({_percent(candidate.probability)})"
            )
        sections.extend(
            [
                f"- Source models: {', '.join(scoreline.source_model_ids)}",
                f"- Grid probability mass: {_percent(scoreline.grid_probability_mass)}",
                f"- Tail mass: {_percent(scoreline.tail_mass)}",
            ]
        )

    sections.extend(["", "## Rules and Adjustment"])
    if report.adjustment is None:
        sections.append("- Unavailable")
    else:
        adjustment = report.adjustment
        sections.extend(
            [
                f"- Base confidence: {_percent(adjustment.base_confidence)}",
                f"- Adjusted confidence: {_percent(adjustment.adjusted_confidence)}",
                f"- Confidence cap: {_percent(adjustment.confidence_cap)}",
                f"- Decision blocked: {str(adjustment.decision_blocked).lower()}",
                "- Applied effects:",
                _lines(adjustment.applied_effects),
                "- Observed effects:",
                _lines(adjustment.observed_effects),
                "- Rule outputs:",
                _rule_lines(adjustment.rule_outputs),
            ]
        )

    provenance = report.provenance
    ai_models = ", ".join(provenance.ai_models) if provenance.ai_models else "None"
    sections.extend(
        [
            "",
            "## Provenance",
            f"- PRISM version: {provenance.prism_version}",
            f"- Schema version: {provenance.schema_version}",
            f"- Runtime version: {provenance.runtime_version}",
            f"- Session ID: {provenance.session_id}",
            f"- Git commit: {_text(provenance.git_commit)}",
            f"- Data version: {_text(provenance.data_version)}",
            f"- Rule version: {_text(provenance.rule_version)}",
            f"- Model version: {_text(provenance.model_version)}",
            f"- Prompt version: {_text(provenance.prompt_version)}",
            f"- AI models: {ai_models}",
            "- Engine trace:",
        ]
    )
    sections.extend(
        f"- {item.name} {item.version} [{item.status}]" for item in provenance.engine_trace
    )
    if not provenance.engine_trace:
        sections.append("- None")

    return "\n".join(sections) + "\n"
