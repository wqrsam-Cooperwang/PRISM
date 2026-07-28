from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from src.evidence.providers import (
    PersonnelReliabilityEngine,
    HomeAwayRegimeEngine,
    RotationDepthEngine,
    PriorityEngine,
    GoalStateStrategyEngine,
    MarketGovernanceEngine,
    ScenarioProbabilityEngine,
)


def test_providers_basic() -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    match_context = {
        "match_id": "M-1",
        "observation_time": now,
        "confirmed_players": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11"],
        "expected_players": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11"],
        "player_quality": {"p1": 0.9, "p2": 0.85},
        "home_advantage_prior": 0.12,
        "homeaway_hist_n": 50,
        "is_knockout": False,
        "days_to_next": 3,
        "travel_distance_km": 150,
        "squad_depth": 0.9,
        "opponent_strength": 0.6,
        "team_style": "balanced",
        "market_odds": {"home": 1.8, "draw": 3.6, "away": 4.5},
        "market_volume": 100000.0,
        "market_sources": ["m1"],
        "scenarios": {"normal": 0.9, "rain": 0.1},
    }

    engines = [
        PersonnelReliabilityEngine(),
        HomeAwayRegimeEngine(),
        RotationDepthEngine(),
        PriorityEngine(),
        GoalStateStrategyEngine(),
        MarketGovernanceEngine(),
        ScenarioProbabilityEngine(),
    ]

    for engine in engines:
        ev = engine.produce_evidence(match_context)
        assert isinstance(ev, list)
        assert len(ev) >= 1
        for e in ev:
            assert e.provider_id
            assert e.evidence_id
            assert isinstance(e.suggestion, dict)
            assert isinstance(e.variance, dict)
            assert 0.0 <= e.reliability <= 1.0
            for v in e.variance.values():
                assert v >= 0.0


def test_providers_missing_observation_time() -> None:
    match_context = {"match_id": "M-1"}
    engines = [
        PersonnelReliabilityEngine(),
        HomeAwayRegimeEngine(),
        RotationDepthEngine(),
        PriorityEngine(),
        GoalStateStrategyEngine(),
        MarketGovernanceEngine(),
        ScenarioProbabilityEngine(),
    ]
    for engine in engines:
        try:
            engine.produce_evidence(match_context)
            assert False, "Expected ValueError for missing observation_time"
        except ValueError:
            pass
