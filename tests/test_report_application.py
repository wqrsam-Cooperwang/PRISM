from datetime import datetime, timezone

from src.domain.models import ModelOutput
from src.report import analyze_match_report_markdown
from src.runtime import MatchRequest


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


def test_analyze_match_report_markdown_runs_full_governed_chain() -> None:
    markdown = analyze_match_report_markdown(
        request(),
        complete_evidence(),
        prism_version="3.2.0-alpha1",
        session_id="report-session",
        created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
        git_commit="abc123",
    )

    assert "# PRISM Prediction Report" in markdown
    assert "- Fixture: Home FC vs Away FC" in markdown
    assert "## 1X2 Consensus" in markdown
    assert "## Decision" in markdown
    assert "## Top 3 Scorelines" in markdown
    assert "- #1:" in markdown
    assert "- #2:" in markdown
    assert "- #3:" in markdown
    assert "- Session ID: report-session" in markdown
    assert "- Git commit: abc123" in markdown
