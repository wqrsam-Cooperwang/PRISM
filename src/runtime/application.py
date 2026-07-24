"""High-level application service for one-shot PRISM match analysis."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from src.decision.engine import DecisionEngine
from src.runtime.factory import build_runtime
from src.runtime.orchestrator import RuntimeResult
from src.runtime.request import MatchRequest, build_match_context


def analyze_match(
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
) -> RuntimeResult:
    """Build canonical input, assemble production runtime, and execute it."""

    context = build_match_context(
        request,
        prism_version=prism_version,
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
    runtime = build_runtime(completeness, decision_engine=decision_engine)
    return runtime.run(context)


def analyze_match_dict(
    request: MatchRequest,
    completeness: Mapping[str, float],
    *,
    prism_version: str,
    **metadata: Any,
) -> dict[str, Any]:
    """Run PRISM and return its final canonical context as JSON-compatible data."""

    result = analyze_match(
        request,
        completeness,
        prism_version=prism_version,
        **metadata,
    )
    return result.context.to_dict()
