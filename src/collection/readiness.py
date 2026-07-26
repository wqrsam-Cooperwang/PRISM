"""Collection readiness and source coverage governance for PRISM."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.intelligence.models import (
    IntelligenceBundle,
    IntelligenceCategory,
    ReadinessLevel,
    VerificationStatus,
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

_USABLE_STATUSES = {
    VerificationStatus.VERIFIED,
    VerificationStatus.PROVISIONAL,
}

_MARKET_REQUIRED_KEYS = {
    "home_decimal_odds",
    "draw_decimal_odds",
    "away_decimal_odds",
}

_TEAM_STATISTICS_REQUIRED_KEYS = {
    "points_per_game",
    "goal_difference_per_game",
}


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
    team_statistics_baseline_available: bool = False

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


def _covered_categories(
    coverage: dict[IntelligenceCategory, bool],
    categories: tuple[IntelligenceCategory, ...],
) -> tuple[IntelligenceCategory, ...]:
    return tuple(category for category in categories if coverage.get(category, False))


def _missing_categories(
    coverage: dict[IntelligenceCategory, bool],
    categories: tuple[IntelligenceCategory, ...],
) -> tuple[IntelligenceCategory, ...]:
    return tuple(category for category in categories if not coverage.get(category, False))


def _team_side(bundle: IntelligenceBundle, subject: str | None) -> str | None:
    if subject is None:
        return None
    target = bundle.target
    if subject in {"home", target.home_team_id, target.home_team_name}:
        return "home"
    if subject in {"away", target.away_team_id, target.away_team_name}:
        return "away"
    return None


def _baseline_availability(bundle: IntelligenceBundle) -> tuple[bool, bool, bool]:
    usable = tuple(
        claim
        for claim in bundle.claims
        if claim.status in _USABLE_STATUSES and claim.value is not None
    )

    elo_sides = {
        side
        for claim in usable
        if claim.category == IntelligenceCategory.TEAM_STRENGTH
        and claim.claim_key == "elo_rating"
        and (side := _team_side(bundle, claim.subject)) is not None
    }
    team_statistics: dict[str, set[str]] = {"home": set(), "away": set()}
    for claim in usable:
        if claim.category != IntelligenceCategory.TEAM_STRENGTH:
            continue
        if claim.claim_key not in _TEAM_STATISTICS_REQUIRED_KEYS:
            continue
        side = _team_side(bundle, claim.subject)
        if side is not None:
            team_statistics[side].add(claim.claim_key)

    market_keys = {
        claim.claim_key for claim in usable if claim.category == IntelligenceCategory.MARKET
    }
    team_statistics_available = all(
        _TEAM_STATISTICS_REQUIRED_KEYS.issubset(team_statistics[side]) for side in ("home", "away")
    )
    return (
        elo_sides == {"home", "away"},
        team_statistics_available,
        _MARKET_REQUIRED_KEYS.issubset(market_keys),
    )


def evaluate_collection_readiness(
    bundle: IntelligenceBundle,
) -> CollectionReadinessGateResult:
    """Evaluate whether verified collection output may enter baseline prediction."""

    coverage = _coverage(bundle)
    covered_core = _covered_categories(coverage, _CORE_CATEGORIES)
    missing_core = _missing_categories(coverage, _CORE_CATEGORIES)
    covered_optional = _covered_categories(coverage, _OPTIONAL_CATEGORIES)

    source_ids = tuple(sorted({item.source.source_id for item in bundle.observations}))
    source_types = tuple(sorted({item.source.source_type.value for item in bundle.observations}))
    elo_available, team_statistics_available, market_available = _baseline_availability(bundle)
    strength_available = elo_available or team_statistics_available
    reasons: list[str] = []

    if bundle.readiness.level == ReadinessLevel.REJECTED:
        decision = CollectionGateDecision.REJECTED
        reasons.append("intelligence readiness is rejected")
    elif not (strength_available and market_available):
        decision = CollectionGateDecision.REJECTED
        if not strength_available:
            reasons.append("team strength baseline inputs are unavailable")
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
        team_statistics_baseline_available=team_statistics_available,
    )
