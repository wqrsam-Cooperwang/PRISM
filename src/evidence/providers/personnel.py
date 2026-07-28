from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from src.evidence.models import EvidenceResult


@dataclass
class PersonnelReliabilityEngine:
    provider_id: str = "personnel.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        """Produce EvidenceResult(s) about personnel reliability and replacement quality.

        Required match_context fields for deterministic output:
        - observation_time: ISO8601 timestamp string (e.g., '2026-07-28T14:00:00Z')
        - confirmed_players: list
        - expected_players: list
        - player_quality: dict
        """
        obs_time = match_context.get("observation_time")
        if not obs_time:
            raise ValueError("match_context must include 'observation_time' for deterministic provider output")

        confirmed = list(match_context.get("confirmed_players", []))
        expected = list(match_context.get("expected_players", []))
        quality = dict(match_context.get("player_quality", {}))

        # Determine replacements
        replacements = [p for p in expected if p not in confirmed]
        rq_list: list[float] = []
        for r in replacements:
            q_sub = float(quality.get(r, 0.7))
            q_start = float(quality.get(r + "_starter", quality.get(r, 0.85)))
            ratio = q_sub / max(1e-6, q_start)
            rq = (1.0 / (1.0 + 2.0 * max(0.0, 1.0 - ratio))) if ratio < 1 else min(1.0, 1.0 + 0.1 * (ratio - 1.0))
            rq = float(max(0.0, min(1.0, rq)))
            rq_list.append(rq)

        if rq_list:
            rq_mean = sum(rq_list) / len(rq_list)
            rq_var = sum((x - rq_mean) ** 2 for x in rq_list) / len(rq_list)
        else:
            rq_mean = 1.0
            rq_var = 0.0001

        confirmed_fraction = (len(confirmed) / max(1, len(expected))) if expected else 1.0
        reliability = float(max(0.0, min(1.0, 0.5 + 0.5 * confirmed_fraction)))

        half_life = 30 * 60

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:personnel"),
            timestamp=obs_time,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("replacement_quality", "personnel_reliability"),
            suggestion={
                "replacement_quality": float(rq_mean),
                "personnel_reliability": float(reliability),
            },
            variance={"replacement_quality": float(rq_var), "personnel_reliability": 0.01},
            reliability=float(reliability),
            weight=1.0,
            direction={"replacement_quality": float(rq_mean - 1.0), "personnel_reliability": float(reliability - 0.5)},
            confidence=float(reliability),
            metadata={"replacements": replacements, "confirmed_fraction": confirmed_fraction},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
            units={"replacement_quality": "probability", "personnel_reliability": "probability"},
            ranges={"replacement_quality": (0.0, 1.0), "personnel_reliability": (0.0, 1.0)},
        )

        return [evidence]
