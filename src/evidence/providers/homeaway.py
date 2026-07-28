from __future__ import annotations

from datetime import timezone
from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class HomeAwayRegimeEngine:
    provider_id: str = "homeaway.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        obs_time = match_context.get("observation_time")
        if not obs_time:
            raise ValueError("match_context must include 'observation_time' for deterministic provider output")
        # Base prior shift (goals per 90)
        home_prior = float(match_context.get("home_advantage_prior", 0.15))
        n_hist = int(match_context.get("homeaway_hist_n", 30))
        var = max(0.01, 0.2 / max(1, n_hist))
        reliability = min(1.0, 0.2 + 0.8 * min(1.0, n_hist / 100.0))
        half_life = 90 * 24 * 3600

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:homeaway"),
            timestamp=obs_time,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("lambda_home", "lambda_away"),
            suggestion={"lambda_home": float(home_prior), "lambda_away": float(-home_prior * 0.8)},
            variance={"lambda_home": float(var), "lambda_away": float(var * 1.5)},
            reliability=float(reliability),
            weight=1.0,
            direction={"lambda_home": 1.0, "lambda_away": -1.0},
            confidence=float(reliability),
            metadata={"n_hist": n_hist},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
            units={"lambda_home": "expected_goals", "lambda_away": "expected_goals"},
            ranges={"lambda_home": (-2.0, 2.0), "lambda_away": (-2.0, 2.0)},
        )
        return [evidence]
