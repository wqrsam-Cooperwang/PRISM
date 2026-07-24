"""Public API for PRISM automated match intelligence."""

from src.intelligence.models import (
    INTELLIGENCE_SCHEMA_VERSION,
    CategoryAssessment,
    IntelligenceBundle,
    IntelligenceCategory,
    IntelligenceReadiness,
    MatchTarget,
    Observation,
    ReadinessLevel,
    SourceRef,
    SourceType,
    VerificationStatus,
    VerifiedClaim,
)
from src.intelligence.pipeline import build_intelligence_bundle, verify_observations

__all__ = [
    "INTELLIGENCE_SCHEMA_VERSION",
    "CategoryAssessment",
    "IntelligenceBundle",
    "IntelligenceCategory",
    "IntelligenceReadiness",
    "MatchTarget",
    "Observation",
    "ReadinessLevel",
    "SourceRef",
    "SourceType",
    "VerificationStatus",
    "VerifiedClaim",
    "build_intelligence_bundle",
    "verify_observations",
]
