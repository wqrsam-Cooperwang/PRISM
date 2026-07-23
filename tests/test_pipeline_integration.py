from dataclasses import replace
from datetime import datetime, timezone

from src.adjustment.engine import AdjustmentEngine
from src.confidence.engine import ConfidenceEngine
from src.consensus.engine import ConsensusEngine
from src.core.pipeline import Pipeline
from src.decision.engine import DecisionEngine
from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    DecisionAction,
    EvidenceGate,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.evidence.context_engine import EvidenceEngine
from src.rules.engine import RuleEngine


def build_context() -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="integration-001",
            created_at=datetime(2026, 7, 23, 0, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="match-001",
            competition="Test League",
            kickoff=datetime(2026, 7, 24, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
    )


def model(model_id: str, home: float, draw: float, away: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
    )


def complete_evidence_engine() -> EvidenceEngine:
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


def test_pipeline_runs_evidence_engine_without_mutating_input() -> None:
    original = build_context()
    result = Pipeline([complete_evidence_engine()]).run(original)

    assert original.evidence is None
    assert result is not original
    assert result.evidence is not None
    assert result.evidence.score == 100
    assert result.evidence.gate is EvidenceGate.DEEP


def test_pipeline_runs_evidence_then_confidence() -> None:
    original = build_context()
    result = Pipeline([complete_evidence_engine(), ConfidenceEngine()]).run(original)

    assert original.evidence is None
    assert original.confidence is None
    assert result.evidence is not None
    assert result.confidence is not None
    assert result.confidence.evidence == 1.0
    assert result.confidence.band is ConfidenceBand.MEDIUM


def test_preferred_pipeline_runs_consensus_before_confidence_rules_and_adjustment() -> None:
    original = replace(
        build_context(),
        lineups={"confirmed": False},
        model_outputs=(
            model("poisson", 0.55, 0.25, 0.20),
            model("bayesian", 0.50, 0.30, 0.20),
        ),
    )
    result = Pipeline(
        [
            complete_evidence_engine(),
            ConsensusEngine(),
            ConfidenceEngine(),
            RuleEngine(),
            AdjustmentEngine(),
        ]
    ).run(original)

    assert original.evidence is None
    assert original.consensus is None
    assert original.confidence is None
    assert original.rule_outputs == ()
    assert original.adjustment is None
    assert result.consensus is not None
    assert result.confidence is not None
    assert result.confidence.consensus == result.consensus.agreement
    assert result.adjustment is not None
    assert "restrict_high_confidence_action" in result.adjustment.applied_effects
    assert result.adjustment.adjusted_confidence <= result.confidence.overall


def test_full_pipeline_can_produce_governed_candidate() -> None:
    original = replace(
        build_context(),
        market={"home_odds": 2.0, "draw_odds": 4.2, "away_odds": 6.0},
        model_outputs=(
            model("poisson", 0.58, 0.24, 0.18),
            model("bayesian", 0.56, 0.25, 0.19),
        ),
    )
    result = Pipeline(
        [
            complete_evidence_engine(),
            ConsensusEngine(),
            ConfidenceEngine(),
            RuleEngine(),
            AdjustmentEngine(),
            DecisionEngine(),
        ]
    ).run(original)

    assert original.decision is None
    assert result.consensus is not None
    assert result.adjustment is not None
    assert result.decision is not None
    assert result.decision.action is DecisionAction.CANDIDATE
    assert result.decision.selected_market == "home"
    assert result.decision.expected_value is not None
    assert result.decision.expected_value > 0


def test_empty_pipeline_returns_original_context() -> None:
    original = build_context()
    assert Pipeline([]).run(original) is original
