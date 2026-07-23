from datetime import datetime, timezone

from src.confidence.engine import ConfidenceEngine
from src.core.pipeline import Pipeline
from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    EvidenceGate,
    MatchContext,
    MatchInfo,
    TeamInfo,
)
from src.evidence.context_engine import EvidenceEngine


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


def test_empty_pipeline_returns_original_context() -> None:
    original = build_context()
    assert Pipeline([]).run(original) is original
