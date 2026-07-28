from __future__ importannotations

from datetime import datetime, timezone
from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class MarketGovernanceEngine:
    provider_id: str = "market.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        market = match_context.get("market_odds", {})
        # market odds assumed dict {"home": float, "draw": float, "away": float}
        # convert to implied probabilities
        probs = {}
        total_inv = 0.0
        for k, odd in market.items():
            if odd and odd > 0:
                total_inv += 1.0 / odd
        for k, odd in market.items():
            probs[k] = (1.0 / odd) / total_inv if odd and odd > 0 else 0.0
        # market strength based on liquidity or number of sources
        market_volume = float(match_context.get("market_volume", 1.0))
        market_strength = min(1.0, market_volume / 100000.0)
        # market variance approximate by odds spread
        odds = [o for o in market.values() if o]
        if odds:
            spread = max(odds) - min(odds)
            market_variance = min(0.5, spread / max(1.0, sum(odds) / len(odds)))
        else:
            market_variance = 0.2
        # double counting flag if multiple market sources exist and correlation high
        market_sources = match_context.get("market_sources", [])
        market_double = len(market_sources) > 1
        half_life = 5 * 60

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "market:composite"),
            timestamp=timestamp,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("market_strength", "market_bias", "market_variance"),
            suggestion={
                "market_strength": market_strength,
                "market_bias": 0.0,
                "market_variance": market_variance,
            },
            variance={"market_strength": 0.01, "market_bias": 0.02, "market_variance": market_variance},
            reliability=0.9,
            weight=1.0,
            direction={"market_strength": market_strength - 0.5, "market_bias": 0.0, "market_variance": market_variance},
            confidence=0.9,
            metadata={"implied_probs": probs, "market_sources": market_sources, "market_double": market_double},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector={"homeaway.v1": 0.4},
        )
        return [evidence]
