"""Outcome-only benchmark and error taxonomy for recovered PRISM predictions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean


def _parse_score(value: str) -> tuple[int, int]:
    normalized = value.strip().replace(":", "-")
    parts = normalized.split("-")
    if len(parts) != 2:
        raise ValueError(f"invalid exact score: {value}")
    try:
        home, away = (int(part.strip()) for part in parts)
    except ValueError as exc:
        raise ValueError(f"invalid exact score: {value}") from exc
    if home < 0 or away < 0:
        raise ValueError(f"invalid exact score: {value}")
    return home, away


def _result_family(score: tuple[int, int]) -> str:
    home, away = score
    if home > away:
        return "home"
    if home < away:
        return "away"
    return "draw"


@dataclass(frozen=True)
class LegacyOutcomeCase:
    """Recovered pre-match PRISM score candidates and a 90-minute outcome."""

    case_id: str
    predicted_scores: tuple[tuple[int, int], ...]
    actual_score: tuple[int, int]
    path_changing_event: bool = False


@dataclass(frozen=True)
class LegacyOutcomeMetrics:
    """Per-case outcome metrics."""

    case_id: str
    primary_exact_hit: bool
    any_exact_hit: bool
    primary_direction_hit: bool
    any_direction_hit: bool
    minimum_manhattan_distance: int
    clean_sheet_overconfidence: bool
    weak_side_tail_miss: bool
    total_goals_error: int
    same_result_story_cluster: bool
    path_changing_event: bool


@dataclass(frozen=True)
class LegacyOutcomeSummary:
    """Aggregate historical PRISM outcome-only benchmark."""

    case_count: int
    primary_exact_hits: int
    any_exact_hits: int
    primary_direction_hits: int
    any_direction_hits: int
    mean_minimum_distance: float
    clean_sheet_overconfidence_cases: int
    weak_side_tail_miss_cases: int
    same_result_story_cluster_cases: int
    path_changing_event_cases: int
    mean_absolute_total_goals_error: float


def load_legacy_outcome_cases(path: Path | str) -> tuple[LegacyOutcomeCase, ...]:
    """Load a frozen outcome benchmark dataset."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("scope") != "outcome_benchmark":
        raise ValueError("legacy outcome dataset must declare scope=outcome_benchmark")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("legacy outcome dataset requires a non-empty cases array")

    cases: list[LegacyOutcomeCase] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise ValueError("legacy outcome case must be an object")
        case_id = raw.get("case_id")
        predicted = raw.get("predicted_scores")
        actual = raw.get("actual_score")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("legacy outcome case_id must be non-blank text")
        if not isinstance(predicted, list) or not predicted:
            raise ValueError("legacy outcome predicted_scores must be non-empty")
        predicted_scores: list[str] = []
        for item in predicted:
            if not isinstance(item, str):
                raise ValueError("legacy outcome predicted_scores must contain text scores")
            predicted_scores.append(item)
        if not isinstance(actual, str):
            raise ValueError("legacy outcome actual_score must be text")
        cases.append(
            LegacyOutcomeCase(
                case_id=case_id.strip(),
                predicted_scores=tuple(_parse_score(item) for item in predicted_scores),
                actual_score=_parse_score(actual),
                path_changing_event=bool(raw.get("path_changing_event", False)),
            )
        )
    return tuple(cases)


def evaluate_legacy_outcome_case(case: LegacyOutcomeCase) -> LegacyOutcomeMetrics:
    """Evaluate one recovered prediction without inventing unavailable model inputs."""

    actual = case.actual_score
    primary = case.predicted_scores[0]
    distances = tuple(
        abs(predicted[0] - actual[0]) + abs(predicted[1] - actual[1])
        for predicted in case.predicted_scores
    )
    actual_family = _result_family(actual)
    predicted_families = tuple(_result_family(item) for item in case.predicted_scores)
    all_away_zero = all(item[1] == 0 for item in case.predicted_scores)
    all_home_zero = all(item[0] == 0 for item in case.predicted_scores)
    clean_sheet_overconfidence = (all_away_zero and actual[1] > 0) or (
        all_home_zero and actual[0] > 0
    )

    if actual_family == "home":
        weak_side_tail_miss = actual[1] > 0 and all(
            item[1] == 0 for item in case.predicted_scores
        )
    elif actual_family == "away":
        weak_side_tail_miss = actual[0] > 0 and all(
            item[0] == 0 for item in case.predicted_scores
        )
    else:
        weak_side_tail_miss = clean_sheet_overconfidence

    predicted_total = primary[0] + primary[1]
    actual_total = actual[0] + actual[1]
    same_story = len(set(predicted_families)) == 1 and len(predicted_families) > 1
    return LegacyOutcomeMetrics(
        case_id=case.case_id,
        primary_exact_hit=primary == actual,
        any_exact_hit=actual in case.predicted_scores,
        primary_direction_hit=_result_family(primary) == actual_family,
        any_direction_hit=actual_family in predicted_families,
        minimum_manhattan_distance=min(distances),
        clean_sheet_overconfidence=clean_sheet_overconfidence,
        weak_side_tail_miss=weak_side_tail_miss,
        total_goals_error=predicted_total - actual_total,
        same_result_story_cluster=same_story,
        path_changing_event=case.path_changing_event,
    )


def summarize_legacy_outcomes(
    cases: tuple[LegacyOutcomeCase, ...],
) -> tuple[LegacyOutcomeSummary, tuple[LegacyOutcomeMetrics, ...]]:
    """Aggregate recovered historical Exact Score performance and error families."""

    if not cases:
        raise ValueError("legacy outcome summary requires at least one case")
    metrics = tuple(evaluate_legacy_outcome_case(case) for case in cases)
    return (
        LegacyOutcomeSummary(
            case_count=len(metrics),
            primary_exact_hits=sum(item.primary_exact_hit for item in metrics),
            any_exact_hits=sum(item.any_exact_hit for item in metrics),
            primary_direction_hits=sum(item.primary_direction_hit for item in metrics),
            any_direction_hits=sum(item.any_direction_hit for item in metrics),
            mean_minimum_distance=mean(
                item.minimum_manhattan_distance for item in metrics
            ),
            clean_sheet_overconfidence_cases=sum(
                item.clean_sheet_overconfidence for item in metrics
            ),
            weak_side_tail_miss_cases=sum(item.weak_side_tail_miss for item in metrics),
            same_result_story_cluster_cases=sum(
                item.same_result_story_cluster for item in metrics
            ),
            path_changing_event_cases=sum(item.path_changing_event for item in metrics),
            mean_absolute_total_goals_error=mean(
                abs(item.total_goals_error) for item in metrics
            ),
        ),
        metrics,
    )
