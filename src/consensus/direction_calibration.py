"""Candidate direction-first calibration for PRISM Exact Score V2.2."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from src.domain.models import ConsensusOutput, EvidenceOutput


@dataclass(frozen=True)
class DirectionCalibrationOutput:
    """Auditable calibrated result-family distribution."""

    home_probability: float
    draw_probability: float
    away_probability: float
    reliability: float
    raw_leading_probability: float
    calibrated_leading_probability: float
    method: str = "evidence_agreement_uniform_shrinkage_v1"

    def __post_init__(self) -> None:
        probabilities = (
            self.home_probability,
            self.draw_probability,
            self.away_probability,
        )
        if any(value < 0.0 or value > 1.0 for value in probabilities):
            raise ValueError("calibrated probabilities must be within [0, 1]")
        if abs(sum(probabilities) - 1.0) > 1e-9:
            raise ValueError("calibrated probabilities must sum to 1")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be within [0, 1]")


class DirectionCalibrator:
    """Conservatively shrink raw consensus when evidence support is weak."""

    name = "direction-calibration"
    version = "2.2.0-candidate1"

    def run(
        self,
        consensus: ConsensusOutput,
        evidence: EvidenceOutput,
    ) -> DirectionCalibrationOutput:
        evidence_strength = evidence.score / 100.0
        reliability = sqrt(consensus.agreement * evidence_strength)
        uniform = 1.0 / 3.0
        raw = (
            consensus.home_probability,
            consensus.draw_probability,
            consensus.away_probability,
        )
        calibrated = tuple(
            reliability * probability + (1.0 - reliability) * uniform for probability in raw
        )
        raw_leading = max(raw)
        calibrated_leading = max(calibrated)
        return DirectionCalibrationOutput(
            home_probability=calibrated[0],
            draw_probability=calibrated[1],
            away_probability=calibrated[2],
            reliability=reliability,
            raw_leading_probability=raw_leading,
            calibrated_leading_probability=calibrated_leading,
        )
