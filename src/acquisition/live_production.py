"""Real-market entry point for the governed PRISM production prediction path."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from src.acquisition.interface import ProviderClient
from src.acquisition.models import ProviderFetchRequest
from src.acquisition.production_path import run_acquired_prediction_path
from src.acquisition.runtime_config import (
    OddsProviderRuntimeConfig,
    build_the_odds_api_market_client,
)
from src.collection import MarketOdds1X2Adapter, ObservationAdapter
from src.connectors import HttpTransport, RetryPolicy
from src.decision.engine import DecisionEngine
from src.prediction.production_path import FullAutomatedPredictionResult


def run_live_market_prediction_path(
    request: ProviderFetchRequest,
    supplemental_clients: Iterable[ProviderClient],
    supplemental_adapters: Iterable[ObservationAdapter],
    *,
    collected_at: datetime,
    prism_version: str,
    environment: Mapping[str, str] | None = None,
    transport: HttpTransport | None = None,
    retry_policy: RetryPolicy | None = None,
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
    """Run the real odds provider plus supplemental providers through production."""

    config = OddsProviderRuntimeConfig.from_environment(environment)
    market_client = build_the_odds_api_market_client(
        config,
        transport=transport,
        retry_policy=retry_policy,
    )
    clients = (market_client, *tuple(supplemental_clients))
    adapters = (MarketOdds1X2Adapter(), *tuple(supplemental_adapters))
    return run_acquired_prediction_path(
        request,
        clients,
        adapters,
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
