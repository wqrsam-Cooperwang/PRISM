"""Provider acquisition entry point for the full PRISM production path."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from src.acquisition.interface import ProviderClient
from src.acquisition.models import ProviderFetchRequest
from src.acquisition.runner import acquire_source_envelopes
from src.collection.interface import ObservationAdapter
from src.decision.engine import DecisionEngine
from src.prediction.production_path import (
    FullAutomatedPredictionResult,
    run_full_automated_prediction_path,
)


def run_acquired_prediction_path(
    request: ProviderFetchRequest,
    clients: Iterable[ProviderClient],
    adapters: Iterable[ObservationAdapter],
    *,
    collected_at: datetime,
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
) -> FullAutomatedPredictionResult:
    """Acquire provider envelopes and run the canonical production prediction path."""

    envelopes = acquire_source_envelopes(request, clients)
    return run_full_automated_prediction_path(
        request.target,
        adapters,
        envelopes,
        collected_at=collected_at,
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
