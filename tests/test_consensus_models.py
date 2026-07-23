from datetime import datetime, timezone

import pytest

from src.domain.models import (
    AnalysisSession,
    ConsensusOutput,
    MatchContext,
    MatchInfo,
    TeamInfo,
)


def build_context(consensus: ConsensusOutput | None = None) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="consensus-model-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="consensus-model-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        consensus=consensus,
    )


def valid_output() -> ConsensusOutput:
    return ConsensusOutput(
        model_count=2,
        model_ids=("a", "b"),
        home_probability=0.50,
        draw_probability=0.30,
        away_probability=0.20,
        agreement=0.80,
        mean_pairwise_distance=0.20,
        max_spread=0.25,
        leading_outcome="home",
        margin=0.20,
    )


def test_consensus_output_serializes_through_match_context() -> None:
    payload = build_context(valid_output()).to_dict()
    assert payload["consensus"]["model_ids"] == ["a", "b"]
    assert payload["consensus"]["leading_outcome"] == "home"
    assert payload["consensus"]["method"] == "equal_weight_mean"


def test_model_count_must_match_model_ids() -> None:
    with pytest.raises(ValueError, match="model_count must match"):
        ConsensusOutput(
            model_count=2,
            model_ids=("a",),
            home_probability=0.50,
            draw_probability=0.30,
            away_probability=0.20,
            agreement=0.80,
            mean_pairwise_distance=0.20,
            max_spread=0.25,
            leading_outcome="home",
            margin=0.20,
        )


def test_duplicate_model_ids_are_rejected_by_domain_model() -> None:
    with pytest.raises(ValueError, match="unique"):
        ConsensusOutput(
            model_count=2,
            model_ids=("a", "a"),
            home_probability=0.50,
            draw_probability=0.30,
            away_probability=0.20,
            agreement=0.80,
            mean_pairwise_distance=0.20,
            max_spread=0.25,
            leading_outcome="home",
            margin=0.20,
        )


def test_consensus_probabilities_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1"):
        ConsensusOutput(
            model_count=1,
            model_ids=("a",),
            home_probability=0.50,
            draw_probability=0.30,
            away_probability=0.30,
            agreement=0.50,
            mean_pairwise_distance=0.50,
            max_spread=0.0,
            leading_outcome="home",
            margin=0.20,
        )


def test_leading_outcome_is_validated() -> None:
    with pytest.raises(ValueError, match="leading_outcome"):
        ConsensusOutput(
            model_count=1,
            model_ids=("a",),
            home_probability=0.50,
            draw_probability=0.30,
            away_probability=0.20,
            agreement=0.50,
            mean_pairwise_distance=0.50,
            max_spread=0.0,
            leading_outcome="unknown",
            margin=0.20,
        )
