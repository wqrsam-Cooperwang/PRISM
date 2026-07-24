"""Immutable feature-vector models for PRISM prediction models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType

from src.intelligence.models import ReadinessLevel

FEATURE_SCHEMA_VERSION = "1.0.0"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class FeatureVector:
    """Deterministic numeric inputs plus explicit missingness metadata."""

    values: Mapping[str, float]
    missing_features: tuple[str, ...]
    intelligence_fingerprint: str
    readiness: ReadinessLevel
    fingerprint: str
    schema_version: str = FEATURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        validated: dict[str, float] = {}
        for key, value in self.values.items():
            name = _require_text(key, "feature_name")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Feature {name} must be numeric")
            numeric = float(value)
            if not isfinite(numeric):
                raise ValueError(f"Feature {name} must be finite")
            validated[name] = numeric

        missing = tuple(sorted(_require_text(item, "missing_feature") for item in self.missing_features))
        if len(set(missing)) != len(missing):
            raise ValueError("missing_features must be unique")
        if set(validated).intersection(missing):
            raise ValueError("A feature cannot be both present and missing")

        object.__setattr__(self, "values", MappingProxyType(dict(sorted(validated.items()))))
        object.__setattr__(self, "missing_features", missing)
        object.__setattr__(
            self,
            "intelligence_fingerprint",
            _require_text(self.intelligence_fingerprint, "intelligence_fingerprint"),
        )
        object.__setattr__(self, "readiness", ReadinessLevel(self.readiness))
        object.__setattr__(self, "fingerprint", _require_text(self.fingerprint, "fingerprint"))
        object.__setattr__(
            self,
            "schema_version",
            _require_text(self.schema_version, "schema_version"),
        )
