"""End-to-end pre-match prediction path built from existing governed PRISM modules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.consensus.engine import ConsensusEngine
from src.domain.models import MatchContext, ModelOutput
from src.features import FeatureVector, build_feature_vector
from src.intelligence.models import IntelligenceBundle
from src.intelligence.normalization import (
    NormalizedIntelligenceFacts,
    normalize_intelligence_bundle,
    normalize_intelligence_facts,
)
from src.prediction.baselines import EloProbabilityModel, MarketProbabilityModel
from src.prediction.runner import run_model_suite
from src.runtime.request import build_match_context


@dataclass(frozen=True)
class PredictionPathResult:
    """Auditable artifacts produced by one deterministic pre-match prediction path."""

    normalized_facts: NormalizedIntelligenceFacts
    features: FeatureVector
    model_outputs: tuple[ModelOutput, ...]
    context: MatchContext


def run_baseline_prediction_path(
    bundle: IntelligenceBundle,
    *,
    prism_version: str,
    session_id: str | None = None,
    created_at: datetime | None = None,
) -> PredictionPathResult:
    """Run verified intelligence through baseline models and the existing Consensus Engine."""

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
    )
    context = ConsensusEngine().run(context)
    if context.consensus is None:
        raise RuntimeError("Consensus Engine completed without consensus output")
    return PredictionPathResult(
        normalized_facts=facts,
        features=features,
        model_outputs=model_outputs,
        context=context,
    )
