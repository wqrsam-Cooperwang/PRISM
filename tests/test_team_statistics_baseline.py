from datetime import datetime, timezone

import pytest

from src.collection import SourceEnvelope, TeamStatisticsAdapter
from src.features import FeatureVector
from src.intelligence import MatchTarget, ReadinessLevel, SourceRef, SourceType
from src.prediction import TeamScoringRateExpectedGoalsModel, TeamStatisticsProbabilityModel

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


def _target() -> MatchTarget:
    return MatchTarget(
        match_id="allsvenskan-gais-halmstad-20260726",
        competition="Allsvenskan",
        kickoff=datetime(2026, 7, 26, 14, 30, tzinfo=timezone.utc),
        home_team_id="gais",
        home_team_name="GAIS",
        away_team_id="halmstads-bk",
        away_team_name="Halmstads BK",
        season="2026",
    )


def _statistics() -> dict[str, object]:
    return {
        "form": "WWDLW",
        "fixtures": {
            "played": {"home": 7, "away": 7, "total": 14},
            "wins": {"home": 5, "away": 3, "total": 8},
            "draws": {"home": 1, "away": 2, "total": 3},
            "loses": {"home": 1, "away": 2, "total": 3},
        },
        "goals": {
            "for": {"total": {"home": 15, "away": 11, "total": 26}},
            "against": {"total": {"home": 7, "away": 10, "total": 17}},
        },
    }


def test_team_statistics_adapter_derives_transparent_strength_observations() -> None:
    envelope = SourceEnvelope(
        adapter_id="team_statistics",
        source=SourceRef(
            source_id="api-football:team-statistics:123",
            source_type=SourceType.PRIMARY_DATA,
            publisher="API-Football",
        ),
        retrieved_at=NOW,
        payload={
            "side": "home",
            "provider_team_id": 123,
            "league_id": 113,
            "season": 2026,
            "statistics": _statistics(),
        },
    )

    observations = TeamStatisticsAdapter().adapt(_target(), envelope)
    by_key = {item.claim_key: item.value for item in observations}

    assert by_key["points_per_game"] == pytest.approx(27.0 / 14.0)
    assert by_key["goal_difference_per_game"] == pytest.approx(9.0 / 14.0)
    assert by_key["goals_for_per_game"] == pytest.approx(26.0 / 14.0)
    assert by_key["goals_against_per_game"] == pytest.approx(17.0 / 14.0)
    assert by_key["points_last_5"] == 10
    assert all(item.subject == "home" for item in observations)


def test_team_statistics_adapter_rejects_inconsistent_fixture_totals() -> None:
    statistics = _statistics()
    fixtures = statistics["fixtures"]
    assert isinstance(fixtures, dict)
    fixtures["wins"] = {"home": 6, "away": 4, "total": 10}
    envelope = SourceEnvelope(
        adapter_id="team_statistics",
        source=SourceRef(
            source_id="api-football:team-statistics:123",
            source_type=SourceType.PRIMARY_DATA,
        ),
        retrieved_at=NOW,
        payload={"side": "home", "statistics": statistics},
    )

    with pytest.raises(ValueError, match="must sum"):
        TeamStatisticsAdapter().adapt(_target(), envelope)


def test_team_statistics_probability_model_is_normalized_and_directional() -> None:
    features = FeatureVector(
        values={
            "team_points_per_game_difference": 0.55,
            "team_goal_difference_per_game_difference": 0.45,
            "recent_points_difference": 4.0,
        },
        missing_features=(),
        intelligence_fingerprint="intel-team-stats",
        readiness=ReadinessLevel.STANDARD,
        fingerprint="features-team-stats",
    )

    output = TeamStatisticsProbabilityModel().predict(features)
    probability_total = output.home_probability + output.draw_probability + output.away_probability

    assert output.home_probability > output.away_probability
    assert probability_total == pytest.approx(1.0)
    assert output.diagnostics["method"] == "provisional_team_statistics_davidson"


def test_scoring_rate_xg_model_produces_auditable_expected_goals() -> None:
    features = FeatureVector(
        values={
            "home_goals_for_per_game": 1.40,
            "home_goals_against_per_game": 1.20,
            "away_goals_for_per_game": 1.60,
            "away_goals_against_per_game": 1.00,
        },
        missing_features=(),
        intelligence_fingerprint="intel-scoring-rates",
        readiness=ReadinessLevel.STANDARD,
        fingerprint="features-scoring-rates",
    )

    output = TeamScoringRateExpectedGoalsModel().predict(features)
    probability_total = output.home_probability + output.draw_probability + output.away_probability

    assert output.expected_home_goals == pytest.approx(1.20)
    assert output.expected_away_goals == pytest.approx(1.40)
    assert probability_total == pytest.approx(1.0)
    assert output.diagnostics["method"] == "scoring_conceding_rate_mean_poisson"
    assert output.diagnostics["evidence_family"] == "team_strength"
    assert output.diagnostics["assumption_family"] == "team_scoring_rates"
