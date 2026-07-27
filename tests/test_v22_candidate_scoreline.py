from datetime import datetime, timezone

from src.consensus import DirectionCalibrationOutput
from src.domain.models import (
    AnalysisSession,
    DecisionOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.scoreline import V22CandidateScorelineEngine


def _context(home_xg: float, away_xg: float) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="v22-candidate",
            created_at=datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc),
            prism_version="2.2.0-candidate1",
        ),
        match=MatchInfo(
            match_id="v22-candidate-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 27, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("home", "Home FC"),
        away_team=TeamInfo("away", "Away FC"),
        model_outputs=(ModelOutput("xg", "1.0.0", 0.55, 0.25, 0.20, home_xg, away_xg),),
        decision=DecisionOutput(),
    )


def _direction(home: float, draw: float, away: float) -> DirectionCalibrationOutput:
    leading = max(home, draw, away)
    return DirectionCalibrationOutput(
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
        reliability=0.8,
        raw_leading_probability=leading,
        calibrated_leading_probability=leading,
    )


def test_candidate_engine_uses_regime_conditioned_weights() -> None:
    output = V22CandidateScorelineEngine().run_with_direction(
        _context(1.85, 1.10),
        _direction(0.52, 0.24, 0.24),
    )

    assert output.available is True
    assert output.method == "regime_scenario_mixture_poisson_v2_2_candidate"
    assert len(output.recommended_scorelines) == 2
    assert any(item == "regime=home_open" for item in output.rationale)
    assert any(item.startswith("scenario_weights=") for item in output.rationale)
    assert any("production V2.1 remains unchanged" in item for item in output.rationale)


def test_candidate_engine_returns_unavailable_without_xg() -> None:
    context = _context(1.0, 1.0)
    context = MatchContext(
        session=context.session,
        match=context.match,
        home_team=context.home_team,
        away_team=context.away_team,
        model_outputs=(ModelOutput("plain", "1.0.0", 0.5, 0.3, 0.2),),
        decision=DecisionOutput(),
    )
    output = V22CandidateScorelineEngine().run_with_direction(
        context,
        _direction(0.4, 0.3, 0.3),
    )

    assert output.available is False
