"""Fixture-backed reference adapter for PRISM collection tests and examples."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from src.collection.models import SourceEnvelope
from src.intelligence.models import IntelligenceCategory, MatchTarget, Observation


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _parse_datetime(value: Any, field_name: str) -> datetime:
    text = _require_text(value, field_name)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _optional_confidence(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be numeric")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError("confidence must be finite and between 0 and 1")
    return result


@dataclass(frozen=True)
class FixtureObservationAdapter:
    """Translate a simple fixture payload into existing Observation objects."""

    adapter_id: str = "fixture_observations"

    def adapt(
        self,
        target: MatchTarget,
        envelope: SourceEnvelope,
    ) -> tuple[Observation, ...]:
        del target
        if envelope.adapter_id != self.adapter_id:
            raise ValueError("SourceEnvelope adapter_id does not match fixture adapter")

        rows = envelope.payload.get("observations")
        if not isinstance(rows, (list, tuple)):
            raise ValueError("Fixture payload observations must be a list")

        observations: list[Observation] = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError("Fixture observation rows must be mappings")
            observation_id = _require_text(row.get("observation_id"), "observation_id")
            claim_key = _require_text(row.get("claim_key"), "claim_key")
            category_text = _require_text(row.get("category"), "category")
            observed_at = _parse_datetime(row.get("observed_at"), "observed_at")
            subject_value = row.get("subject")
            subject = None if subject_value is None else _require_text(subject_value, "subject")
            confidence = _optional_confidence(row.get("confidence"))
            if "value" not in row:
                raise ValueError("Fixture observation row must contain value")

            observations.append(
                Observation(
                    observation_id=observation_id,
                    category=IntelligenceCategory(category_text),
                    claim_key=claim_key,
                    value=row["value"],
                    source=envelope.source,
                    observed_at=observed_at,
                    collected_at=envelope.retrieved_at,
                    subject=subject,
                    confidence=confidence,
                )
            )
        return tuple(observations)
