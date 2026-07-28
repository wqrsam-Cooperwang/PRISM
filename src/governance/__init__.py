# Governance skeleton

"""Minimal governance module used during scaffolding.

This module provides governance validation stubs and an audit writer stub. The
full governance rules are implemented in Phase G.
"""

from dataclasses import dataclass
from typing import Mapping, Any


@dataclass(frozen=True)
class GovernanceDecision:
    evidence_id: str
    decision: str  # 'accept' | 'flag' | 'reject'
    reason: str
    action_required: bool


def validate_evidence_basic(payload: Mapping[str, Any]) -> GovernanceDecision:
    # Basic validation for scaffold; real rules implemented later
    eid = payload.get("evidence_id", "<unknown>")
    if not payload.get("provider_id"):
        return GovernanceDecision(evidence_id=eid, decision="reject", reason="missing provider_id", action_required=True)
    return GovernanceDecision(evidence_id=eid, decision="accept", reason="ok", action_required=False)
