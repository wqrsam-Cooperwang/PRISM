from dataclasses import replace
from datetime import datetime, timezone

import pytest

from src.domain.models import ModelOutput
from src.evaluation import (
    EvaluationCase,
    RealMatchEvaluationHarness,
    export_evaluation_csv,
    export_evaluation_jsonl,
    import_evaluation_csv,
    import_evaluation_jsonl,
    load_benchmark,
    records_from_summary,
)
from src.runtime import MatchRequest


def _case(case_id: str, home_goals: int, away_goals: int) -> EvaluationCase:
    request = MatchRequest(
        match_id=f"match-{case_id}",
        competition="Benchmark League",
        kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        home_team_id="home",
        home_team_name="Home FC",
        away_team_id="away",
        away_team_name="Away FC",
        model_outputs=(
            ModelOutput("poisson", "1.0.0", 0.60, 0.22, 0.18, 1.7, 0.8),
            ModelOutput("elo", "1.0.0", 0.58, 0.23, 0.19, 1.5, 0.8),
        ),
        lineups={"confirmed": True},
        injuries={"home": [], "away": []},
        market={"home_odds": 2.20, "draw_odds": 4.50, "away_odds": 7.00},
        weather={"condition": "clear"},
        schedule={"home_rest_days": 6, "away_rest_days": 6},
        tactical={"home_shape": "4-3-3", "away_shape": "4-2-3-1"},
    )
    return EvaluationCase(
        case_id=case_id,
        request=request,
        completeness={
            "lineup": 1.0,
            "injuries": 1.0,
            "odds": 1.0,
            "weather": 1.0,
            "tactical_data": 1.0,
            "historical_data": 1.0,
            "market_data": 1.0,
            "motivation": 1.0,
        },
        prism_version="3.2.0-alpha1",
        actual_home_goals=home_goals,
        actual_away_goals=away_goals,
        session_id=f"session-{case_id}",
        created_at=datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc),
        git_commit="benchmark123",
    )


def _summary():
    return RealMatchEvaluationHarness().evaluate_many(
        (_case("first", 1, 0), _case("second", 0, 1))
    )


def test_jsonl_round_trip_preserves_exported_records() -> None:
    generated_at = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)
    summary = _summary()
    exported = export_evaluation_jsonl(summary, generated_at=generated_at)

    imported = import_evaluation_jsonl(exported.payload, exported.manifest)

    assert imported == records_from_summary(summary)


def test_csv_round_trip_restores_canonical_types() -> None:
    generated_at = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)
    summary = _summary()
    exported = export_evaluation_csv(summary, generated_at=generated_at)

    imported = import_evaluation_csv(exported.payload, exported.manifest)

    assert imported == records_from_summary(summary)
    assert imported[0].top1_correct is True
    assert imported[1].top1_correct is False
    assert imported[0].actual_home_goals == 1
    assert isinstance(imported[0].brier_score, float)


def test_import_fails_closed_when_manifest_hash_does_not_match() -> None:
    exported = export_evaluation_jsonl(
        _summary(),
        generated_at=datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc),
    )
    tampered = exported.payload.replace('"case_id":"first"', '"case_id":"changed"', 1)

    with pytest.raises(ValueError, match="SHA-256"):
        import_evaluation_jsonl(tampered, exported.manifest)


def test_import_rejects_unsupported_schema_version() -> None:
    exported = export_evaluation_jsonl(
        _summary(),
        generated_at=datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc),
    )
    payload = exported.payload.replace(
        '"dataset_schema_version":"1.0.0"',
        '"dataset_schema_version":"2.0.0"',
        1,
    )

    with pytest.raises(ValueError, match="unsupported dataset_schema_version"):
        import_evaluation_jsonl(payload)


def test_import_rejects_manifest_format_mismatch() -> None:
    exported = export_evaluation_jsonl(
        _summary(),
        generated_at=datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc),
    )
    wrong_manifest = replace(exported.manifest, format="csv")

    with pytest.raises(ValueError, match="format mismatch"):
        import_evaluation_jsonl(exported.payload, wrong_manifest)


def test_load_benchmark_aggregates_imported_historical_records() -> None:
    exported = export_evaluation_jsonl(
        _summary(),
        generated_at=datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc),
    )
    records = import_evaluation_jsonl(exported.payload, exported.manifest)

    benchmark = load_benchmark(records)

    assert benchmark.record_count == 2
    assert benchmark.top1_accuracy == pytest.approx(0.5)
    assert benchmark.scoreline_available_count == 2
    assert benchmark.scoreline_top3_hit_rate == pytest.approx(0.5)
    assert benchmark.candidate_count == 2
    assert benchmark.candidate_accuracy == pytest.approx(0.5)
    assert benchmark.mean_brier_score == pytest.approx(
        sum(record.brier_score for record in records) / 2
    )
    assert benchmark.mean_log_loss == pytest.approx(
        sum(record.log_loss for record in records) / 2
    )
    assert benchmark.prism_versions == ("3.2.0-alpha1",)
    assert benchmark.runtime_versions == ("1.0.0",)
    assert benchmark.git_commits == ("benchmark123",)
    assert benchmark.competitions == ("Benchmark League",)


def test_import_and_benchmark_reject_empty_inputs() -> None:
    with pytest.raises(ValueError, match="at least one record"):
        import_evaluation_jsonl("")
    with pytest.raises(ValueError, match="at least one record"):
        load_benchmark(())
