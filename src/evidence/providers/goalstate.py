from __future__ importannotations

from datetime import datetime, timezone
from typing import Any, Mapping

from src.evidence.models import EvidenceResult


class GoalStateStrategyEngine:
    provider_id: str = "goalstate.v1"

    def produce_evidence(self, match_context: Mapping[str, Any]) -> list[EvidenceResult]:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        # Simple default tempo multipliers for key states
        states = ["0-0", "1-0", "0-1", "2-0", "2-1", "1-2", "0-2"]
        base = match_context.get("base_tempo", 1.0)
        team_style = match_context.get("team_style", "balanced")
        # Adjustments by style
        style_map = {
            "balanced": 1.0,
            "attacking": 1.1,
            "defensive": 0.9,
            "counter": 0.95,
        }
        style_factor = style_map.get(team_style, 1.0)
        tempo_curve = {s: base * style_factor * (1.0 + 0.05 * (int(s.split("-")[0]) - int(s.split("-")[1]))) for s in states}

        # draw_acceptance approximations
        draw_acceptance = {s: 0.5 - 0.1 * (int(s.split("-")[0]) - int(s.split("-")[1])) for s in states}
        # late attack risk higher when trailing
        late_attack = {s: max(0.0, 0.2 * (int(s.split("-")[1]) - int(s.split("-")[0]))) for s in states}

        half_life = 7 * 24 * 3600

        evidence = EvidenceResult(
            provider_id=self.provider_id,
            source=match_context.get("source", "internal:goalstate"),
            timestamp=timestamp,
            evidence_id=f"{self.provider_id}:{match_context.get('match_id','unknown')}",
            targets=("tempo_curve", "draw_acceptance", "late_attack_risk"),
            suggestion={"tempo_curve": 0.0, "draw_acceptance": 0.0, "late_attack_risk": 0.0},
            # For complex structures store in metadata; set small placeholder variances
            variance={"tempo_curve": 0.01, "draw_acceptance": 0.01, "late_attack_risk": 0.01},
            reliability=0.6,
            weight=1.0,
            direction={"tempo_curve": style_factor - 1.0, "draw_acceptance": 0.0, "late_attack_risk": 0.0},
            confidence=0.6,
            metadata={"tempo_curve": tempo_curve, "draw_acceptance": draw_acceptance, "late_attack_risk": late_attack},
            freshness=None,
            half_life=half_life,
            decay_function="exponential",
            dependency_vector={"rotation.v1": 0.4, "personnel.v1": 0.3},
        )
        return [evidence]
