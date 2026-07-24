"""One-shot application entrypoints for governed PRISM prediction reports."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from src.decision.engine import DecisionEngine
from src.report.builder import build_prediction_report
from src.report.models import PredictionReport
from src.runtime.application import analyze_match
from src.runtime.request import MatchRequest


def analyze_match_report(
    request: MatchRequest,
    completeness: Mapping[str, float],
    *,
    prism_version: str,
    decision_engine: DecisionEngine | None = None,
    session_id: str | None = None,
    created_at: datetime | None = None,
    git_commit: str | None = None,
    data_version: str | None = None,
    rule_version: str | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    operator: str | None = None,
    ai_models: tuple[str, ...] = (),
) -> PredictionReport:
    """Run the governed runtime once and project its immutable final report."""

    result = analyze_match(
        request,
        completeness,
        prism_version=prism_version,
        decision_engine=decision_engine,
        session_id=session_id,
        created_at=created_at,
        git_commit=git_commit,
        data_version=data_version,
        rule_version=rule_version,
        model_version=model_version,
        prompt_version=prompt_version,
        operator=operator,
        ai_models=ai_models,
    )
    return build_prediction_report(result)


def analyze_match_report_dict(
    request: MatchRequest,
    completeness: Mapping[str, float],
    *,
    prism_version: str,
    **metadata: Any,
) -> dict[str, Any]:
    """Run PRISM once and return the immutable final report as JSON-compatible data."""

    return analyze_match_report(
        request,
        completeness,
        prism_version=prism_version,
        **metadata,
    ).to_dict()
