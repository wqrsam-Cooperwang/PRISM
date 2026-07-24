from datetime import datetime, timezone

import pytest

from src.report import (
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


def build_report() -> PredictionReport:
    return PredictionReport(
        match=MatchReport(
            match_id="match-1",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
            home_team="Home FC",
            away_team="Away FC",
        ),
        consensus=ConsensusReport(
            home_probability=0.58,
            draw_probability=0.24,
            away_probability=0.18,
            leading_outcome="home",
            agreement=0.84,
            model_count=2,
        ),
        confidence=ConfidenceReport(overall=0.76, band="high", penalties=()),
        evidence=EvidenceReport(score=92, gate="deep"),
        decision=DecisionReport(
            action="candidate",
            selected_market="home",
            expected_value=0.06,
            risk_level="medium",
        ),
        adjustment=AdjustmentReport(
            base_confidence=0.76,
            adjusted_confidence=0.74,
            confidence_cap=None,
            decision_blocked=False,
            rule_outputs=({"rule_id": "rule-1", "effect": "flag_market_movement"},),
        ),
        scoreline=ScorelineReport(
            available=True,
            method="independent_poisson_equal_weight_xg",
            expected_home_goals=1.5,
            expected_away_goals=0.9,
            top_scorelines=(
                ScorelineCandidateReport(1, 0, 0.13),
                ScorelineCandidateReport(1, 1, 0.12),
                ScorelineCandidateReport(2, 0, 0.10),
            ),
            source_model_ids=("poisson", "xg"),
            grid_probability_mass=0.999,
            tail_mass=0.001,
        ),
        provenance=ProvenanceReport(
            prism_version="3.2.0-alpha1",
            schema_version="1.0.0",
            runtime_version="1.0.0",
            session_id="session-1",
            git_commit="abc123",
            engine_trace=(EngineTraceReport("evidence", "1.0.0", "completed"),),
        ),
    )


def test_prediction_report_serializes_to_json_compatible_dictionary() -> None:
    output = build_report().to_dict()

    assert output["match"]["kickoff"] == "2026-07-25T18:00:00+00:00"
    assert output["consensus"]["home_probability"] == 0.58
    assert output["decision"]["action"] == "candidate"
    assert output["scoreline"]["top_scorelines"][0] == {
        "home_goals": 1,
        "away_goals": 0,
        "probability": 0.13,
    }
    assert output["provenance"]["engine_trace"][0]["name"] == "evidence"


def test_adjustment_report_freezes_rule_outputs() -> None:
    source = {"rule_id": "rule-1"}
    report = AdjustmentReport(
        base_confidence=0.7,
        adjusted_confidence=0.7,
        confidence_cap=None,
        decision_blocked=False,
        rule_outputs=(source,),
    )
    source["rule_id"] = "changed"

    assert report.rule_outputs[0]["rule_id"] == "rule-1"
    with pytest.raises(TypeError):
        report.rule_outputs[0]["rule_id"] = "mutated"  # type: ignore[index]


def test_prediction_report_is_frozen() -> None:
    report = build_report()

    with pytest.raises(AttributeError):
        report.consensus = None  # type: ignore[misc]


def test_optional_sections_can_be_absent_without_inference() -> None:
    report = PredictionReport(
        match=MatchReport(
            match_id="match-2",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
            home_team="Home FC",
            away_team="Away FC",
        ),
        consensus=None,
        confidence=None,
        evidence=None,
        decision=None,
        adjustment=None,
        scoreline=None,
        provenance=ProvenanceReport(
            prism_version="3.2.0-alpha1",
            schema_version="1.0.0",
            runtime_version="1.0.0",
            session_id="session-2",
        ),
    )

    output = report.to_dict()
    assert output["consensus"] is None
    assert output["scoreline"] is None
