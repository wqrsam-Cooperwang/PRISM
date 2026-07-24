from datetime import datetime, timezone

from src.report.models import (
    AdjustmentReport,
    ConfidenceReport,
    ConsensusReport,
    DecisionReport,
    EngineTraceReport,
    EvidenceReport,
    MatchReport,
    PredictionReport,
    ProvenanceReport,
    ScorelineCandidateReport,
    ScorelineReport,
)
from src.report.renderer import render_prediction_report_markdown


def report(*, scoreline_available: bool = True) -> PredictionReport:
    scoreline = ScorelineReport(
        available=scoreline_available,
        method="independent_poisson_equal_weight_xg",
        expected_home_goals=1.50 if scoreline_available else None,
        expected_away_goals=0.90 if scoreline_available else None,
        top_scorelines=(
            ScorelineCandidateReport(1, 0, 0.136),
            ScorelineCandidateReport(1, 1, 0.122),
            ScorelineCandidateReport(2, 0, 0.102),
        )
        if scoreline_available
        else (),
        source_model_ids=("poisson", "bayesian") if scoreline_available else (),
        grid_probability_mass=0.999,
        tail_mass=0.001,
    )
    return PredictionReport(
        match=MatchReport(
            match_id="match-1",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
            home_team="Home FC",
            away_team="Away FC",
        ),
        consensus=ConsensusReport(0.58, 0.24, 0.18, "home", 0.82, 2),
        confidence=ConfidenceReport(0.74, "high", ("weather uncertainty",)),
        evidence=EvidenceReport(
            score=86,
            gate="deep",
            warnings=("late lineup confirmation",),
            missing_categories=("weather",),
        ),
        decision=DecisionReport(
            action="candidate",
            selected_market="home",
            expected_value=0.034,
            risk_level="medium",
            rationale=("positive governed EV",),
        ),
        adjustment=AdjustmentReport(
            base_confidence=0.78,
            adjusted_confidence=0.74,
            confidence_cap=0.80,
            decision_blocked=False,
            applied_effects=("weather_penalty",),
            observed_effects=("home_advantage",),
            rule_outputs=({"rule_id": "R-1", "status": "active"},),
        ),
        scoreline=scoreline,
        provenance=ProvenanceReport(
            prism_version="3.2.0-alpha1",
            schema_version="1.0.0",
            runtime_version="1.0.0",
            session_id="session-1",
            git_commit="abc123",
            engine_trace=(
                EngineTraceReport("evidence", "1.0.0", "completed"),
                EngineTraceReport("decision", "1.0.0", "completed"),
            ),
        ),
    )


def test_renderer_is_deterministic_and_preserves_canonical_values() -> None:
    first = render_prediction_report_markdown(report())
    second = render_prediction_report_markdown(report())

    assert first == second
    assert "Home: 58.0%" in first
    assert "Overall confidence: 74.0%" in first
    assert "Expected value: +3.4%" in first
    assert "#1: 1-0 (13.6%)" in first
    assert "Expected goals: 1.50 - 0.90" in first
    assert "Action: candidate" in first
    assert "weather uncertainty" in first
    assert '"rule_id": "R-1"' in first
    assert "evidence 1.0.0 [completed]" in first


def test_unavailable_scoreline_is_not_fabricated() -> None:
    output = render_prediction_report_markdown(report(scoreline_available=False))

    scoreline_section = output.split("## Top 3 Scorelines", maxsplit=1)[1].split(
        "## Rules and Adjustment", maxsplit=1
    )[0]
    assert "Unavailable" in scoreline_section
    assert "#1:" not in scoreline_section
    assert "Expected goals:" not in scoreline_section
