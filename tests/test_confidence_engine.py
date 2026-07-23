from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.confidence.engine import ConfidenceEngine, _band_from_score
from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    EvidenceGate,
    EvidenceOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)


def build_context(
    gate: EvidenceGate = EvidenceGate.DEEP,
    score: int = 95,
    models: tuple[ModelOutput, ...] = (),
    complete_context: bool = False,
) -> MatchContext:
    session = AnalysisSession(
        session_id="confidence-session",
        created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
        prism_version="3.2.0-alpha1",
    )
    context = MatchContext(
        session=session,
        match=MatchInfo(
            match_id="confidence-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        evidence=EvidenceOutput(score=score, raw_score=float(score), gate=gate),
        model_outputs=models,
    )
    if not complete_context:
        return context
    return replace(
        context,
        lineups={"confirmed": True},
        injuries={"home": []},
        market={"home_odds": 2.0},
        weather={"temperature_c": 15},
        schedule={"home_rest_days": 6},
        tactical={"home_shape": "4-3-3"},
    )


def model(model_id: str, home: float, draw: float, away: float) -> ModelOutput:
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
    )


def test_requires_evidence() -> None:
    context = build_context()
    context = replace(context, evidence=None)
    with pytest.raises(ValueError, match="requires evidence"):
        ConfidenceEngine().run(context)


def test_high_quality_complete_context_produces_very_high_confidence() -> None:
    models = (
        model("poisson", 0.55, 0.25, 0.20),
        model("bayesian", 0.55, 0.25, 0.20),
    )
    result = ConfidenceEngine().run(build_context(models=models, complete_context=True))
    assert result.confidence is not None
    assert result.confidence.band is ConfidenceBand.VERY_HIGH
    assert result.confidence.overall > 0.85
    assert result.confidence.consensus == 1.0


def test_limited_evidence_caps_overall_confidence() -> None:
    models = (
        model("m1", 0.60, 0.20, 0.20),
        model("m2", 0.60, 0.20, 0.20),
        model("m3", 0.60, 0.20, 0.20),
    )
    result = ConfidenceEngine().run(
        build_context(
            gate=EvidenceGate.LIMITED,
            score=90,
            models=models,
            complete_context=True,
        )
    )
    assert result.confidence is not None
    assert result.confidence.overall == 0.64
    assert result.confidence.band is ConfidenceBand.MEDIUM
    assert result.confidence.penalties == ("evidence_gate_cap:limited:0.64",)


def test_rejected_evidence_cannot_reach_medium_confidence() -> None:
    result = ConfidenceEngine().run(
        build_context(
            gate=EvidenceGate.REJECTED,
            score=90,
            models=(
                model("m1", 0.50, 0.30, 0.20),
                model("m2", 0.50, 0.30, 0.20),
            ),
            complete_context=True,
        )
    )
    assert result.confidence is not None
    assert result.confidence.overall == 0.34
    assert result.confidence.band is ConfidenceBand.VERY_LOW


def test_model_confidence_handles_zero_one_many_and_cap() -> None:
    no_models = ConfidenceEngine().run(build_context())
    one_model = ConfidenceEngine().run(build_context(models=(model("m1", 0.50, 0.30, 0.20),)))
    many_models = tuple(model(f"m{index}", 0.50, 0.30, 0.20) for index in range(1, 7))
    capped = ConfidenceEngine().run(build_context(models=many_models))
    assert no_models.confidence is not None
    assert one_model.confidence is not None
    assert capped.confidence is not None
    assert no_models.confidence.model == 0.50
    assert one_model.confidence.model == 0.65
    assert capped.confidence.model == 0.95


def test_model_disagreement_reduces_consensus_confidence() -> None:
    agreeing = ConfidenceEngine().run(
        build_context(
            models=(
                model("a", 0.70, 0.20, 0.10),
                model("b", 0.70, 0.20, 0.10),
            )
        )
    )
    disagreeing = ConfidenceEngine().run(
        build_context(
            models=(
                model("a", 0.80, 0.10, 0.10),
                model("b", 0.10, 0.10, 0.80),
            )
        )
    )
    assert agreeing.confidence is not None
    assert disagreeing.confidence is not None
    assert agreeing.confidence.consensus > disagreeing.confidence.consensus


def test_engine_returns_new_context_without_mutating_original() -> None:
    original = build_context(complete_context=True)
    result = ConfidenceEngine().run(original)
    assert original.confidence is None
    assert result.confidence is not None
    assert result is not original


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.90, ConfidenceBand.VERY_HIGH),
        (0.75, ConfidenceBand.HIGH),
        (0.55, ConfidenceBand.MEDIUM),
        (0.40, ConfidenceBand.LOW),
        (0.20, ConfidenceBand.VERY_LOW),
    ],
)
def test_band_boundaries(score: float, expected: ConfidenceBand) -> None:
    assert _band_from_score(score) is expected
