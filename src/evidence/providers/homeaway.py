from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class HomeAwayRegimeEngine:
    provider_id: str = "homeaway.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        # Base prior shift (goals per 90)
        home_prior = float(match_context.get("home_advantage_prior", 0.15))
        # historical sample size
        n_hist = int(match_context.get("homeaway_hist_n", 30))
        # variance decreases with sample size
        var = max(0.01, 0.2 / max(1, n_hist))
        reliability = min(1.0, 0.2 + 0.8 * min(1.0, n_hist / 100.0))
        half_life = 90 * 24 * 3600  # 90 days

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:homeaway"),
            timestamp=timestamp,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("lambda_home", "lambda_away"),
            suggestion={"lambda_home": home_prior, "lambda_away": -home_prior * 0.8},
            variance={"lambda_home": var, "lambda_away": var * 1.5},
            reliability=reliability,
            weight=1.0,
            direction={"lambda_home": 1.0, "lambda_away": -1.0},
            confidence=reliability,
            metadata={"n_hist": n_hist},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector=None,
        )
        return [evidence]
