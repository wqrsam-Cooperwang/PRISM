"""Deterministic feature construction from normalized PRISM intelligence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from math import isfinite
from typing import Any

from src.features.models import FEATURE_SCHEMA_VERSION, FeatureVector
from src.intelligence.models import ReadinessLevel
from src.intelligence.normalization import NormalizedIntelligenceFacts, NormalizedMatchInput

_READINESS_SCORE = {
    ReadinessLevel.REJECTED: 0.0,
    ReadinessLevel.LIMITED: 1.0 / 3.0,
    ReadinessLevel.STANDARD: 2.0 / 3.0,
    ReadinessLevel.DEEP: 1.0,
}

_CORE_FEATURES = (
    "elo_difference",
    "recent_points_difference",
    "missing_starters_difference",
    "rest_days_difference",
    "market_home_implied_probability",
    "market_draw_implied_probability",
    "market_away_implied_probability",
    "market_overround",
    "temperature_c",
)


def _numeric(value: Any, feature_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{feature_name} must be a finite numeric value")
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{feature_name} must be a finite numeric value")
    return numeric


def _nested_numeric(
    data: Mapping[str, Mapping[str, Any]],
    category: str,
    subject: str,
    key: str,
    feature_name: str,
) -> float | None:
    category_data = data.get(category)
    if category_data is None:
        return None
    subject_data = category_data.get(subject)
    if subject_data is None:
        return None
    if not isinstance(subject_data, Mapping):
        raise ValueError(f"{category}.{subject} must be a mapping")
    if key not in subject_data:
        return None
    return _numeric(subject_data[key], feature_name)


def _difference(
    data: Mapping[str, Mapping[str, Any]],
    category: str,
    key: str,
    feature_name: str,
) -> float | None:
    home = _nested_numeric(data, category, "home", key, feature_name)
    away = _nested_numeric(data, category, "away", key, feature_name)
    if home is None or away is None:
        return None
    return home - away


def _market_features(
    data: Mapping[str, Mapping[str, Any]],
) -> dict[str, float] | None:
    market = data.get("market")
    if market is None:
        return None
    keys = (
        "home_decimal_odds",
        "draw_decimal_odds",
        "away_decimal_odds",
    )
    if any(key not in market for key in keys):
        return None
    odds = [_numeric(market[key], key) for key in keys]
    if any(value <= 1.0 for value in odds):
        raise ValueError("1X2 decimal odds must be greater than 1.0")
    raw = [1.0 / value for value in odds]
    total = sum(raw)
    if total <= 0.0:
        raise ValueError("1X2 implied probability total must be positive")
    return {
        "market_home_implied_probability": raw[0] / total,
        "market_draw_implied_probability": raw[1] / total,
        "market_away_implied_probability": raw[2] / total,
        "market_overround": total - 1.0,
    }


def _temperature(data: Mapping[str, Mapping[str, Any]]) -> float | None:
    weather = data.get("weather")
    if weather is None or "temperature_c" not in weather:
        return None
    return _numeric(weather["temperature_c"], "temperature_c")


def _fingerprint(
    values: Mapping[str, float],
    missing: tuple[str, ...],
    intelligence_fingerprint: str,
    readiness: ReadinessLevel,
) -> str:
    payload = {
        "schema_version": FEATURE_SCHEMA_VERSION,
        "values": dict(sorted(values.items())),
        "missing_features": list(sorted(missing)),
        "intelligence_fingerprint": intelligence_fingerprint,
        "readiness": readiness.value,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_feature_vector(
    normalized: NormalizedIntelligenceFacts | NormalizedMatchInput,
) -> FeatureVector:
    """Build deterministic numeric features without imputing missing facts."""

    data = normalized.model_feature_data
    values: dict[str, float] = {}
    missing: set[str] = set(_CORE_FEATURES)

    elo_difference = _difference(data, "team_strength", "elo_rating", "elo_difference")
    recent_points_difference = _difference(
        data,
        "recent_form",
        "points_last_5",
        "recent_points_difference",
    )
    missing_starters_difference = _difference(
        data,
        "availability",
        "missing_starters",
        "missing_starters_difference",
    )
    rest_days_difference = _difference(data, "schedule", "rest_days", "rest_days_difference")

    direct = {
        "elo_difference": elo_difference,
        "recent_points_difference": recent_points_difference,
        "missing_starters_difference": missing_starters_difference,
        "rest_days_difference": rest_days_difference,
        "temperature_c": _temperature(data),
    }
    for name, value in direct.items():
        if value is not None:
            values[name] = value
            missing.discard(name)

    market = _market_features(data)
    if market is not None:
        values.update(market)
        missing.difference_update(market)

    values["intelligence_readiness_score"] = _READINESS_SCORE[normalized.readiness]
    for key, value in normalized.evidence_completeness.items():
        values[f"evidence_{key}"] = _numeric(value, f"evidence_{key}")

    missing_tuple = tuple(sorted(missing))
    fingerprint = _fingerprint(
        values,
        missing_tuple,
        normalized.intelligence_fingerprint,
        normalized.readiness,
    )
    return FeatureVector(
        values=values,
        missing_features=missing_tuple,
        intelligence_fingerprint=normalized.intelligence_fingerprint,
        readiness=normalized.readiness,
        fingerprint=fingerprint,
    )
