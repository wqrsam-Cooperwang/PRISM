"""Collection readiness and source coverage governance for PRISM."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.intelligence.models import (
    IntelligenceBundle,
    IntelligenceCategory,
    ReadinessLevel,
)


class CollectionGateDecision(str, Enum):
    """Governed collection-readiness outcome."""

    READY = "ready"
    DEGRADED = "degraded"
    REJECTED = "rejected"


_CORE_CATEGORIES = (
    IntelligenceCategory.TEAM_STRENGTH,
    IntelligenceCategory.RECENT_FORM,
    IntelligenceCategory.AVAILABILITY,
    IntelligenceCategory.SCHEDULE,
    IntelligenceCategory.MARKET,
)

_OPTIONAL_CATEGORIES = (
    IntelligenceCategory.LINEUP,
    IntelligenceCategory.WEATHER,
)


@dataclass(frozen=True)
class CollectionReadinessGateResult:
    """Deterministic coverage decision for one verified intelligence bundle."""

    decision: CollectionGateDecision
    covered_core_categories: tuple[IntelligenceCategory, ...]
    missing_core_categories: tuple[IntelligenceCategory, ...]
    covered_optional_categories: tuple[IntelligenceCategory, ...]
    source_ids: tuple[str, ...]
    source_types: tuple[str, ...]
    elo_baseline_available: bool
    market_baseline_available: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision", CollectionGateDecision(self.decision))
        object.__setattr__(
            self,
            "covered_core_categories",
            tuple(IntelligenceCategory(item) for item in self.covered_core_categories),
        )
        object.__setattr__(
            self,
            "missing_core_categories",
            tuple(IntelligenceCategory(item) for item in self.missing_core_categories),
        )
        object.__setattr__(
            self,
            "covered_optional_categories",
            tuple(IntelligenceCategory(item) for item in self.covered_optional_categories),
        )
        object.__setattr__(self, "source_ids", tuple(self.source_ids))
        object.__setattr__(self, "source_types", tuple(self.source_types))
        object.__setattr__(self, "reasons", tuple(self.reasons))


def _coverage(bundle: IntelligenceBundle) -> dict[IntelligenceCategory, bool]:
    return {assessment.category: assessment.covered for assessment in bundle.category_assessments}


def evaluate_collection_readiness(
    bundle: IntelligenceBundle,
) -> CollectionReadinessGateResult:
    """Evaluate whether verified collection output may enter baseline prediction."""

    coverage = _coverage(bundle)
    covered_core = tuple(category for category in _CORE_CATEGORIES if coverage.get(category, False))
    missing_core = tuple(category for category in _CORE_CATEGORIES if not coverage.get(category, False))
    covered_optional = tuple(
        category for category in _OPTIONAL_CATEGORIES if coverage.get(category, False)
    )

    source_ids = tuple(sorted({item.source.source_id for item in bundle.observations}))
    source_types = tuple(sorted({item.source.source_type.value for item in bundle.observations}))

    elo_available = coverage.get(IntelligenceCategory.TEAM_STRENGTH, False)
    market_available = coverage.get(IntelligenceCategory.MARKET, False)
    reasons: list[str] = []

    if bundle.readiness.level == ReadinessLevel.REJECTED:
        decision = CollectionGateDecision.REJECTED
        reasons.append("intelligence readiness is rejected")
    elif not (elo_available and market_available):
        decision = CollectionGateDecision.REJECTED
        if not elo_available:
            reasons.append("elo baseline inputs are unavailable")
        if not market_available:
            reasons.append("market baseline inputs are unavailable")
    elif not missing_core and bundle.readiness.level in {
        ReadinessLevel.STANDARD,
        ReadinessLevel.DEEP,
    }:
        decision = CollectionGateDecision.READY
    else:
        decision = CollectionGateDecision.DEGRADED
        if missing_core:
            reasons.append("one or more core intelligence categories are missing")
        if bundle.readiness.level == ReadinessLevel.LIMITED:
            reasons.append("intelligence readiness is limited")

    return CollectionReadinessGateResult(
        decision=decision,
        covered_core_categories=covered_core,
        missing_core_categories=missing_core,
        covered_optional_categories=covered_optional,
        source_ids=source_ids,
        source_types=source_types,
        elo_baseline_available=elo_available,
        market_baseline_available=market_available,
        reasons=tuple(reasons),
    )
