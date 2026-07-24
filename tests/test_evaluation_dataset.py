import csv
import hashlib
import io
import json
from datetime import datetime, timezone

from src.domain.models import ModelOutput
from src.evaluation import (
    EvaluationCase,
    RealMatchEvaluationHarness,
    export_evaluation_csv,
    export_evaluation_jsonl,
    records_from_summary,
)
from src.runtime import MatchRequest


def _case(case_id: str, home_goals: int, away_goals: int) -> EvaluationCase:
    request = MatchRequest(
        match_id=f"match-{case_id}",
        competition="Dataset League",
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
        git_commit="dataset123",
        data_version="data-v1",
        rule_version="rules-v1",
        model_version="models-v1",
        prompt_version="prompts-v1",
    )


def _summary():
    return RealMatchEvaluationHarness().evaluate_many(
        (_case("first", 1, 0), _case("second", 0, 1))
    )


def test_records_from_summary_preserves_order_and_provenance() -> None:
    records = records_from_summary(_summary())

    assert tuple(record.case_id for record in records) == ("first", "second")
    assert records[0].competition == "Dataset League"
    assert records[0].home_team == "Home FC"
    assert records[0].prism_version == "3.2.0-alpha1"
    assert records[0].runtime_version == "1.0.0"
    assert records[0].git_commit == "dataset123"
    assert records[0].session_id == "session-first"


def test_jsonl_export_is_deterministic_and_hashes_exact_payload() -> None:
    generated_at = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)
    summary = _summary()

    first = export_evaluation_jsonl(summary, generated_at=generated_at)
    second = export_evaluation_jsonl(summary, generated_at=generated_at)

    assert first == second
    assert first.payload.endswith("\n")
    lines = first.payload.splitlines()
    assert len(lines) == 2
    decoded = [json.loads(line) for line in lines]
    assert [item["case_id"] for item in decoded] == ["first", "second"]
    assert first.manifest.record_count == 2
    assert first.manifest.format == "jsonl"
    assert first.manifest.generated_at == generated_at.isoformat()
    assert first.manifest.content_sha256 == hashlib.sha256(
        first.payload.encode("utf-8")
    ).hexdigest()
    assert first.manifest.prism_versions == ("3.2.0-alpha1",)
    assert first.manifest.git_commits == ("dataset123",)


def test_csv_export_has_fixed_header_and_normalized_booleans() -> None:
    generated_at = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)
    exported = export_evaluation_csv(_summary(), generated_at=generated_at)

    assert exported.payload.endswith("\n")
    rows = list(csv.DictReader(io.StringIO(exported.payload)))
    assert len(rows) == 2
    assert rows[0]["case_id"] == "first"
    assert rows[0]["top1_correct"] == "true"
    assert rows[1]["top1_correct"] == "false"
    assert exported.manifest.format == "csv"
    assert exported.manifest.content_sha256 == hashlib.sha256(
        exported.payload.encode("utf-8")
    ).hexdigest()


def test_export_rejects_naive_generated_at() -> None:
    summary = _summary()
    naive = datetime(2026, 7, 27, 9, 0)

    try:
        export_evaluation_jsonl(summary, generated_at=naive)
    except ValueError as exc:
        assert "timezone-aware" in str(exc)
    else:
        raise AssertionError("expected timezone-aware validation")
