from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import json

import pytest

from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    ConfidenceOutput,
    DecisionAction,
    DecisionOutput,
    EvidenceGate,
    EvidenceOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)


def build_context(**changes):
    session = AnalysisSession(
        session_id="session-001",
        created_at=datetime(2026, 7, 22, 10, 0, tzinfo=timezone.utc),
        prism_version="3.1.0-alpha1",
        git_commit="abc123",
        ai_models=("chatgpt", "gemini"),
    )
    context = MatchContext(
        session=session,
        match=MatchInfo(
            match_id="match-001",
            competition="Test League",
            kickoff=datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        market={"home_odds": 2.1},
    )
    return replace(context, **changes)


def test_minimal_context_can_be_created():
    context = build_context()
    assert context.match.match_id == "match-001"
    assert context.schema_version == "1.0.0"


def test_context_is_frozen():
    context = build_context()
    with pytest.raises(FrozenInstanceError):
        context.schema_version = "2.0.0"


def test_mapping_fields_are_read_only():
    context = build_context()
    with pytest.raises(TypeError):
        context.market["home_odds"] = 1.9


def test_replace_returns_new_context_without_mutation():
    original = build_context()
    updated = replace(original, weather={"temperature_c": 14})
    assert original.weather == {}
    assert updated.weather["temperature_c"] == 14
    assert original is not updated


def test_context_serializes_to_json():
    payload = build_context().to_dict()
    encoded = json.dumps(payload)
    assert '"session-001"' in encoded
    assert payload["session"]["created_at"].endswith("+00:00")
    assert payload["market"]["home_odds"] == 2.1


def test_naive_session_datetime_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        AnalysisSession(
            session_id="s1",
            created_at=datetime(2026, 7, 22, 10, 0),
            prism_version="3.1.0",
        )


def test_naive_kickoff_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        MatchInfo(
            match_id="m1",
            competition="League",
            kickoff=datetime(2026, 7, 23, 18, 0),
        )


def test_empty_identifier_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        TeamInfo(team_id=" ", name="Team")


def test_same_home_and_away_team_is_rejected():
    session = AnalysisSession(
        session_id="s1",
        created_at=datetime.now(timezone.utc),
        prism_version="3.1.0",
    )
    team = TeamInfo(team_id="same", name="Same FC")
    with pytest.raises(ValueError, match="must be different"):
        MatchContext(
            session=session,
            match=MatchInfo(
                match_id="m1",
                competition="League",
                kickoff=datetime.now(timezone.utc),
            ),
            home_team=team,
            away_team=team,
        )


def test_schema_version_mismatch_is_rejected():
    with pytest.raises(ValueError, match="schema versions"):
        build_context(schema_version="2.0.0")


def test_valid_model_probabilities_are_accepted():
    output = ModelOutput(
        model_id="poisson",
        model_version="1.0.0",
        home_probability=0.5,
        draw_probability=0.3,
        away_probability=0.2,
    )
    assert output.home_probability == 0.5


def test_model_probabilities_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to 1"):
        ModelOutput(
            model_id="poisson",
            model_version="1.0.0",
            home_probability=0.5,
            draw_probability=0.3,
            away_probability=0.3,
        )


def test_model_probability_must_be_finite():
    with pytest.raises(ValueError, match="finite"):
        ModelOutput(
            model_id="poisson",
            model_version="1.0.0",
            home_probability=float("nan"),
            draw_probability=0.5,
            away_probability=0.5,
        )


def test_evidence_output_accepts_enum_string():
    output = EvidenceOutput(score=85, raw_score=84.6, gate="deep")
    assert output.gate is EvidenceGate.DEEP


def test_evidence_score_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 100"):
        EvidenceOutput(score=101, raw_score=100, gate=EvidenceGate.DEEP)


def test_confidence_values_are_bounded():
    with pytest.raises(ValueError, match="between 0 and 1"):
        ConfidenceOutput(
            evidence=1.1,
            model=0.8,
            context=0.8,
            consensus=0.8,
            overall=0.8,
            band=ConfidenceBand.HIGH,
        )


def test_rejected_evidence_cannot_have_candidate_decision():
    evidence = EvidenceOutput(score=20, raw_score=20, gate=EvidenceGate.REJECTED)
    decision = DecisionOutput(action=DecisionAction.CANDIDATE)
    with pytest.raises(ValueError, match="Rejected evidence"):
        build_context(evidence=evidence, decision=decision)


def test_rejected_evidence_allows_no_decision():
    evidence = EvidenceOutput(score=20, raw_score=20, gate=EvidenceGate.REJECTED)
    decision = DecisionOutput(action=DecisionAction.NO_DECISION)
    context = build_context(evidence=evidence, decision=decision)
    assert context.decision.action is DecisionAction.NO_DECISION


def test_engine_output_sections_attach_independently():
    evidence = EvidenceOutput(score=75, raw_score=75, gate=EvidenceGate.STANDARD)
    model = ModelOutput(
        model_id="poisson",
        model_version="1.0.0",
        home_probability=0.5,
        draw_probability=0.3,
        away_probability=0.2,
    )
    confidence = ConfidenceOutput(
        evidence=0.75,
        model=0.82,
        context=0.7,
        consensus=0.8,
        overall=0.77,
        band=ConfidenceBand.HIGH,
    )
    context = build_context(
        evidence=evidence,
        model_outputs=(model,),
        confidence=confidence,
    )
    payload = context.to_dict()
    assert payload["evidence"]["gate"] == "standard"
    assert payload["model_outputs"][0]["model_id"] == "poisson"
    assert payload["confidence"]["band"] == "high"
