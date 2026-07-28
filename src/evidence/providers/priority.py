from __future__ import annotations

from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class PriorityEngine:
    provider_id: str = "priority.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        obs_time = match_context.get("observation_time")
        if not obs_time:
            raise ValueError("match_context must include 'observation_time' for deterministic provider output")
        is_knockout = bool(match_context.get("is_knockout", False))
        days_to_next = float(match_context.get("days_to_next", 7.0))
        travel_km = float(match_context.get("travel_distance_km", 100.0))
        squad_depth = float(match_context.get("squad_depth", 1.0))
        opponent_strength = float(match_context.get("opponent_strength", 0.5))

        import math

        score_raw = (1.5 * float(is_knockout)) + 0.8 * (1.0 - min(1.0, days_to_next / 7.0)) - 0.0005 * travel_km + 0.5 * (1.0 - squad_depth) + 0.3 * opponent_strength
        cup_priority = 1.0 / (1.0 + math.exp(-score_raw))
        fixture_raw = 1.2 * (1.0 - min(1.0, days_to_next / 4.0)) + 0.2 * opponent_strength
        fixture_priority = 1.0 / (1.0 + math.exp(-fixture_raw))

        p_rot = 1.0 / (1.0 + math.exp(3.0 * cup_priority + 2.0 * fixture_priority - 2.0 * (1.0 - squad_depth)))

        half_life = 24 * 3600

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:priority"),
            timestamp=obs_time,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("cup_priority", "fixture_priority", "rotation_probability"),
            suggestion={"cup_priority": float(cup_priority), "fixture_priority": float(fixture_priority), "rotation_probability": float(p_rot)},
            variance={"cup_priority": 0.02, "fixture_priority": 0.03, "rotation_probability": float(p_rot * (1 - p_rot))},
            reliability=0.75,
            weight=1.0,
            direction={"cup_priority": float(cup_priority - 0.5), "fixture_priority": float(fixture_priority - 0.5), "rotation_probability": float(p_rot - 0.1)},
            confidence=0.75,
            metadata={"is_knockout": is_knockout, "days_to_next": days_to_next},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
            units={"cup_priority": "probability", "fixture_priority": "probability", "rotation_probability": "probability"},
            ranges={"cup_priority": (0.0, 1.0), "fixture_priority": (0.0, 1.0), "rotation_probability": (0.0, 1.0)},
        )
        return [evidence]
