from __future__ import annotations

from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class RotationDepthEngine:
    provider_id: str = "rotation.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        obs_time = match_context.get("observation_time")
        if not obs_time:
            raise ValueError("match_context must include 'observation_time' for deterministic provider output")
        expected = list(match_context.get("expected_players", []))
        confirmed = list(match_context.get("confirmed_players", []))
        replacements = [p for p in expected if p not in confirmed]
        n = len(expected) if expected else 1
        rcount = len(replacements)
        prop = rcount / n
        cup_priority = float(match_context.get("cup_priority", 0.5))
        import math

        logits = -2.0 + 5.0 * prop - 3.0 * cup_priority
        p_rot = 1.0 / (1.0 + math.exp(-logits))
        quality = dict(match_context.get("player_quality", {}))
        rq_list = []
        for r in replacements:
            q_sub = float(quality.get(r, 0.7))
            q_start = float(quality.get(r + "_starter", quality.get(r, 0.85)))
            ratio = q_sub / max(1e-6, q_start)
            rq = float(max(0.0, min(1.0, ratio)))
            rq_list.append(rq)
        rq_mean = float(sum(rq_list) / len(rq_list)) if rq_list else 1.0
        rq_var = float(sum((x - rq_mean) ** 2 for x in rq_list) / len(rq_list)) if rq_list else 0.0001

        lambda_adj = -0.5 * (1.0 - rq_mean) * prop
        confidence_adj = -0.2 * prop

        half_life = 6 * 3600

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:rotation"),
            timestamp=obs_time,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("rotation_probability", "replacement_quality", "rotation_impact"),
            suggestion={
                "rotation_probability": float(p_rot),
                "replacement_quality": float(rq_mean),
                "rotation_impact": float(lambda_adj),
            },
            variance={
                "rotation_probability": float(max(1e-4, p_rot * (1 - p_rot))),
                "replacement_quality": float(rq_var),
                "rotation_impact": 0.01,
            },
            reliability=0.7,
            weight=1.0,
            direction={"rotation_probability": float(p_rot - 0.1), "replacement_quality": float(rq_mean - 1.0), "rotation_impact": float(-abs(lambda_adj))},
            confidence=0.7,
            metadata={"replacements": replacements, "prop_replaced": prop, "cup_priority": cup_priority},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector={"personnel.v1": 0.9, "priority.v1": 0.6},
            units={"rotation_probability": "probability", "replacement_quality": "probability", "rotation_impact": "expected_goals"},
            ranges={"rotation_probability": (0.0, 1.0), "replacement_quality": (0.0, 1.0), "rotation_impact": (-2.0, 2.0)},
        )
        return [evidence]
