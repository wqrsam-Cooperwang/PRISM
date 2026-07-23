from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from src.adjustment.engine import AdjustmentEngine
from src.confidence.engine import ConfidenceEngine
from src.consensus.engine import ConsensusEngine
from src.decision.engine import DecisionEngine
from src.domain.models import (
    AnalysisSession,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.evidence.context_engine import EvidenceEngine
from src.rules.engine import RuleEngine
from src.runtime.orchestrator import OrchestrationError, PrismOrchestrator


def build_context(*, with_models: bool = True) -> MatchContext:
    models = ()
    if with_models:
        models = (
            ModelOutput("poisson", "1.0.0", 0.58, 0.24, 0.18),
            ModelOutput("bayesian", "1.0.0", 0.54, 0.26, 0.20),
        )
    return MatchContext(
        session=AnalysisSession(
            session_id="runtime-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="runtime-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("home", "Home FC"),
        away_team=TeamInfo("away", "Away FC"),
        market={"home_odds": 2.0, "draw_odds": 4.2, "away_odds": 6.0},
        model_outputs=models,
    )


def evidence_engine() -> EvidenceEngine:
    return EvidenceEngine(
        {
            "lineup": 1.0,
            "injuries": 1.0,
            "odds": 1.0,
            "weather": 1.0,
            "tactical_data": 1.0,
            "historical_data": 1.0,
            "market_data": 1.0,
            "motivation": 1.0,
        }
    )


def test_standard_orchestrator_runs_full_canonical_runtime() -> None:
    original = build_context()
    result = PrismOrchestrator.standard(evidence_engine()).run(original)

    assert original.evidence is None
    assert original.consensus is None
    assert original.confidence is None
    assert original.rule_outputs == ()
    assert original.adjustment is None
    assert original.decision is None

    final = result.context
    assert final.evidence is not None
    assert final.consensus is not None
    assert final.confidence is not None
    assert final.adjustment is not None
    assert final.decision is not None
    assert tuple(item.name for item in result.engine_trace) == (
        "evidence",
        "consensus",
        "confidence",
        "rules",
        "adjustment",
        "decision",
    )
    assert all(item.status == "completed" for item in result.engine_trace)
    assert result.runtime_version == "1.0.0"


def test_preflight_rejects_missing_models_before_evidence_runs() -> None:
    context = build_context(with_models=False)
    with pytest.raises(ValueError, match="at least one model output"):
        PrismOrchestrator.standard(evidence_engine()).run(context)
    assert context.evidence is None


@dataclass
class PassthroughEngine:
    name: str
    version: str = "1.0.0"

    def run(self, context: MatchContext) -> MatchContext:
        return context


def test_invalid_sequence_is_rejected() -> None:
    engines = (
        PassthroughEngine("consensus"),
        PassthroughEngine("evidence"),
        PassthroughEngine("confidence"),
        PassthroughEngine("rules"),
        PassthroughEngine("adjustment"),
        PassthroughEngine("decision"),
    )
    with pytest.raises(ValueError, match="canonical sequence"):
        PrismOrchestrator(engines)


def test_duplicate_engine_names_are_rejected() -> None:
    engines = (
        PassthroughEngine("evidence"),
        PassthroughEngine("consensus"),
        PassthroughEngine("confidence"),
        PassthroughEngine("rules"),
        PassthroughEngine("rules"),
        PassthroughEngine("decision"),
    )
    with pytest.raises(ValueError, match="must be unique"):
        PrismOrchestrator(engines)


def test_empty_engine_metadata_is_rejected() -> None:
    engines = (
        PassthroughEngine("evidence", ""),
        PassthroughEngine("consensus"),
        PassthroughEngine("confidence"),
        PassthroughEngine("rules"),
        PassthroughEngine("adjustment"),
        PassthroughEngine("decision"),
    )
    with pytest.raises(ValueError, match="non-empty version"):
        PrismOrchestrator(engines)


class FailingRuleEngine:
    name = "rules"
    version = "9.9.9-test"

    def run(self, context: MatchContext) -> MatchContext:
        raise RuntimeError("synthetic rule failure")


def test_engine_failure_preserves_partial_context_and_trace() -> None:
    orchestrator = PrismOrchestrator(
        (
            evidence_engine(),
            ConsensusEngine(),
            ConfidenceEngine(),
            FailingRuleEngine(),
            AdjustmentEngine(),
            DecisionEngine(),
        )
    )

    with pytest.raises(OrchestrationError) as captured:
        orchestrator.run(build_context())

    error = captured.value
    assert error.engine_name == "rules"
    assert error.engine_version == "9.9.9-test"
    assert tuple(item.name for item in error.completed_trace) == (
        "evidence",
        "consensus",
        "confidence",
    )
    assert error.partial_context.evidence is not None
    assert error.partial_context.consensus is not None
    assert error.partial_context.confidence is not None
    assert error.partial_context.rule_outputs == ()
    assert isinstance(error.__cause__, RuntimeError)


def test_standard_runtime_accepts_decision_engine_override() -> None:
    custom_decision = DecisionEngine(
        minimum_adjusted_confidence=0.0,
        minimum_expected_value=-1.0,
        minimum_consensus_margin=0.0,
    )
    orchestrator = PrismOrchestrator.standard(
        evidence_engine(),
        decision_engine=custom_decision,
    )
    assert orchestrator.engines[-1] is custom_decision
    assert orchestrator.run(build_context()).context.decision is not None
