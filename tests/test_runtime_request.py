from datetime import datetime, timezone

from src.domain.models import ModelOutput
from src.runtime import MatchRequest, build_match_context


def request() -> MatchRequest:
    return MatchRequest(
        match_id="match-1",
        competition="Test League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home",
        home_team_name="Home FC",
        away_team_id="away",
        away_team_name="Away FC",
        model_outputs=(ModelOutput("poisson", "1.0.0", 0.58, 0.24, 0.18),),
        venue="Test Stadium",
        season="2026",
        stage="Round 1",
        market={"home_odds": 2.0, "draw_odds": 4.2, "away_odds": 6.0},
        tactical={"home_shape": "4-3-3", "away_shape": "4-2-3-1"},
    )


def test_build_match_context_creates_fresh_canonical_input() -> None:
    created_at = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    context = build_match_context(
        request(),
        prism_version="3.2.0-alpha1",
        session_id="session-1",
        created_at=created_at,
        git_commit="abc123",
    )

    assert context.session.session_id == "session-1"
    assert context.session.created_at == created_at
    assert context.session.prism_version == "3.2.0-alpha1"
    assert context.session.git_commit == "abc123"
    assert context.match.match_id == "match-1"
    assert context.match.venue == "Test Stadium"
    assert context.home_team.name == "Home FC"
    assert context.away_team.name == "Away FC"
    assert context.market["home_odds"] == 2.0
    assert context.tactical["home_shape"] == "4-3-3"
    assert len(context.model_outputs) == 1
    assert context.evidence is None
    assert context.decision is None


def test_build_match_context_generates_session_metadata_by_default() -> None:
    context = build_match_context(request(), prism_version="3.2.0-alpha1")

    assert context.session.session_id
    assert context.session.created_at.tzinfo is not None


def test_request_data_is_frozen_when_context_is_built() -> None:
    market = {"home_odds": 2.0}
    source = request()
    custom = MatchRequest(
        match_id=source.match_id,
        competition=source.competition,
        kickoff=source.kickoff,
        home_team_id=source.home_team_id,
        home_team_name=source.home_team_name,
        away_team_id=source.away_team_id,
        away_team_name=source.away_team_name,
        model_outputs=source.model_outputs,
        market=market,
    )
    context = build_match_context(custom, prism_version="3.2.0-alpha1")
    market["home_odds"] = 9.0

    assert context.market["home_odds"] == 2.0
