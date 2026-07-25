from datetime import datetime, timezone

from src.collection import FixtureObservationAdapter, SourceEnvelope
from src.intelligence import MatchTarget, SourceRef, SourceType
from src.prediction import run_collected_prediction_path

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
OBSERVED = "2026-07-24T11:00:00+00:00"


def _row(
    observation_id: str,
    category: str,
    claim_key: str,
    value: object,
    subject: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "observation_id": observation_id,
        "category": category,
        "claim_key": claim_key,
        "value": value,
        "observed_at": OBSERVED,
        "confidence": 0.95,
    }
    if subject is not None:
        row["subject"] = subject
    return row


def test_degraded_collection_effect_is_carried_into_prediction_context() -> None:
    target = MatchTarget(
        match_id="degraded-collected-001",
        competition="Test League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home-id",
        home_team_name="Home FC",
        away_team_id="away-id",
        away_team_name="Away FC",
    )
    envelope = SourceEnvelope(
        adapter_id="fixture_observations",
        source=SourceRef(source_id="baseline-provider", source_type=SourceType.PRIMARY_DATA),
        retrieved_at=NOW,
        payload={
            "observations": [
                _row("home-elo", "team_strength", "elo_rating", 1600, "home"),
                _row("away-elo", "team_strength", "elo_rating", 1550, "away"),
                _row("home-odds", "market", "home_decimal_odds", 2.0),
                _row("draw-odds", "market", "draw_decimal_odds", 3.5),
                _row("away-odds", "market", "away_decimal_odds", 4.0),
            ]
        },
    )

    result = run_collected_prediction_path(
        target,
        (FixtureObservationAdapter(),),
        (envelope,),
        collected_at=NOW,
        prism_version="test",
        created_at=NOW,
    )

    assert result.collection_gate.decision.value == "degraded"
    governance = result.prediction.context.rule_outputs[-1]
    assert governance["governance_source"] == "collection_readiness_gate"
    assert governance["collection_gate_decision"] == "degraded"
    assert governance["effective_effects"] == ("restrict_high_confidence_action",)
