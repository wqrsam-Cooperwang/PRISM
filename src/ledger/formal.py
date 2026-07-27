"""Formal prediction orchestration with mandatory ledger persistence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.acquisition.interface import ProviderClient
from src.acquisition.models import ProviderFetchRequest
from src.acquisition.production_path import run_acquired_prediction_path
from src.collection.interface import ObservationAdapter
from src.decision.engine import DecisionEngine
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.shadow import build_v22_shadow_payload
from src.ledger.snapshot import build_prediction_snapshot
from src.ledger.store import PredictionLedgerStore
from src.prediction.production_path import FullAutomatedPredictionResult


@dataclass(frozen=True)
class FormalPredictionResult:
    """One production prediction that has been durably frozen in the ledger."""

    production: FullAutomatedPredictionResult
    snapshot: PredictionLedgerSnapshot
    ledger_path: Path


def run_formal_acquired_prediction_path(
    request: ProviderFetchRequest,
    clients: Iterable[ProviderClient],
    adapters: Iterable[ObservationAdapter],
    ledger_store: PredictionLedgerStore,
    *,
    collected_at: datetime,
    frozen_at: datetime,
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
) -> FormalPredictionResult:
    """Run production V2.1 and freeze a non-interfering V2.2 shadow prediction."""

    production = run_acquired_prediction_path(
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
    shadow = build_v22_shadow_payload(production.runtime_result.context)
    snapshot = build_prediction_snapshot(
        production.report,
        production.observations,
        production.collection_gate,
        production.features,
        frozen_at=frozen_at,
        model_outputs=production.runtime_result.context.model_outputs,
        shadow_predictions={"v2_2": shadow},
    )
    ledger_path = ledger_store.persist(snapshot)
    return FormalPredictionResult(
        production=production,
        snapshot=snapshot,
        ledger_path=ledger_path,
    )
