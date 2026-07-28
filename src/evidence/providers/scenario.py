from __future__ import annotations

from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class ScenarioProbabilityEngine:
    provider_id: str = "scenario.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        obs_time = match_context.get("observation_time")
        if not obs_time:
            raise ValueError("match_context must include 'observation_time' for deterministic provider output")
        scenarios = dict(match_context.get("scenarios", {"normal": 1.0}))
        total = sum(float(v) for v in scenarios.values()) if scenarios else 1.0
        weights = {k: float(v) / max(1e-12, total) for k, v in scenarios.items()}
        import math

        entropy = -sum(w * math.log(w) for w in weights.values() if w > 0)
        half_life = 12 * 3600

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:scenario"),
            timestamp=obs_time,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("scenario_weights", "scenario_probability"),
            suggestion={"scenario_probability": 1.0},
            variance={"scenario_probability": 0.01, "scenario_weights": float(entropy)},
            reliability=0.8,
            weight=1.0,
            direction={"scenario_probability": 0.0},
            confidence=0.8,
            metadata={"weights": weights},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
            units={"scenario_weights": "unitless", "scenario_probability": "probability"},
            ranges={"scenario_probability": (0.0, 1.0)},
        )
        return [evidence]
