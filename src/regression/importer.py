"""Convert frozen prediction and outcome ledgers into replayable regression cases."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.domain.models import ModelOutput
from src.ledger.models import PredictionLedgerSnapshot
from src.ledger.outcomes import MatchOutcome
from src.regression.scoreline import ScorelineRegressionCase


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def _optional_number(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    return _number(value, field_name)


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-blank text")
    return value.strip()


def _diagnostics(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("model diagnostics must be a mapping")
    return value


def _model_from_dict(value: Any) -> ModelOutput:
    if not isinstance(value, Mapping):
        raise ValueError("model_outputs entries must be mappings")
    return ModelOutput(
        model_id=_text(value.get("model_id"), "model_id"),
        model_version=_text(value.get("model_version"), "model_version"),
        home_probability=_number(value.get("home_probability"), "home_probability"),
        draw_probability=_number(value.get("draw_probability"), "draw_probability"),
        away_probability=_number(value.get("away_probability"), "away_probability"),
        expected_home_goals=_optional_number(
            value.get("expected_home_goals"), "expected_home_goals"
        ),
        expected_away_goals=_optional_number(
            value.get("expected_away_goals"), "expected_away_goals"
        ),
        diagnostics=_diagnostics(value.get("diagnostics")),
    )


def regression_case_from_ledgers(
    snapshot: PredictionLedgerSnapshot,
    outcome: MatchOutcome,
) -> ScorelineRegressionCase:
    """Create one replay case from a frozen pre-match snapshot and verified outcome."""

    if snapshot.match_id != outcome.match_id:
        raise ValueError("prediction snapshot and outcome match_id must agree")
    raw_models = snapshot.payload.get("model_outputs")
    if not isinstance(raw_models, list) or not raw_models:
        raise ValueError("prediction snapshot does not contain replayable model_outputs")
    models = tuple(_model_from_dict(item) for item in raw_models)
    return ScorelineRegressionCase(
        case_id=snapshot.prediction_id,
        models=models,
        actual_home_goals=outcome.home_goals,
        actual_away_goals=outcome.away_goals,
    )
