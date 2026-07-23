"""Deterministic, auditable rule evaluation for PRISM."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Mapping

from src.domain.models import ConfidenceBand, EvidenceGate, MatchContext

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


def _rejected_evidence(context: MatchContext) -> bool:
    return context.evidence is not None and context.evidence.gate is EvidenceGate.REJECTED


def _limited_evidence(context: MatchContext) -> bool:
    return context.evidence is not None and context.evidence.gate is EvidenceGate.LIMITED


def _low_confidence(context: MatchContext) -> bool:
    return context.confidence is not None and context.confidence.band in {
        ConfidenceBand.VERY_LOW,
        ConfidenceBand.LOW,
    }


def _model_disagreement(context: MatchContext) -> bool:
    if len(context.model_outputs) < 2:
        return False
    dimensions = (
        [item.home_probability for item in context.model_outputs],
        [item.draw_probability for item in context.model_outputs],
        [item.away_probability for item in context.model_outputs],
    )
    return max(max(values) - min(values) for values in dimensions) >= 0.30


def _short_turnaround(context: MatchContext) -> bool:
    for key in ("home_rest_days", "away_rest_days"):
        value = context.schedule.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and value <= 3:
            return True
    return False


DEFAULT_RULES = (
    Rule(
        "RULE-E001",
        "1.0.0",
        "critical",
        ("block_active_decision", "require_more_evidence"),
        _rejected_evidence,
        lambda _: "Evidence gate is rejected; active decisions must be blocked.",
    ),
    Rule(
        "RULE-E002",
        "1.0.0",
        "warning",
        ("restrict_high_confidence_action", "require_evidence_warning"),
        _limited_evidence,
        lambda _: "Evidence gate is limited; downstream action must remain conservative.",
    ),
    Rule(
        "RULE-C001",
        "1.0.0",
        "warning",
        ("restrict_active_decision",),
        _low_confidence,
        lambda _: "Overall confidence is low; active decisions require restriction.",
    ),
    Rule(
        "RULE-M001",
        "1.0.0",
        "warning",
        ("flag_model_disagreement", "require_uncertainty_rationale"),
        _model_disagreement,
        lambda _: "Model probability ranges show material disagreement.",
    ),
    Rule(
        "RULE-S001",
        "1.0.0",
        "info",
        ("apply_schedule_caution",),
        _short_turnaround,
        lambda _: "At least one team has three or fewer explicit rest days.",
    ),
)


class RuleEngine:
    """Evaluate registered rules and attach activated outputs to MatchContext."""

    name = "rules"
    version = "1.0.0"

    def __init__(self, rules: tuple[Rule, ...] = DEFAULT_RULES) -> None:
        identifiers = [rule.rule_id for rule in rules]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Rule registry contains duplicate rule ids")
        self._rules = rules

    def run(self, context: MatchContext) -> MatchContext:
        outputs = tuple(
            output
            for rule in self._rules
            if (output := rule.evaluate(context)) is not None
        )
        return replace(context, rule_outputs=outputs)
