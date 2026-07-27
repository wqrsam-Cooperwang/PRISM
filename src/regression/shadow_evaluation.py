"""Evaluate frozen V2.2 shadow scorelines only on the governed settled cohort."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, cast

from src.ledger import load_formal_forward_testing_cohort
from src.regression.governed_dataset import load_governed_ledger_regression_dataset


@dataclass(frozen=True)
class ShadowScorelineEvaluation:
    """Aggregate exact-score evidence for the frozen V2.2 shadow candidate."""

    case_count: int
    production_primary_hits: int
    production_dual_hits: int
    shadow_primary_hits: int
    shadow_dual_hits: int

    @property
    def shadow_dual_hit_delta(self) -> int:
        return self.shadow_dual_hits - self.production_dual_hits


def evaluate_governed_v22_shadow(
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
) -> ShadowScorelineEvaluation:
    """Compare frozen production and V2.2 shadow pairs on the same governed cases."""

    cases = load_governed_ledger_regression_dataset(prediction_root, outcome_root)
    snapshots = {
        item.prediction_id: item
        for item in load_formal_forward_testing_cohort(prediction_root)
    }
    outcomes = Path(outcome_root)

    production_primary_hits = 0
    production_dual_hits = 0
    shadow_primary_hits = 0
    shadow_dual_hits = 0

    for case in cases:
        snapshot = snapshots[case.case_id]
        actual = f"{case.actual_home_goals}-{case.actual_away_goals}"
        production = _scorelines(snapshot.payload.get("report"), "production")
        shadow_root = _mapping(
            snapshot.payload.get("shadow_predictions"),
            "shadow_predictions",
        )
        shadow = _mapping(shadow_root.get("v2_2"), "shadow_predictions.v2_2")
        if shadow.get("status") != "available":
            raise ValueError(f"V2.2 shadow must be available for governed case {case.case_id}")
        shadow_pair = _scorelines(shadow, "V2.2 shadow")

        production_primary_hits += production[0] == actual
        production_dual_hits += actual in production
        shadow_primary_hits += shadow_pair[0] == actual
        shadow_dual_hits += actual in shadow_pair

        # The governed loader skips missing outcomes; an outcome disappearing between
        # the two reads is therefore treated as an inconsistent evaluation snapshot.
        if not (outcomes / f"{snapshot.match_id}.json").exists():
            raise ValueError(f"outcome disappeared during shadow evaluation: {snapshot.match_id}")

    return ShadowScorelineEvaluation(
        case_count=len(cases),
        production_primary_hits=production_primary_hits,
        production_dual_hits=production_dual_hits,
        shadow_primary_hits=shadow_primary_hits,
        shadow_dual_hits=shadow_dual_hits,
    )


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a mapping")
    return value


def _scorelines(value: Any, label: str) -> tuple[str, str]:
    root = _mapping(value, label)
    scoreline = _mapping(root.get("scoreline"), f"{label}.scoreline")
    raw = scoreline.get("recommended_scorelines")
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError(f"{label} requires exactly two scorelines")
    first, second = raw
    if not isinstance(first, str) or not isinstance(second, str):
        raise ValueError(f"{label} scorelines must be strings")
    return cast(str, first), cast(str, second)
