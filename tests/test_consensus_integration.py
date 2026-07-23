from dataclasses import replace
from datetime import datetime, timezone

from src.confidence.engine import ConfidenceEngine
from src.consensus.engine import ConsensusEngine
from src.domain.models import (
    AnalysisSession,
    EvidenceGate,
    EvidenceOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)


def model(model_id: str, home: float, draw: float, away: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
    )


def build_context() -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="consensus-integration",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="consensus-integration-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        evidence=EvidenceOutput(score=90, raw_score=90.0, gate=EvidenceGate.DEEP),
        model_outputs=(
            model("a", 0.80, 0.10, 0.10),
            model("b", 0.10, 0.10, 0.80),
        ),
    )


def test_confidence_engine_uses_consensus_output_when_present() -> None:
    base = build_context()
    with_consensus = ConsensusEngine().run(base)
    result = ConfidenceEngine().run(with_consensus)
    assert with_consensus.consensus is not None
    assert result.confidence is not None
    assert result.confidence.consensus == with_consensus.consensus.agreement


def test_consensus_agreement_overrides_backward_compatibility_fallback() -> None:
    base = build_context()
    computed = ConsensusEngine().run(base)
    assert computed.consensus is not None
    altered = replace(
        computed,
        consensus=replace(computed.consensus, agreement=0.25),
    )
    result = ConfidenceEngine().run(altered)
    assert result.confidence is not None
    assert result.confidence.consensus == 0.25
