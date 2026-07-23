"""Shared rule definition for PRISM rule packs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from src.domain.models import MatchContext

RuleOutput = Mapping[str, object]
Predicate = Callable[[MatchContext], bool]
Rationale = Callable[[MatchContext], str]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    version: str
    severity: str
    effects: tuple[str, ...]
    predicate: Predicate
    rationale: Rationale

    def evaluate(self, context: MatchContext) -> RuleOutput | None:
        if not self.predicate(context):
            return None
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "severity": self.severity,
            "rationale": self.rationale(context),
            "effects": self.effects,
        }
