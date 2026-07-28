from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class ScenarioProbabilityEngine:
    provider_id: str = "scenario.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        scenarios = match_context.get("scenarios", {"normal": 1.0})
        # normalize
        total = sum(float(v) for v in scenarios.values()) if scenarios else 1.0
        weights = {k: float(v) / max(1e-12, total) for k, v in scenarios.items()}
        # scenario dispersion via entropy
        import math

        entropy = -sum(w * math.log(w) for w in weights.values() if w > 0)
        half_life = 12 * 3600

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:scenario"),
            timestamp=timestamp,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("scenario_weights", "scenario_probability"),
            suggestion={"scenario_probability": 1.0},
            variance={"scenario_probability": 0.01, "scenario_weights": entropy},
            reliability=0.8,
            weight=1.0,
            direction={"scenario_probability": 0.0},
            confidence=0.8,
            metadata={"weights": weights},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
        )
        return [evidence]
