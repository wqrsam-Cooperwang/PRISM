"""Determinism tests for governed V2.2 promotion ledger provenance."""

from __future__ import annotations

from pathlib import Path

from scripts.governed_v22_promotion_gate import _ledger_fingerprint


def test_ledger_fingerprint_is_stable_across_file_creation_order(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    (first / "b.json").write_text('{"value": 2}\n', encoding="utf-8")
    (first / "a.json").write_text('{"value": 1}\n', encoding="utf-8")

    (second / "a.json").write_text('{"value": 1}\n', encoding="utf-8")
    (second / "b.json").write_text('{"value": 2}\n', encoding="utf-8")

    first_fingerprint = _ledger_fingerprint(first)
    second_fingerprint = _ledger_fingerprint(second)

    assert first_fingerprint["file_count"] == 2
    assert second_fingerprint["file_count"] == 2
    assert first_fingerprint["sha256"] == second_fingerprint["sha256"]


def test_ledger_fingerprint_changes_when_content_changes(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger"
    ledger.mkdir()
    record = ledger / "prediction.json"
    record.write_text('{"score": "2-1"}\n', encoding="utf-8")

    before = _ledger_fingerprint(ledger)
    record.write_text('{"score": "1-1"}\n', encoding="utf-8")
    after = _ledger_fingerprint(ledger)

    assert before["file_count"] == after["file_count"] == 1
    assert before["sha256"] != after["sha256"]


def test_ledger_fingerprint_changes_when_relative_path_changes(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    (first / "prediction.json").write_text("same-content\n", encoding="utf-8")
    nested = second / "archive"
    nested.mkdir()
    (nested / "prediction.json").write_text("same-content\n", encoding="utf-8")

    first_fingerprint = _ledger_fingerprint(first)
    second_fingerprint = _ledger_fingerprint(second)

    assert first_fingerprint["sha256"] != second_fingerprint["sha256"]
