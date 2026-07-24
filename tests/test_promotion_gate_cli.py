import json
from dataclasses import asdict, replace
from pathlib import Path

from scripts.promotion_gate import run_gate
from src.evaluation import EvaluationRecord


def _record(case_id: str, *, prism_version: str, git_commit: str) -> EvaluationRecord:
    return EvaluationRecord(
        dataset_schema_version="1.0.0",
        case_id=case_id,
        match_id=f"match-{case_id}",
        competition="Promotion League",
        kickoff="2026-07-25T18:00:00+00:00",
        home_team="Home FC",
        away_team="Away FC",
        actual_home_goals=1,
        actual_away_goals=0,
        actual_outcome="home",
        home_probability=0.60,
        draw_probability=0.22,
        away_probability=0.18,
        leading_outcome="home",
        leading_probability=0.60,
        brier_score=0.40,
        log_loss=0.60,
        top1_correct=True,
        scoreline_top3_hit=True,
        decision_action="candidate",
        selected_market="home",
        candidate_correct=True,
        overall_confidence=0.70,
        evidence_gate="deep",
        prism_version=prism_version,
        runtime_version="1.0.0",
        git_commit=git_commit,
        data_version="data-v1",
        rule_version="rules-v1",
        model_version="models-v1",
        prompt_version="prompts-v1",
        session_id=f"session-{case_id}",
    )


def _write_jsonl(path: Path, records: tuple[EvaluationRecord, ...]) -> None:
    payload = "".join(
        json.dumps(asdict(record), sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    )
    path.write_text(payload, encoding="utf-8")


def _datasets(tmp_path: Path) -> tuple[Path, Path]:
    baseline = (
        _record("first", prism_version="3.2.0", git_commit="base"),
        replace(
            _record("second", prism_version="3.2.0", git_commit="base"),
            brier_score=0.60,
            log_loss=0.80,
            top1_correct=False,
            scoreline_top3_hit=False,
            candidate_correct=False,
        ),
    )
    candidate = (
        replace(
            baseline[0],
            brier_score=0.30,
            log_loss=0.50,
            prism_version="3.3.0",
            git_commit="candidate",
        ),
        replace(
            baseline[1],
            brier_score=0.40,
            log_loss=0.60,
            top1_correct=True,
            scoreline_top3_hit=True,
            candidate_correct=True,
            prism_version="3.3.0",
            git_commit="candidate",
        ),
    )
    baseline_path = tmp_path / "baseline.jsonl"
    candidate_path = tmp_path / "candidate.jsonl"
    _write_jsonl(baseline_path, baseline)
    _write_jsonl(candidate_path, candidate)
    return baseline_path, candidate_path


def test_run_gate_writes_all_reports_before_returning_promote_code(tmp_path: Path) -> None:
    baseline, candidate = _datasets(tmp_path)
    output = tmp_path / "reports"

    exit_code = run_gate(
        baseline,
        candidate,
        output,
        minimum_case_count=2,
        minimum_brier_improvement=0.001,
    )

    assert exit_code == 0
    assert sorted(path.name for path in output.iterdir()) == [
        "comparison.json",
        "comparison.md",
        "promotion-decision.json",
        "promotion-decision.md",
    ]
    decision = json.loads((output / "promotion-decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "promote"
    assert decision["release_gate"] == {"allowed": True, "exit_code": 0}


def test_run_gate_returns_hold_code_but_still_writes_reports(tmp_path: Path) -> None:
    baseline, candidate = _datasets(tmp_path)
    output = tmp_path / "reports"

    exit_code = run_gate(baseline, candidate, output, minimum_case_count=3)

    assert exit_code == 2
    decision = json.loads((output / "promotion-decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "hold"
    assert decision["release_gate"] == {"allowed": False, "exit_code": 2}


def test_run_gate_returns_reject_code_for_required_metric_regression(tmp_path: Path) -> None:
    baseline, candidate = _datasets(tmp_path)
    candidate_records = tuple(
        replace(record, log_loss=1.50)
        for record in (
            _record("first", prism_version="3.3.0", git_commit="candidate"),
            _record("second", prism_version="3.3.0", git_commit="candidate"),
        )
    )
    _write_jsonl(candidate, candidate_records)
    output = tmp_path / "reports"

    exit_code = run_gate(baseline, candidate, output, minimum_case_count=2)

    assert exit_code == 3
    decision = json.loads((output / "promotion-decision.json").read_text(encoding="utf-8"))
    assert decision["decision"] == "reject"
    assert decision["release_gate"] == {"allowed": False, "exit_code": 3}
