"""PRISM Evidence Engine MVP.

This module evaluates evidence completeness only. It does not predict match
outcomes or make betting decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping

CATEGORY_WEIGHTS: Mapping[str, int] = MappingProxyType(
    {
        "lineup": 20,
        "injuries": 10,
        "odds": 15,
        "weather": 10,
        "tactical_data": 15,
        "historical_data": 15,
        "market_data": 10,
        "motivation": 5,
    }
)

_GATE_RANK = {"rejected": 0, "limited": 1, "standard": 2, "deep": 3}


@dataclass(frozen=True)
class EvidenceResult:
    """Immutable audit result returned by the Evidence Engine."""

    score: int
    raw_score: float
    gate: str
    category_scores: Mapping[str, float]
    missing_categories: tuple[str, ...]
    warnings: tuple[str, ...]
    critical_caps_applied: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return {
            "score": self.score,
            "raw_score": self.raw_score,
            "gate": self.gate,
            "category_scores": dict(self.category_scores),
            "missing_categories": list(self.missing_categories),
            "warnings": list(self.warnings),
            "critical_caps_applied": list(self.critical_caps_applied),
        }


def _validate_payload(payload: Mapping[str, float]) -> dict[str, float]:
    unknown = sorted(set(payload) - set(CATEGORY_WEIGHTS))
    if unknown:
        raise ValueError(f"Unknown evidence categories: {', '.join(unknown)}")

    validated: dict[str, float] = {}
    for category, value in payload.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{category} must be a numeric value from 0.0 to 1.0")

        numeric_value = float(value)
        if not isfinite(numeric_value):
            raise ValueError(f"{category} must be finite")
        if not 0.0 <= numeric_value <= 1.0:
            raise ValueError(f"{category} must be between 0.0 and 1.0")

        validated[category] = numeric_value

    return validated


def _gate_from_score(score: int) -> str:
    if score >= 85:
        return "deep"
    if score >= 70:
        return "standard"
    if score >= 45:
        return "limited"
    return "rejected"


def _cap_gate(current_gate: str, maximum_gate: str) -> str:
    if _GATE_RANK[current_gate] <= _GATE_RANK[maximum_gate]:
        return current_gate
    return maximum_gate


def evaluate_evidence(payload: Mapping[str, float]) -> EvidenceResult:
    """Validate and score one evidence-completeness payload.

    Args:
        payload: Mapping of supported evidence category names to completeness
            values from 0.0 to 1.0.

    Returns:
        EvidenceResult with category scoring, warnings, and quality gate.

    Raises:
        TypeError: If payload is not a mapping.
        ValueError: If categories or values are invalid.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("Evidence payload must be a mapping")

    validated = _validate_payload(payload)
    normalized = {category: validated.get(category, 0.0) for category in CATEGORY_WEIGHTS}

    category_scores = {
        category: round(normalized[category] * weight, 4)
        for category, weight in CATEGORY_WEIGHTS.items()
    }
    raw_score = round(sum(category_scores.values()), 4)
    score = int(raw_score + 0.5)
    gate = _gate_from_score(score)

    missing = tuple(
        category for category, completeness in normalized.items() if completeness == 0
    )
    warnings: list[str] = []
    caps: list[str] = []

    if missing:
        warnings.append(f"Missing or zero-completeness categories: {', '.join(missing)}")

    if normalized["lineup"] < 0.25:
        capped = _cap_gate(gate, "limited")
        if capped != gate:
            gate = capped
            caps.append("lineup_below_0.25")
        warnings.append("Lineup evidence is critically incomplete")

    if normalized["odds"] == 0:
        capped = _cap_gate(gate, "limited")
        if capped != gate:
            gate = capped
            caps.append("odds_missing")
        warnings.append("Odds evidence is missing")

    if normalized["lineup"] == 0 and normalized["injuries"] == 0:
        if gate != "rejected":
            caps.append("lineup_and_injuries_missing")
        gate = "rejected"
        warnings.append("Lineup and injury evidence are both missing")

    if len(missing) >= 3:
        capped = _cap_gate(gate, "limited")
        if capped != gate:
            gate = capped
            caps.append("three_or_more_categories_missing")
        warnings.append("Three or more evidence categories are missing")

    return EvidenceResult(
        score=score,
        raw_score=raw_score,
        gate=gate,
        category_scores=MappingProxyType(category_scores),
        missing_categories=missing,
        warnings=tuple(warnings),
        critical_caps_applied=tuple(caps),
    )
