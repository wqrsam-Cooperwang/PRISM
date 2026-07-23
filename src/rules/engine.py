"""Deterministic, auditable rule evaluation for PRISM."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable

from src.domain.models import ConfidenceBand, EvidenceGate, MatchContext
from src.rules.football import FOOTBALL_RULES
from src.rules.models import Rule, RuleOutput

_RULESET_VERSION = "1.2.0"
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
_SEVERITY_RANK = {"info": 1, "warning": 2, "critical": 3}
_DECISION_RESTRICTION_STRENGTH = {
    "restrict_high_confidence_action": 1,
    "restrict_active_decision": 2,
    "block_active_decision": 3,
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


CORE_RULES = (
    Rule(
        "RULE-E001",
        "1.0.0",
        "critical",
        ("block_active_decision", "require_more_evidence"),
        _rejected_evidence,
        lambda _: "Evidence gate is rejected; active decisions must be blocked.",
        priority=100,
    ),
    Rule(
        "RULE-E002",
        "1.0.0",
        "warning",
        ("restrict_high_confidence_action", "require_evidence_warning"),
        _limited_evidence,
        lambda _: "Evidence gate is limited; downstream action must remain conservative.",
        priority=75,
    ),
    Rule(
        "RULE-C001",
        "1.0.0",
        "warning",
        ("restrict_active_decision",),
        _low_confidence,
        lambda _: "Overall confidence is low; active decisions require restriction.",
        priority=85,
    ),
    Rule(
        "RULE-M001",
        "1.0.0",
        "warning",
        ("flag_model_disagreement", "require_uncertainty_rationale"),
        _model_disagreement,
        lambda _: "Model probability ranges show material disagreement.",
        priority=60,
    ),
    Rule(
        "RULE-S001",
        "1.0.0",
        "info",
        ("apply_schedule_caution",),
        _short_turnaround,
        lambda _: "At least one team has three or fewer explicit rest days.",
        priority=30,
    ),
)

DEFAULT_RULES = CORE_RULES + FOOTBALL_RULES


def _sort_key(rule: Rule) -> tuple[int, int, str]:
    return (-rule.priority, -_SEVERITY_RANK[rule.severity], rule.rule_id)


def _effects_from_output(output: RuleOutput) -> tuple[str, ...]:
    effects = output["effects"]
    if not isinstance(effects, tuple) or not all(isinstance(item, str) for item in effects):
        raise TypeError("Rule effects must be a tuple of strings")
    return effects


def _strongest_decision_restriction(outputs: Iterable[RuleOutput]) -> str | None:
    strongest: str | None = None
    strongest_strength = 0
    for output in outputs:
        for effect in _effects_from_output(output):
            strength = _DECISION_RESTRICTION_STRENGTH.get(effect, 0)
            if strength > strongest_strength:
                strongest = effect
                strongest_strength = strength
    return strongest


def _resolve_outputs(
    outputs: tuple[RuleOutput, ...], ruleset_version: str
) -> tuple[RuleOutput, ...]:
    strongest_restriction = _strongest_decision_restriction(outputs)
    seen_effects: set[str] = set()
    resolved: list[RuleOutput] = []

    for output in outputs:
        effective: list[str] = []
        suppressed: list[str] = []
        for effect in _effects_from_output(output):
            if effect in _DECISION_RESTRICTION_STRENGTH:
                if effect != strongest_restriction or effect in seen_effects:
                    suppressed.append(effect)
                    continue
            elif effect in seen_effects:
                suppressed.append(effect)
                continue
            effective.append(effect)
            seen_effects.add(effect)

        if effective and suppressed:
            status = "partially_suppressed"
        elif suppressed:
            status = "suppressed"
        else:
            status = "active"

        resolved.append(
            {
                **output,
                "ruleset_version": ruleset_version,
                "effective_effects": tuple(effective),
                "suppressed_effects": tuple(suppressed),
                "status": status,
            }
        )
    return tuple(resolved)


class RuleEngine:
    """Evaluate, order, and resolve registered PRISM rules."""

    name = "rules"
    version = "1.2.0"

    def __init__(
        self,
        rules: tuple[Rule, ...] = DEFAULT_RULES,
        ruleset_version: str = _RULESET_VERSION,
    ) -> None:
        identifiers = [rule.rule_id for rule in rules]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Rule registry contains duplicate rule ids")
        if _SEMVER_PATTERN.fullmatch(ruleset_version) is None:
            raise ValueError("ruleset_version must use MAJOR.MINOR.PATCH")
        self._rules = tuple(sorted(rules, key=_sort_key))
        self._ruleset_version = ruleset_version

    def run(self, context: MatchContext) -> MatchContext:
        outputs = tuple(
            output for rule in self._rules if (output := rule.evaluate(context)) is not None
        )
        return replace(
            context,
            rule_outputs=_resolve_outputs(outputs, self._ruleset_version),
        )
