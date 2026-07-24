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
from src.intelligence.normalization import (
    NormalizedIntelligenceFacts,
    NormalizedMatchInput,
    normalize_intelligence_bundle,
    normalize_intelligence_facts,
)
from src.intelligence.pipeline import build_intelligence_bundle, verify_observations

__all__ = [
    "INTELLIGENCE_SCHEMA_VERSION",
    "CategoryAssessment",
    "IntelligenceBundle",
    "IntelligenceCategory",
    "IntelligenceReadiness",
    "MatchTarget",
    "NormalizedIntelligenceFacts",
    "NormalizedMatchInput",
    "Observation",
    "ReadinessLevel",
    "SourceRef",
    "SourceType",
    "VerificationStatus",
    "VerifiedClaim",
    "build_intelligence_bundle",
    "normalize_intelligence_bundle",
    "normalize_intelligence_facts",
    "verify_observations",
]
