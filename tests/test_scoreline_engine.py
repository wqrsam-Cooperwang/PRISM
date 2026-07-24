from datetime import datetime, timezone

import pytest

from src.domain.models import (
    AnalysisSession,
    DecisionOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.scoreline.engine import ScorelineEngine


def context_with_models(models: tuple[ModelOutput, ...], *, with_decision: bool = True) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="scoreline-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="scoreline-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("home", "Home FC"),
        away_team=TeamInfo("away", "Away FC"),
        model_outputs=models,
        decision=DecisionOutput() if with_decision else None,
    )


def test_scoreline_requires_decision_output() -> None:
    context = context_with_models(
        (ModelOutput("xg", "1.0.0", 0.5, 0.3, 0.2, 1.4, 0.9),),
        with_decision=False,
    )

    with pytest.raises(ValueError, match="requires Decision"):
        ScorelineEngine().run(context)


def test_missing_expected_goals_returns_unavailable_output() -> None:
    output = ScorelineEngine().run(
        context_with_models((ModelOutput("plain", "1.0.0", 0.5, 0.3, 0.2),))
    )

    assert output.available is False
    assert output.source_model_ids == ()
    assert output.top_scorelines == ()
    assert output.grid_probability_mass == 0.0
    assert output.tail_mass == 1.0


def test_scoreline_uses_equal_weight_expected_goals_and_returns_top_three() -> None:
    output = ScorelineEngine().run(
        context_with_models(
            (
                ModelOutput("model-a", "1.0.0", 0.55, 0.25, 0.20, 1.6, 0.8),
                ModelOutput("model-b", "1.0.0", 0.50, 0.28, 0.22, 1.4, 1.0),
            )
        )
    )

    assert output.available is True
    assert output.source_model_ids == ("model-a", "model-b")
    assert output.expected_home_goals == pytest.approx(1.5)
    assert output.expected_away_goals == pytest.approx(0.9)
    assert len(output.top_scorelines) == 3
    assert output.top_scorelines[0].probability >= output.top_scorelines[1].probability
    assert output.top_scorelines[1].probability >= output.top_scorelines[2].probability
    assert output.grid_probability_mass + output.tail_mass == pytest.approx(1.0)
    assert 0.0 <= output.tail_mass <= 1.0


def test_models_without_complete_expected_goals_are_not_used() -> None:
    output = ScorelineEngine().run(
        context_with_models(
            (
                ModelOutput("eligible", "1.0.0", 0.55, 0.25, 0.20, 1.3, 0.7),
                ModelOutput("missing-away", "1.0.0", 0.50, 0.28, 0.22, 1.8, None),
            )
        )
    )

    assert output.source_model_ids == ("eligible",)
    assert output.expected_home_goals == pytest.approx(1.3)
    assert output.expected_away_goals == pytest.approx(0.7)


def test_invalid_expected_goals_are_rejected() -> None:
    context = context_with_models(
        (ModelOutput("invalid", "1.0.0", 0.5, 0.3, 0.2, -0.1, 0.9),)
    )

    with pytest.raises(ValueError, match="finite and non-negative"):
        ScorelineEngine().run(context)
