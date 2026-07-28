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

        Expected keys in match_context:
        - confirmed_players: list of player ids
        - expected_players: list of player ids
        - player_quality: dict player_id -> float (quality score > 0)
        - source: optional source string
        """
        confirmed = list(match_context.get("confirmed_players", []))
        expected = list(match_context.get("expected_players", []))
        quality = dict(match_context.get("player_quality", {}))
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Determine replacements
        replacements = [p for p in expected if p not in confirmed]
        rq_list: list[float] = []
        for r in replacements:
            # approximate sub quality: look up in quality mapping; if not found assume baseline 0.7
            q_sub = quality.get(r, 0.7)
            # approximate starter quality if available by position (best available), try to map by name prefix
            # fallback: assume starter quality 0.85
            q_start = quality.get(r + "_starter", quality.get(r, 0.85))
            # replacement quality ratio in [0,1.5], normalize
            ratio = q_sub / max(1e-6, q_start)
            rq = (1.0 / (1.0 + 2.0 * max(0.0, 1.0 - ratio))) if ratio < 1 else min(1.0, 1.0 + 0.1 * (ratio - 1.0))
            rq = float(max(0.0, min(1.0, rq)))
            rq_list.append(rq)

        if rq_list:
            rq_mean = sum(rq_list) / len(rq_list)
            # variance approximate
            rq_var = sum((x - rq_mean) ** 2 for x in rq_list) / len(rq_list)
        else:
            rq_mean = 1.0
            rq_var = 0.0001

        # personnel reliability based on fraction of confirmed starters
        confirmed_fraction = (len(confirmed) / max(1, len(expected))) if expected else 1.0
        reliability = max(0.0, min(1.0, 0.5 + 0.5 * confirmed_fraction))

        # half-life: lineups are volatile; default 30 minutes
        half_life = 30 * 60

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:personnel"),
            timestamp=timestamp,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("replacement_quality", "personnel_reliability"),
            suggestion={
                "replacement_quality": rq_mean,
                "personnel_reliability": reliability,
            },
            variance={"replacement_quality": float(rq_var), "personnel_reliability": 0.01},
            reliability=reliability,
            weight=1.0,
            direction={"replacement_quality": rq_mean - 1.0, "personnel_reliability": reliability - 0.5},
            confidence=reliability,
            metadata={"replacements": replacements, "confirmed_fraction": confirmed_fraction},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
        )

        return [evidence]
