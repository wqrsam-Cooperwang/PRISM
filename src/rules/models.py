"""Shared rule definition for PRISM rule packs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from src.domain.models import MatchContext

RuleOutput = dict[str, object]
Predicate = Callable[[MatchContext], bool]
Rationale = Callable[[MatchContext], str]

_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_VALID_SEVERITIES = {"info", "warning", "critical"}


@dataclass(frozen=True)
class Rule:
    rule_id: str
    version: str
    severity: str
    effects: tuple[str, ...]
    predicate: Predicate
    rationale: Rationale
    priority: int = 50

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id must be a non-empty string")
        if _SEMVER_PATTERN.fullmatch(self.version) is None:
            raise ValueError("rule version must use MAJOR.MINOR.PATCH")
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError("rule severity must be info, warning, or critical")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValueError("rule priority must be an integer")
        if not 0 <= self.priority <= 100:
            raise ValueError("rule priority must be between 0 and 100")
        object.__setattr__(self, "effects", tuple(self.effects))

    def evaluate(self, context: MatchContext) -> RuleOutput | None:
        if not self.predicate(context):
            return None
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "severity": self.severity,
            "priority": self.priority,
            "rationale": self.rationale(context),
            "effects": self.effects,
        }
