from datetime import datetime, timezone

from src.domain.models import ModelOutput
from src.report import build_prediction_report, build_prediction_report_dict
from src.runtime import MatchRequest, analyze_match


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
        match_id="report-match",
        competition="Test League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home",
        home_team_name="Home FC",
        away_team_id="away",
        away_team_name="Away FC",
        model_outputs=(
            ModelOutput("model-a", "1.0.0", 0.58, 0.24, 0.18, 1.6, 0.8),
            ModelOutput("model-b", "1.0.0", 0.54, 0.27, 0.19, 1.4, 1.0),
        ),
        market={"home_odds": 2.0, "draw_odds": 4.2, "away_odds": 6.0},
    )


def runtime_result():
    return analyze_match(
        request(),
        complete_evidence(),
        prism_version="3.2.0-alpha1",
        session_id="report-session",
        created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
        git_commit="abc123",
        data_version="data-v1",
        rule_version="rules-v1",
        model_version="models-v1",
        prompt_version="prompts-v1",
        ai_models=("gpt", "gemini"),
    )


def test_builder_projects_governed_runtime_values_without_recalculation() -> None:
    result = runtime_result()
    report = build_prediction_report(result)

    assert report.match.match_id == result.context.match.match_id
    assert report.consensus is not None
    assert result.context.consensus is not None
    assert report.consensus.home_probability == result.context.consensus.home_probability
    assert report.confidence is not None
    assert result.context.confidence is not None
    assert report.confidence.overall == result.context.confidence.overall
    assert report.decision is not None
    assert result.context.decision is not None
    assert report.decision.action == result.context.decision.action.value
    assert report.scoreline is not None
    assert result.scoreline is not None
    assert report.scoreline.top_scorelines[0].probability == (
        result.scoreline.top_scorelines[0].probability
    )


def test_builder_preserves_rules_and_runtime_provenance() -> None:
    result = runtime_result()
    report = build_prediction_report(result)

    assert report.adjustment is not None
    assert report.adjustment.rule_outputs == result.context.rule_outputs
    assert report.provenance.prism_version == "3.2.0-alpha1"
    assert report.provenance.runtime_version == result.runtime_version
    assert report.provenance.git_commit == "abc123"
    assert report.provenance.data_version == "data-v1"
    assert report.provenance.rule_version == "rules-v1"
    assert report.provenance.model_version == "models-v1"
    assert report.provenance.prompt_version == "prompts-v1"
    assert report.provenance.ai_models == ("gpt", "gemini")
    assert tuple(item.name for item in report.provenance.engine_trace) == (
        "evidence",
        "consensus",
        "confidence",
        "rules",
        "adjustment",
        "decision",
    )


def test_builder_dict_is_json_compatible_projection() -> None:
    output = build_prediction_report_dict(runtime_result())

    assert output["match"]["match_id"] == "report-match"
    assert output["match"]["kickoff"] == "2026-07-25T18:00:00+00:00"
    assert output["consensus"] is not None
    assert output["scoreline"] is not None
    assert len(output["scoreline"]["top_scorelines"]) == 3
    assert output["provenance"]["session_id"] == "report-session"
