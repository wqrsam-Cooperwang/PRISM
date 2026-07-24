from datetime import datetime, timezone

from src.domain.models import ModelOutput
from src.runtime import MatchRequest, analyze_match, analyze_match_dict


def complete_evidence() -> dict[str, float]:
    return {
        "lineup": 1.0,
        "injuries": 1.0,
        "odds": 1.0,
        "weather": 1.0,
        "tactical_data": 1.0,
        "historical_data": 1.0,
        "market_data": 1.0,
        "motivation": 1.0,
    }


def request() -> MatchRequest:
    return MatchRequest(
        match_id="match-1",
        competition="Test League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home",
        home_team_name="Home FC",
        away_team_id="away",
        away_team_name="Away FC",
        model_outputs=(
            ModelOutput("poisson", "1.0.0", 0.58, 0.24, 0.18, 1.6, 0.8),
            ModelOutput("elo", "1.0.0", 0.54, 0.27, 0.19, 1.4, 1.0),
        ),
    )


def test_analyze_match_executes_canonical_pipeline() -> None:
    result = analyze_match(
        request(),
        complete_evidence(),
        prism_version="3.2.0-alpha1",
        session_id="session-1",
        created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
    )

    assert tuple(step.name for step in result.engine_trace) == (
        "evidence",
        "consensus",
        "confidence",
        "rules",
        "adjustment",
        "decision",
    )
    assert result.context.session.session_id == "session-1"
    assert result.context.evidence is not None
    assert result.context.consensus is not None
    assert result.context.confidence is not None
    assert result.context.adjustment is not None
    assert result.context.decision is not None
    assert result.scoreline is not None
    assert result.scoreline.available is True
    assert len(result.scoreline.top_scorelines) == 3


def test_analyze_match_dict_returns_json_compatible_final_context() -> None:
    output = analyze_match_dict(
        request(),
        complete_evidence(),
        prism_version="3.2.0-alpha1",
        session_id="session-2",
        created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
    )

    assert output["session"]["session_id"] == "session-2"
    assert output["match"]["match_id"] == "match-1"
    assert output["evidence"] is not None
    assert output["consensus"] is not None
    assert output["decision"] is not None
    assert output["scoreline"]["available"] is True
    assert len(output["scoreline"]["top_scorelines"]) == 3
