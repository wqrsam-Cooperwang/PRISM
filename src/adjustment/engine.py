"""Adjustment Engine for governed PRISM rule effects."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping

from src.domain.models import AdjustmentOutput, MatchContext

_RESTRICTION_CAPS = {
    "block_active_decision": 0.34,
    "restrict_active_decision": 0.49,
    "restrict_high_confidence_action": 0.69,
}


class AdjustmentEngine:
    """Apply governed confidence ceilings without mutating upstream outputs."""

    name = "adjustment"
    version = "1.0.0"

    def run(self, context: MatchContext) -> MatchContext:
        if context.confidence is None:
            raise ValueError("Adjustment Engine requires confidence output")

        observed_effects = _collect_effects(context.rule_outputs)
        applied_effects = tuple(
            effect for effect in observed_effects if effect in _RESTRICTION_CAPS
        )
        confidence_cap = _strictest_cap(applied_effects)
        base_confidence = context.confidence.overall
        adjusted_confidence = (
            base_confidence
            if confidence_cap is None
            else min(base_confidence, confidence_cap)
        )
        decision_blocked = "block_active_decision" in applied_effects

        rationale = [f"base_confidence={base_confidence:.4f}"]
        if confidence_cap is None:
            rationale.append("confidence_cap=none")
        else:
            rationale.append(f"confidence_cap={confidence_cap:.2f}")
        rationale.append(f"adjusted_confidence={adjusted_confidence:.4f}")

        output = AdjustmentOutput(
            base_confidence=base_confidence,
            adjusted_confidence=round(adjusted_confidence, 4),
            confidence_cap=confidence_cap,
            decision_blocked=decision_blocked,
            applied_effects=applied_effects,
            observed_effects=observed_effects,
            rationale=tuple(rationale),
        )
        return replace(context, adjustment=output)


def _collect_effects(rule_outputs: Iterable[Mapping[str, object]]) -> tuple[str, ...]:
    seen: set[str] = set()
    effects: list[str] = []
    for output in rule_outputs:
        raw_effects = output.get("effective_effects", ())
        if not isinstance(raw_effects, tuple):
            continue
        for effect in raw_effects:
            if isinstance(effect, str) and effect not in seen:
                effects.append(effect)
                seen.add(effect)
    return tuple(effects)


def _strictest_cap(effects: tuple[str, ...]) -> float | None:
    caps = [_RESTRICTION_CAPS[effect] for effect in effects if effect in _RESTRICTION_CAPS]
    return min(caps) if caps else None
