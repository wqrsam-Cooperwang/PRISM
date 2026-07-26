from datetime import datetime, timezone

import pytest

from src.ledger import FileSystemOutcomeLedgerStore, MatchOutcome, PredictionLedgerSnapshot
from src.regression import regression_case_from_ledgers

NOW = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def _snapshot(match_id: str = "match-1") -> PredictionLedgerSnapshot:
    return PredictionLedgerSnapshot(
        prediction_id="pred-1",
        match_id=match_id,
        frozen_at=NOW,
        payload={
            "model_outputs": [
                {
                    "model_id": "xg",
                    "model_version": "1.0.0",
                    "home_probability": 0.55,
                    "draw_probability": 0.25,
                    "away_probability": 0.20,
                    "expected_home_goals": 1.6,
                    "expected_away_goals": 0.8,
                    "diagnostics": {"assumption_family": "xg"},
                }
            ]
        },
    )


def test_outcome_store_is_append_only(tmp_path) -> None:
    outcome = MatchOutcome("match-1", 2, 1, NOW, source="official")
    store = FileSystemOutcomeLedgerStore(tmp_path)

    path = store.persist(outcome)

    assert path.exists()
    assert '"home_goals": 2' in path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        store.persist(outcome)


def test_outcome_validation_fails_closed() -> None:
    with pytest.raises(ValueError, match="match_id"):
        MatchOutcome(" ", 1, 0, NOW)
    with pytest.raises(ValueError, match="non-negative"):
        MatchOutcome("match-1", -1, 0, NOW)
    with pytest.raises(ValueError, match="timezone-aware"):
        MatchOutcome("match-1", 1, 0, datetime(2026, 7, 27, 12, 0))


def test_regression_case_imports_frozen_models_and_outcome() -> None:
    case = regression_case_from_ledgers(
        _snapshot(),
        MatchOutcome("match-1", 2, 1, NOW),
    )

    assert case.case_id == "pred-1"
    assert case.actual_home_goals == 2
    assert case.actual_away_goals == 1
    assert case.models[0].expected_home_goals == pytest.approx(1.6)
    assert case.models[0].diagnostics["assumption_family"] == "xg"


def test_regression_import_rejects_mismatch_and_legacy_snapshot() -> None:
    with pytest.raises(ValueError, match="match_id"):
        regression_case_from_ledgers(_snapshot(), MatchOutcome("other", 1, 1, NOW))

    legacy = PredictionLedgerSnapshot(
        prediction_id="legacy",
        match_id="match-1",
        frozen_at=NOW,
        payload={},
    )
    with pytest.raises(ValueError, match="model_outputs"):
        regression_case_from_ledgers(legacy, MatchOutcome("match-1", 1, 1, NOW))
