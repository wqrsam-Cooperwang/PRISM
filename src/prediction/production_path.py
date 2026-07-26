"""Full automated provider-to-report production prediction orchestration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime

from src.collection.interface import ObservationAdapter
from src.collection.models import SourceEnvelope
from src.collection.readiness import (
    CollectionGateDecision,
    CollectionReadinessGateResult,
    apply_collection_governance,
    evaluate_collection_readiness,
)
from src.collection.runner import collect_observations
from src.decision.engine import DecisionEngine
from src.features import FeatureVector, build_feature_vector
from src.intelligence.models import IntelligenceBundle, MatchTarget, Observation
from src.intelligence.normalization import (
    normalize_intelligence_bundle,
    normalize_intelligence_facts,
)
from src.intelligence.pipeline import build_intelligence_bundle
from src.prediction.baselines import EloProbabilityModel, MarketProbabilityModel
from src.prediction.runner import run_model_suite
from src.report.builder import build_prediction_report
from src.report.models import PredictionReport
from src.runtime.factory import build_runtime
from src.runtime.orchestrator import RuntimeResult
from src.runtime.request import build_match_context
from src.scoreline.engine import ScorelineEngine


@dataclass(frozen=True)
class FullAutomatedPredictionResult:
    """Auditable artifacts from provider collection through final report."""

    observations: tuple[Observation, ...]
    intelligence_bundle: IntelligenceBundle
    collection_gate: CollectionReadinessGateResult
    features: FeatureVector
    runtime_result: RuntimeResult
    report: PredictionReport


def run_full_automated_prediction_path(
    target: MatchTarget,
    adapters: Iterable[ObservationAdapter],
    envelopes: Iterable[SourceEnvelope],
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
    """Run provider inputs through the complete governed PRISM production path."""

    observations = collect_observations(target, adapters, envelopes)
    bundle = build_intelligence_bundle(target, observations, collected_at=collected_at)
    gate = evaluate_collection_readiness(bundle)
    if gate.decision == CollectionGateDecision.REJECTED:
        reasons = "; ".join(gate.reasons) or "collection readiness gate rejected prediction"
        raise ValueError(f"Collection readiness gate rejected prediction: {reasons}")

    facts = normalize_intelligence_facts(bundle)
    features = build_feature_vector(facts)
    model_outputs = run_model_suite(
        (EloProbabilityModel(), MarketProbabilityModel()),
        features,
    )
    normalized = normalize_intelligence_bundle(bundle, model_outputs)
    context = build_match_context(
        normalized.request,
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
    context = apply_collection_governance(context, gate)

    runtime = build_runtime(
        normalized.evidence_completeness,
        decision_engine=decision_engine,
    ).run(context)
    scoreline = ScorelineEngine().run(runtime.context)
    runtime = replace(runtime, scoreline=scoreline)
    report = build_prediction_report(runtime)

    return FullAutomatedPredictionResult(
        observations=observations,
        intelligence_bundle=bundle,
        collection_gate=gate,
        features=features,
        runtime_result=runtime,
        report=report,
    )
