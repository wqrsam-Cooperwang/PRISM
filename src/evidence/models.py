from __future__ import annotations

"""Evidence models and contracts for PRISM Enterprise V3.4.

This file freezes the EvidenceResult contract per the Architecture Freeze.
No implementation logic beyond basic validation is included here.
"""

from dataclasses import dataclass
from typing import Mapping, Any, Tuple


@dataclass(frozen=True)
class EvidenceResult:
    """Immutable evidence object produced by an evidence provider.

    Fields are strictly frozen by the Architecture Freeze. No field names or
    types may change without a new architectural freeze.
    """

    provider_id: str
    source: str
    timestamp: str  # ISO 8601 datetime with timezone (e.g., 2026-07-28T14:00:00Z)
    evidence_id: str
    targets: tuple[str, ...]
    suggestion: Mapping[str, float]
    variance: Mapping[str, float]
    reliability: float  # 0..1
    weight: float
    direction: Mapping[str, float]
    confidence: float  # 0..1
    metadata: Mapping[str, Any]

    # Amendment 2: aging
    freshness: float | None = None  # seconds since observation (optional)
    half_life: float | None = None  # seconds
    decay_function: str | None = None  # 'exponential'|'linear'|'custom'

    # Amendment 1: dependencies
    dependency_vector: Mapping[str, float] | None = None  # provider_id -> strength [0,1]

    # Amendment 3: explicit units and ranges per target
    units: Mapping[str, str] | None = None  # e.g., {"rotation_probability": "probability"}
    ranges: Mapping[str, Tuple[float, float]] | None = None  # e.g., {"rotation_probability": (0.0,1.0)}

    def __post_init__(self) -> None:
        # Basic validations (kept minimal so providers can construct easily)
        if not self.provider_id:
            raise ValueError("provider_id must not be blank")
        if not self.source:
            raise ValueError("source must not be blank")
        if not self.evidence_id:
            raise ValueError("evidence_id must not be blank")
        if not self.targets:
            raise ValueError("targets must include at least one latent name")
        if not (0.0 <= self.reliability <= 1.0):
            raise ValueError("reliability must be within [0,1]")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be within [0,1]")
        if self.weight < 0:
            raise ValueError("weight must be non-negative")
        for k in self.targets:
            if k not in self.suggestion:
                raise ValueError(f"missing suggestion for target: {k}")
            if k not in self.variance:
                raise ValueError(f"missing variance for target: {k}")
            if k not in self.direction:
                raise ValueError(f"missing direction for target: {k}")
        # variance positivity
        for v in self.variance.values():
            if v < 0 or not float(v) == v:
                raise ValueError("variance values must be non-negative floats")
        # units and ranges consistency
        if self.units is None:
            raise ValueError("units mapping is required for EvidenceResult to avoid ambiguity")
        for k in self.targets:
            if k not in self.units:
                raise ValueError(f"missing unit for target: {k}")
        if self.ranges:
            for k, r in self.ranges.items():
                if r[0] > r[1]:
                    raise ValueError(f"invalid range for {k}")
                # if suggestion present, validate within range
                if k in self.suggestion:
                    s = float(self.suggestion[k])
                    if not (r[0] - 1e-12 <= s <= r[1] + 1e-12):
                        raise ValueError(f"suggestion for {k}={s} outside declared range {r}")
