from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.domain.models import (
    AdjustmentOutput,
    AnalysisSession,
    MatchContext,
    MatchInfo,
    TeamInfo,
)


def build_context() -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="adjustment-domain-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="3.2.0-alpha1",
        ),
        match=MatchInfo(
            match_id="adjustment-domain-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
    )


def test_adjustment_output_rejects_increasing_confidence() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        AdjustmentOutput(base_confidence=0.5, adjusted_confidence=0.6)


def test_adjustment_cap_must_be_bounded() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        AdjustmentOutput(
            base_confidence=0.5,
            adjusted_confidence=0.5,
            confidence_cap=1.2,
        )


def test_adjustment_serializes_inside_match_context() -> None:
    adjustment = AdjustmentOutput(
        base_confidence=0.8,
        adjusted_confidence=0.69,
        confidence_cap=0.69,
        applied_effects=("restrict_high_confidence_action",),
        observed_effects=("restrict_high_confidence_action", "flag_market_movement"),
        rationale=("confidence_cap=0.69",),
    )
    payload = replace(build_context(), adjustment=adjustment).to_dict()
    assert payload["adjustment"]["adjusted_confidence"] == 0.69
    assert payload["adjustment"]["applied_effects"] == ["restrict_high_confidence_action"]
