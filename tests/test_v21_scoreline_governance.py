from datetime import datetime, timezone

import pytest

from src.consensus.correlation import family_capped_weights
from src.consensus.engine import ConsensusEngine
from src.domain.models import (
    AnalysisSession,
    DecisionOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.scoreline.diversity import select_diversified_pair
from src.scoreline.engine import ScorelineEngine
from src.scoreline.models import ScorelineCandidate


def _context(models: tuple[ModelOutput, ...]) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="v21-regression",
            created_at=datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc),
            prism_version="2.1.0",
        ),
        match=MatchInfo(
            match_id="v21-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 28, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("home", "Home FC"),
        away_team=TeamInfo("away", "Away FC"),
        model_outputs=models,
        decision=DecisionOutput(),
    )


def _model(
    model_id: str,
    home: float,
    draw: float,
    away: float,
    *,
    home_xg: float | None = None,
    away_xg: float | None = None,
    evidence_family: str | None = None,
    assumption_family: str | None = None,
) -> ModelOutput:
    diagnostics: dict[str, str] = {}
    if evidence_family is not None:
        diagnostics["evidence_family"] = evidence_family
    if assumption_family is not None:
        diagnostics["assumption_family"] = assumption_family
    return ModelOutput(
        model_id=model_id,
        model_version="1.0.0",
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
        expected_home_goals=home_xg,
        expected_away_goals=away_xg,
        diagnostics=diagnostics,
    )


def test_correlated_evidence_family_gets_one_unit_of_mass() -> None:
    models = (
        _model("market-a", 0.80, 0.10, 0.10, evidence_family="market"),
        _model("market-b", 0.80, 0.10, 0.10, evidence_family="market"),
        _model("strength", 0.20, 0.30, 0.50, evidence_family="strength"),
    )

    weights = family_capped_weights(models)

    assert weights == pytest.approx((0.25, 0.25, 0.50))


def test_consensus_does_not_double_count_duplicate_market_family() -> None:
    models = (
        _model("market-a", 0.80, 0.10, 0.10, evidence_family="market"),
        _model("market-b", 0.80, 0.10, 0.10, evidence_family="market"),
        _model("strength", 0.20, 0.30, 0.50, evidence_family="strength"),
    )

    result = ConsensusEngine().run(_context(models))

    assert result.consensus is not None
    assert result.consensus.home_probability == pytest.approx(0.50)
    assert result.consensus.draw_probability == pytest.approx(0.20)
    assert result.consensus.away_probability == pytest.approx(0.30)
    assert result.consensus.method == "correlated_evidence_family_cap"


def test_shared_xg_assumption_family_is_capped() -> None:
    models = (
        _model(
            "xg-a",
            0.60,
            0.25,
            0.15,
            home_xg=2.0,
            away_xg=0.5,
            assumption_family="shared",
        ),
        _model(
            "xg-b",
            0.60,
            0.25,
            0.15,
            home_xg=2.0,
            away_xg=0.5,
            assumption_family="shared",
        ),
        _model(
            "xg-independent",
            0.45,
            0.30,
            0.25,
            home_xg=1.0,
            away_xg=1.0,
            assumption_family="independent",
        ),
    )

    weights = family_capped_weights(models, use_assumption_family=True)

    assert weights == pytest.approx((0.25, 0.25, 0.50))


def test_symmetric_tail_floor_protects_low_scoring_side() -> None:
    engine = ScorelineEngine()

    rates = engine._scenario_rates(2.2, 0.05)

    tail_home, tail_away = rates["symmetric_tail_floor"]
    assert tail_home == pytest.approx(2.2)
    assert tail_away == pytest.approx(engine.defensive_tail_rate_floor)


def test_dual_score_selector_prefers_different_match_path() -> None:
    ranked = (
        ScorelineCandidate(1, 0, 0.20),
        ScorelineCandidate(2, 0, 0.19),
        ScorelineCandidate(1, 1, 0.18),
        ScorelineCandidate(2, 1, 0.15),
    )

    primary, alternative = select_diversified_pair(ranked)

    assert primary == ranked[0]
    assert alternative == ranked[2]


def test_scenario_mixture_is_deterministic() -> None:
    models = (
        _model(
            "xg",
            0.55,
            0.25,
            0.20,
            home_xg=1.7,
            away_xg=0.8,
            assumption_family="xg-independent",
        ),
    )
    context = _context(models)

    first = ScorelineEngine().run(context)
    second = ScorelineEngine().run(context)

    assert first == second
    assert len(first.top_scorelines) == 3
    assert len(first.recommended_scorelines) == 2
    assert first.recommended_scorelines[0] == first.top_scorelines[0]
