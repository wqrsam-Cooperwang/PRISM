from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.consensus.engine import ConsensusEngine
from src.domain.models import AnalysisSession, MatchContext, MatchInfo, ModelOutput, TeamInfo


def build_context(models: tuple[ModelOutput, ...] = ()) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="consensus-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="consensus-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        model_outputs=models,
    )


def model(model_id: str, home: float, draw: float, away: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
    )


def test_requires_at_least_one_model() -> None:
    with pytest.raises(ValueError, match="at least one model"):
        ConsensusEngine().run(build_context())


def test_duplicate_model_ids_are_rejected() -> None:
    models = (
        model("same", 0.50, 0.30, 0.20),
        model("same", 0.40, 0.30, 0.30),
    )
    with pytest.raises(ValueError, match="unique model ids"):
        ConsensusEngine().run(build_context(models))


def test_single_model_preserves_distribution_with_neutral_agreement() -> None:
    result = ConsensusEngine().run(build_context((model("only", 0.55, 0.25, 0.20),)))
    assert result.consensus is not None
    assert result.consensus.model_count == 1
    assert result.consensus.home_probability == 0.55
    assert result.consensus.draw_probability == 0.25
    assert result.consensus.away_probability == 0.20
    assert result.consensus.agreement == 0.50
    assert result.consensus.mean_pairwise_distance == 0.50
    assert result.consensus.max_spread == 0.0
    assert result.consensus.leading_outcome == "home"
    assert result.consensus.margin == 0.30


def test_identical_models_produce_perfect_agreement() -> None:
    models = (
        model("a", 0.60, 0.25, 0.15),
        model("b", 0.60, 0.25, 0.15),
        model("c", 0.60, 0.25, 0.15),
    )
    result = ConsensusEngine().run(build_context(models))
    assert result.consensus is not None
    assert result.consensus.agreement == 1.0
    assert result.consensus.mean_pairwise_distance == 0.0
    assert result.consensus.max_spread == 0.0


def test_consensus_uses_equal_weight_arithmetic_mean() -> None:
    models = (
        model("a", 0.60, 0.25, 0.15),
        model("b", 0.30, 0.30, 0.40),
    )
    result = ConsensusEngine().run(build_context(models))
    assert result.consensus is not None
    assert result.consensus.home_probability == 0.45
    assert result.consensus.draw_probability == 0.275
    assert result.consensus.away_probability == 0.275
    assert result.consensus.leading_outcome == "home"
    assert result.consensus.margin == 0.175
    assert result.consensus.max_spread == 0.30


def test_strong_model_disagreement_reduces_agreement() -> None:
    agreeing = ConsensusEngine().run(
        build_context(
            (
                model("a", 0.70, 0.20, 0.10),
                model("b", 0.70, 0.20, 0.10),
            )
        )
    )
    disagreeing = ConsensusEngine().run(
        build_context(
            (
                model("a", 0.80, 0.10, 0.10),
                model("b", 0.10, 0.10, 0.80),
            )
        )
    )
    assert agreeing.consensus is not None
    assert disagreeing.consensus is not None
    assert agreeing.consensus.agreement > disagreeing.consensus.agreement
    assert disagreeing.consensus.agreement == 0.30


def test_equal_top_probabilities_are_reported_as_tie() -> None:
    result = ConsensusEngine().run(build_context((model("a", 0.40, 0.40, 0.20),)))
    assert result.consensus is not None
    assert result.consensus.leading_outcome == "tie"
    assert result.consensus.margin == 0.0


def test_engine_returns_new_context_without_mutating_original() -> None:
    original = build_context((model("a", 0.50, 0.30, 0.20),))
    result = ConsensusEngine().run(original)
    assert original.consensus is None
    assert result.consensus is not None
    assert result is not original


def test_existing_consensus_is_replaced_deterministically() -> None:
    original = build_context((model("a", 0.50, 0.30, 0.20),))
    first = ConsensusEngine().run(original)
    changed = replace(
        first,
        model_outputs=(model("b", 0.20, 0.30, 0.50),),
    )
    second = ConsensusEngine().run(changed)
    assert second.consensus is not None
    assert second.consensus.leading_outcome == "away"
    assert second.consensus.model_ids == ("b",)
