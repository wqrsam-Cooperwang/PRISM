from datetime import datetime, timezone

from src.domain.models import (
    AnalysisSession,
    ConsensusOutput,
    DecisionOutput,
    EvidenceGate,
    EvidenceOutput,
    MatchContext,
    MatchInfo,
    ModelOutput,
    TeamInfo,
)
from src.ledger import V22_SHADOW_SCHEMA_VERSION, build_v22_shadow_payload


def _context(*, with_consensus: bool = True) -> MatchContext:
    consensus = None
    if with_consensus:
        consensus = ConsensusOutput(
            model_count=2,
            model_ids=("market", "team-stats"),
            home_probability=0.56,
            draw_probability=0.26,
            away_probability=0.18,
            agreement=0.82,
            mean_pairwise_distance=0.08,
            max_spread=0.10,
            leading_outcome="home",
            margin=0.30,
            method="test",
        )
    return MatchContext(
        session=AnalysisSession(
            session_id="shadow-ledger-test",
            created_at=datetime(2026, 7, 27, tzinfo=timezone.utc),
            prism_version="2.1.0",
        ),
        match=MatchInfo(
            match_id="shadow-test-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 28, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo("home", "Home"),
        away_team=TeamInfo("away", "Away"),
        evidence=EvidenceOutput(
            score=84,
            raw_score=84.0,
            gate=EvidenceGate.STANDARD,
        ),
        model_outputs=(
            ModelOutput(
                model_id="market",
                model_version="1",
                home_probability=0.56,
                draw_probability=0.26,
                away_probability=0.18,
                expected_home_goals=1.62,
                expected_away_goals=0.94,
            ),
            ModelOutput(
                model_id="team-stats",
                model_version="1",
                home_probability=0.54,
                draw_probability=0.27,
                away_probability=0.19,
                expected_home_goals=1.55,
                expected_away_goals=1.01,
            ),
        ),
        consensus=consensus,
        decision=DecisionOutput(),
    )


def test_v22_shadow_freezes_direction_and_dual_scoreline() -> None:
    payload = build_v22_shadow_payload(_context())

    assert payload["schema_version"] == V22_SHADOW_SCHEMA_VERSION
    assert payload["status"] == "available"
    assert payload["candidate_version"] == "2.2.0-candidate1"
    direction = payload["direction_calibration"]
    scoreline = payload["scoreline"]
    assert direction["calibrated_leading_probability"] < direction["raw_leading_probability"]
    assert len(scoreline["recommended_scorelines"]) == 2
    assert scoreline["method"] == "regime_scenario_mixture_poisson_v2_2_candidate"


def test_v22_shadow_records_missing_full_stack_inputs_without_breaking_production() -> None:
    payload = build_v22_shadow_payload(_context(with_consensus=False))

    assert payload["status"] == "unavailable"
    assert "consensus and evidence" in payload["reason"]
