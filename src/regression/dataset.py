"""Load frozen historical scoreline-only regression datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from src.domain.models import ModelOutput
from src.regression.scoreline import ScorelineRegressionCase


def _number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be numeric")
    return float(value)


def _non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return cast(int, value)


def load_scoreline_regression_dataset(path: Path | str) -> tuple[ScorelineRegressionCase, ...]:
    """Load scoreline-only cases without fabricating evidence or model weights."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("scope") != "scoreline_only":
        raise ValueError("regression dataset must declare scope=scoreline_only")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("regression dataset requires a non-empty cases array")

    cases: list[ScorelineRegressionCase] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError("regression dataset case must be an object")
        case_id = raw.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("regression dataset case_id must be non-blank text")
        home_xg = _number(raw.get("home_xg"), "home_xg")
        away_xg = _number(raw.get("away_xg"), "away_xg")
        if home_xg < 0.0 or away_xg < 0.0:
            raise ValueError("expected goals must be non-negative")

        # The neutral probability vector is a serialization wrapper only. The exact-score
        # regression consumes expected goals; it does not use these 1X2 probabilities.
        model = ModelOutput(
            model_id="legacy-aggregate-xg",
            model_version="scoreline-only",
            home_probability=1.0 / 3.0,
            draw_probability=1.0 / 3.0,
            away_probability=1.0 / 3.0,
            expected_home_goals=home_xg,
            expected_away_goals=away_xg,
            diagnostics={"assumption_family": "legacy_aggregate_xg"},
        )
        cases.append(
            ScorelineRegressionCase(
                case_id=case_id.strip(),
                models=(model,),
                actual_home_goals=_non_negative_int(
                    raw.get("actual_home_goals"), "actual_home_goals"
                ),
                actual_away_goals=_non_negative_int(
                    raw.get("actual_away_goals"), "actual_away_goals"
                ),
            )
        )
    return tuple(cases)
