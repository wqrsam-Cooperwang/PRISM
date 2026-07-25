"""Translate collection readiness into existing governed decision effects."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from src.collection.readiness import CollectionGateDecision, CollectionReadinessGateResult
from src.domain.models import MatchContext

_GOVERNANCE_SOURCE = "collection_readiness_gate"

_DECISION_EFFECTS = {
    CollectionGateDecision.READY: (),
    CollectionGateDecision.DEGRADED: ("restrict_high_confidence_action",),
    CollectionGateDecision.REJECTED: ("block_active_decision",),
}


def collection_governance_effects(
    gate: CollectionReadinessGateResult,
) -> tuple[str, ...]:
    """Return the existing governed effects required by a collection gate result."""

    return _DECISION_EFFECTS[gate.decision]


def apply_collection_governance(
    context: MatchContext,
    gate: CollectionReadinessGateResult,
) -> MatchContext:
    """Inject one deterministic collection-governance rule record into a context."""

    existing = tuple(
        output
        for output in context.rule_outputs
        if output.get("governance_source") != _GOVERNANCE_SOURCE
    )
    effects = collection_governance_effects(gate)
    record: dict[str, Any] = {
        "governance_source": _GOVERNANCE_SOURCE,
        "collection_gate_decision": gate.decision.value,
        "effective_effects": effects,
        "reasons": gate.reasons,
    }
    return replace(context, rule_outputs=(*existing, record))
