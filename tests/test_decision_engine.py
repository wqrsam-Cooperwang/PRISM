from datetime import datetime, timezone

import pytest

from src.decision.engine import DecisionEngine
from src.domain.models import (
    AdjustmentOutput,
    AnalysisSession,
    ConsensusOutput,
    DecisionAction,
    MatchContext,
    MatchInfo,
    TeamInfo,
)


def build_context(
    *,
    adjustment: AdjustmentOutput | None = None,
    consensus: ConsensusOutput | None = None,
    market: dict[str, float] | None = None,
) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="decision-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="decision-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        market={} if market is None else market,
        consensus=consensus,
        adjustment=adjustment,
    )


def consensus(
    home: float = 0.58,
    draw: float = 0.24,
    away: float = 0.18,
    margin: float = 0.34,
) -> ConsensusOutput:
    return ConsensusOutput(
        model_count=2,
        model_ids=("m1", "m2"),
        home_probability=home,
        draw_probability=draw,
        away_probability=away,
        agreement=0.95,
        mean_pairwise_distance=0.05,
        max_spread=0.08,
        leading_outcome="home",
        margin=margin,
    )


def adjustment(confidence: float = 0.80, blocked: bool = False) -> AdjustmentOutput:
    return AdjustmentOutput(
        base_confidence=confidence,
        adjusted_confidence=confidence,
        decision_blocked=blocked,
    )


def full_odds(home: float = 2.0, draw: float = 4.2, away: float = 6.0) -> dict[str, float]:
    return {"home_odds": home, "draw_odds": draw, "away_odds": away}


def test_requires_consensus_and_adjustment() -> None:
    with pytest.raises(ValueError, match="requires consensus"):
        DecisionEngine().run(build_context(adjustment=adjustment()))
    with pytest.raises(ValueError, match="requires adjustment"):
        DecisionEngine().run(build_context(consensus=consensus()))


def test_blocked_adjustment_forces_no_decision() -> None:
    result = DecisionEngine().run(
        build_context(
            consensus=consensus(),
            adjustment=adjustment(blocked=True),
            market=full_odds(),
        )
    )
    assert result.decision is not None
    assert result.decision.action is DecisionAction.NO_DECISION
    assert result.decision.selected_market is None


def test_missing_or_partial_odds_yields_watch() -> None:
    missing = DecisionEngine().run(build_context(consensus=consensus(), adjustment=adjustment()))
    partial = DecisionEngine().run(
        build_context(
            consensus=consensus(),
            adjustment=adjustment(),
            market={"home_odds": 2.0},
        )
    )
    assert missing.decision is not None
    assert partial.decision is not None
    assert missing.decision.action is DecisionAction.WATCH
    assert partial.decision.action is DecisionAction.WATCH


def test_invalid_decimal_odds_are_rejected() -> None:
    context = build_context(
        consensus=consensus(),
        adjustment=adjustment(),
        market=full_odds(home=1.0),
    )
    with pytest.raises(ValueError, match="greater than 1"):
        DecisionEngine().run(context)


def test_candidate_requires_all_policy_gates() -> None:
    result = DecisionEngine().run(
        build_context(
            consensus=consensus(),
            adjustment=adjustment(0.80),
            market=full_odds(),
        )
    )
    assert result.decision is not None
    assert result.decision.action is DecisionAction.CANDIDATE
    assert result.decision.selected_market == "home"
    assert result.decision.expected_value == 0.16
    assert result.decision.risk_level == "medium"


def test_positive_ev_is_insufficient_when_confidence_is_low() -> None:
    result = DecisionEngine().run(
        build_context(
            consensus=consensus(),
            adjustment=adjustment(0.60),
            market=full_odds(),
        )
    )
    assert result.decision is not None
    assert result.decision.expected_value is not None
    assert result.decision.expected_value > 0
    assert result.decision.action is DecisionAction.NO_BET
    assert result.decision.risk_level == "high"


def test_consensus_margin_gate_can_prevent_candidate() -> None:
    result = DecisionEngine().run(
        build_context(
            consensus=consensus(home=0.40, draw=0.37, away=0.23, margin=0.03),
            adjustment=adjustment(0.80),
            market=full_odds(home=3.0, draw=2.5, away=5.0),
        )
    )
    assert result.decision is not None
    assert result.decision.action is DecisionAction.NO_BET


def test_highest_ev_market_is_selected() -> None:
    result = DecisionEngine().run(
        build_context(
            consensus=consensus(),
            adjustment=adjustment(0.90),
            market=full_odds(home=1.8, draw=5.0, away=7.0),
        )
    )
    assert result.decision is not None
    assert result.decision.selected_market == "away"
    assert result.decision.risk_level == "low"


def test_ev_ties_use_home_draw_away_order() -> None:
    result = DecisionEngine(
        minimum_adjusted_confidence=0.0,
        minimum_expected_value=-1.0,
        minimum_consensus_margin=0.0,
    ).run(
        build_context(
            consensus=consensus(home=0.5, draw=0.25, away=0.25, margin=0.25),
            adjustment=adjustment(0.5),
            market=full_odds(home=2.0, draw=4.0, away=4.0),
        )
    )
    assert result.decision is not None
    assert result.decision.selected_market == "home"


def test_engine_is_immutable() -> None:
    original = build_context(
        consensus=consensus(),
        adjustment=adjustment(),
        market=full_odds(),
    )
    result = DecisionEngine().run(original)
    assert original.decision is None
    assert result.decision is not None
    assert result is not original


def test_policy_parameters_validate_numeric_ranges() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        DecisionEngine(minimum_adjusted_confidence=1.1)
    with pytest.raises(ValueError, match="between 0 and 1"):
        DecisionEngine(minimum_consensus_margin=-0.1)
    with pytest.raises(ValueError, match="finite"):
        DecisionEngine(minimum_expected_value=float("nan"))
