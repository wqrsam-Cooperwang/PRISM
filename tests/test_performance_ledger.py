import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.collection import CollectionGateDecision, CollectionReadinessGateResult
from src.domain.models import ModelOutput
from src.features import FeatureVector
from src.intelligence import (
    IntelligenceCategory,
    Observation,
    ReadinessLevel,
    SourceRef,
    SourceType,
)
from src.ledger import FileSystemPredictionLedgerStore, build_prediction_snapshot
from src.ledger import formal as formal_module
from src.report.models import (
    ConsensusReport,
    MatchReport,
    PredictionReport,
    ProvenanceReport,
    ScorelineCandidateReport,
    ScorelineReport,
)

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
KICKOFF = NOW + timedelta(hours=4)


def _recommended_scorelines() -> tuple[ScorelineCandidateReport, ScorelineCandidateReport]:
    return (
        ScorelineCandidateReport(home_goals=1, away_goals=0, probability=0.14),
        ScorelineCandidateReport(home_goals=1, away_goals=1, probability=0.13),
    )


def _report() -> PredictionReport:
    return PredictionReport(
        match=MatchReport(
            match_id="ledger-match-001",
            competition="Allsvenskan",
            kickoff=KICKOFF,
            home_team="GAIS",
            away_team="Halmstads BK",
        ),
        consensus=ConsensusReport(
            home_probability=0.51,
            draw_probability=0.27,
            away_probability=0.22,
            leading_outcome="home",
            agreement=0.81,
            model_count=2,
        ),
        confidence=None,
        evidence=None,
        decision=None,
        adjustment=None,
        scoreline=ScorelineReport(
            available=True,
            method="poisson",
            expected_home_goals=1.62,
            expected_away_goals=0.94,
            top_scorelines=_recommended_scorelines(),
            recommended_scorelines=_recommended_scorelines(),
            source_model_ids=("elo", "market"),
            grid_probability_mass=0.98,
            tail_mass=0.02,
        ),
        provenance=ProvenanceReport(
            prism_version="test",
            schema_version="1.0.0",
            runtime_version="test",
            session_id="ledger-session-001",
            git_commit="abc123",
        ),
    )


def _observation() -> Observation:
    return Observation(
        observation_id="market-home-odds",
        category=IntelligenceCategory.MARKET,
        claim_key="home_decimal_odds",
        value=1.95,
        source=SourceRef(source_id="the-odds-api:pinnacle", source_type=SourceType.MARKET),
        observed_at=NOW - timedelta(minutes=5),
        collected_at=NOW,
        subject="home",
        confidence=1.0,
    )


def _gate() -> CollectionReadinessGateResult:
    return CollectionReadinessGateResult(
        decision=CollectionGateDecision.READY,
        covered_core_categories=(
            IntelligenceCategory.TEAM_STRENGTH,
            IntelligenceCategory.RECENT_FORM,
            IntelligenceCategory.AVAILABILITY,
            IntelligenceCategory.SCHEDULE,
            IntelligenceCategory.MARKET,
        ),
        missing_core_categories=(),
        covered_optional_categories=(),
        source_ids=("the-odds-api:pinnacle",),
        source_types=("market",),
        elo_baseline_available=True,
        market_baseline_available=True,
        reasons=(),
    )


def _features() -> FeatureVector:
    return FeatureVector(
        values={"elo_difference": 75.0, "market_home_probability": 0.51},
        missing_features=(),
        intelligence_fingerprint="intel-fingerprint",
        readiness=ReadinessLevel.STANDARD,
        fingerprint="feature-fingerprint",
    )


def _model_output() -> ModelOutput:
    return ModelOutput(
        model_id="team-statistics",
        model_version="test",
        home_probability=0.51,
        draw_probability=0.27,
        away_probability=0.22,
        expected_home_goals=1.62,
        expected_away_goals=0.94,
    )


def _available_shadow() -> dict[str, object]:
    scorelines = [
        {"home_goals": 1, "away_goals": 0, "probability": 0.14},
        {"home_goals": 1, "away_goals": 1, "probability": 0.13},
    ]
    return {
        "schema_version": "1.0.0",
        "candidate_version": "2.2.0-candidate1",
        "status": "available",
        "direction_calibration": {
            "home_probability": 0.48,
            "draw_probability": 0.29,
            "away_probability": 0.23,
            "reliability": 0.80,
            "method": "test",
        },
        "scoreline": {
            "available": True,
            "method": "regime_scenario_mixture_poisson_v2_2_candidate",
            "recommended_scorelines": scorelines,
        },
    }


def test_snapshot_contains_auditable_exact_score_and_source_data() -> None:
    snapshot = build_prediction_snapshot(
        _report(),
        (_observation(),),
        _gate(),
        _features(),
        frozen_at=NOW,
    )

    assert snapshot.prediction_id.startswith("pred-")
    assert snapshot.match_id == "ledger-match-001"
    assert snapshot.payload["report"]["scoreline"]["top_scorelines"][0] == {
        "home_goals": 1,
        "away_goals": 0,
        "probability": 0.14,
    }
    assert snapshot.payload["observations"][0]["source"]["source_id"] == "the-odds-api:pinnacle"
    assert snapshot.payload["collection_gate"]["decision"] == "ready"
    assert snapshot.payload["features"]["values"]["elo_difference"] == pytest.approx(75.0)


def test_filesystem_store_is_append_only_and_json_durable(tmp_path: Path) -> None:
    snapshot = build_prediction_snapshot(
        _report(),
        (_observation(),),
        _gate(),
        _features(),
        frozen_at=NOW,
    )
    store = FileSystemPredictionLedgerStore(tmp_path)

    path = store.persist(snapshot)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved["prediction_id"] == snapshot.prediction_id
    assert saved["payload"]["report"]["match"]["home_team"] == "GAIS"
    with pytest.raises(FileExistsError, match="already exists"):
        store.persist(snapshot)


def test_snapshot_rejects_freeze_at_or_after_kickoff() -> None:
    with pytest.raises(ValueError, match="before kickoff"):
        build_prediction_snapshot(
            _report(),
            (_observation(),),
            _gate(),
            _features(),
            frozen_at=KICKOFF,
        )


def test_formal_prediction_fails_closed_when_persistence_fails(monkeypatch) -> None:
    production = SimpleNamespace(
        report=_report(),
        observations=(_observation(),),
        collection_gate=_gate(),
        features=_features(),
        runtime_result=SimpleNamespace(
            context=SimpleNamespace(model_outputs=(_model_output(),)),
        ),
    )
    monkeypatch.setattr(
        formal_module,
        "run_acquired_prediction_path",
        lambda *args, **kwargs: production,
    )
    monkeypatch.setattr(
        formal_module,
        "build_v22_shadow_payload",
        lambda context: _available_shadow(),
    )

    class FailingStore:
        def persist(self, snapshot):
            del snapshot
            raise OSError("ledger unavailable")

    with pytest.raises(OSError, match="ledger unavailable"):
        formal_module.run_formal_acquired_prediction_path(
            request=object(),
            clients=(),
            adapters=(),
            ledger_store=FailingStore(),
            collected_at=NOW,
            frozen_at=NOW,
            prism_version="test",
        )
