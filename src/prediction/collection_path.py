"""Multi-source collection orchestration into the existing PRISM prediction path."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime

from src.collection.degraded_governance import apply_collection_governance
from src.collection.interface import ObservationAdapter
from src.collection.models import SourceEnvelope
from src.collection.readiness import (
    CollectionGateDecision,
    CollectionReadinessGateResult,
    evaluate_collection_readiness,
)
from src.collection.runner import collect_observations
from src.intelligence.models import IntelligenceBundle, MatchTarget, Observation
from src.intelligence.pipeline import build_intelligence_bundle
from src.prediction.path import PredictionPathResult, run_baseline_prediction_path


@dataclass(frozen=True)
class CollectedPredictionPathResult:
    """Auditable artifacts from collection through baseline consensus."""

    observations: tuple[Observation, ...]
    intelligence_bundle: IntelligenceBundle
    collection_gate: CollectionReadinessGateResult
    prediction: PredictionPathResult


def run_collected_prediction_path(
    target: MatchTarget,
    adapters: Iterable[ObservationAdapter],
    envelopes: Iterable[SourceEnvelope],
    *,
    collected_at: datetime,
    prism_version: str,
    session_id: str | None = None,
    created_at: datetime | None = None,
) -> CollectedPredictionPathResult:
    """Collect provider facts and run the existing governed baseline prediction path."""

    observations = collect_observations(target, adapters, envelopes)
    bundle = build_intelligence_bundle(target, observations, collected_at=collected_at)
    gate = evaluate_collection_readiness(bundle)
    if gate.decision == CollectionGateDecision.REJECTED:
        reasons = "; ".join(gate.reasons) or "collection readiness gate rejected prediction"
        raise ValueError(f"Collection readiness gate rejected prediction: {reasons}")

    prediction = run_baseline_prediction_path(
        bundle,
        prism_version=prism_version,
        session_id=session_id,
        created_at=created_at,
    )
    prediction = replace(
        prediction,
        context=apply_collection_governance(prediction.context, gate),
    )
    return CollectedPredictionPathResult(
        observations=observations,
        intelligence_bundle=bundle,
        collection_gate=gate,
        prediction=prediction,
    )
