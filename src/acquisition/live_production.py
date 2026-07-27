"""Real-market entry points for governed PRISM production prediction paths."""

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
from src.ledger.formal import FormalPredictionResult, run_formal_acquired_prediction_path
from src.ledger.store import PredictionLedgerStore
from src.prediction.production_path import FullAutomatedPredictionResult


def _live_clients_and_adapters(
    supplemental_clients: Iterable[ProviderClient],
    supplemental_adapters: Iterable[ObservationAdapter],
    *,
    environment: Mapping[str, str] | None,
    transport: HttpTransport | None,
    retry_policy: RetryPolicy | None,
) -> tuple[tuple[ProviderClient, ...], tuple[ObservationAdapter, ...]]:
    config = OddsProviderRuntimeConfig.from_environment(environment)
    market_client = build_the_odds_api_market_client(
        config,
        transport=transport,
        retry_policy=retry_policy,
    )
    return (
        (market_client, *tuple(supplemental_clients)),
        (MarketOdds1X2Adapter(), *tuple(supplemental_adapters)),
    )


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
    """Run an exploratory live prediction without freezing a formal ledger record.

    This entry point is intentionally non-formal. Any prediction intended for
    publication, forward testing, regression evaluation, or later outcome review
    must use :func:`run_live_market_formal_prediction_path` so the pre-match
    snapshot is persisted before kickoff.
    """

    clients, adapters = _live_clients_and_adapters(
        supplemental_clients,
        supplemental_adapters,
        environment=environment,
        transport=transport,
        retry_policy=retry_policy,
    )
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


def run_live_market_formal_prediction_path(
    request: ProviderFetchRequest,
    supplemental_clients: Iterable[ProviderClient],
    supplemental_adapters: Iterable[ObservationAdapter],
    ledger_store: PredictionLedgerStore,
    *,
    collected_at: datetime,
    frozen_at: datetime,
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
) -> FormalPredictionResult:
    """Run a formal live prediction and fail closed unless its snapshot persists.

    This is the canonical live entry point for predictions that count toward
    forward testing or historical evaluation. It freezes the governed pre-match
    prediction, including the configured shadow scoreline output, into the
    prediction ledger before the result can be treated as formal.
    """

    clients, adapters = _live_clients_and_adapters(
        supplemental_clients,
        supplemental_adapters,
        environment=environment,
        transport=transport,
        retry_policy=retry_policy,
    )
    return run_formal_acquired_prediction_path(
        request,
        clients,
        adapters,
        ledger_store,
        collected_at=collected_at,
        frozen_at=frozen_at,
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
