"""Governed 1X2 candidate decisions for PRISM."""

from __future__ import annotations

from dataclasses import replace
from math import isfinite

from src.domain.models import DecisionAction, DecisionOutput, MatchContext

_MARKETS = (
    ("home", "home_odds"),
    ("draw", "draw_odds"),
    ("away", "away_odds"),
)
_TOLERANCE = 1e-12


class DecisionEngine:
    """Convert upstream analytical state into a governed final action."""

    name = "decision"
    version = "1.0.0"

    def __init__(
        self,
        minimum_adjusted_confidence: float = 0.70,
        minimum_expected_value: float = 0.03,
        minimum_consensus_margin: float = 0.05,
    ) -> None:
        self._minimum_adjusted_confidence = _unit_interval(
            minimum_adjusted_confidence,
            "minimum_adjusted_confidence",
        )
        self._minimum_consensus_margin = _unit_interval(
            minimum_consensus_margin,
            "minimum_consensus_margin",
        )
        if isinstance(minimum_expected_value, bool) or not isinstance(
            minimum_expected_value, (int, float)
        ):
            raise ValueError("minimum_expected_value must be numeric")
        expected_value = float(minimum_expected_value)
        if not isfinite(expected_value):
            raise ValueError("minimum_expected_value must be finite")
        self._minimum_expected_value = expected_value

    def run(self, context: MatchContext) -> MatchContext:
        if context.consensus is None:
            raise ValueError("Decision Engine requires consensus output")
        if context.adjustment is None:
            raise ValueError("Decision Engine requires adjustment output")

        if context.adjustment.decision_blocked:
            output = DecisionOutput(
                action=DecisionAction.NO_DECISION,
                risk_level="high",
                rationale=(
                    "decision_blocked=true",
                    f"adjusted_confidence={context.adjustment.adjusted_confidence:.4f}",
                ),
            )
            return replace(context, decision=output)

        odds = _supported_odds(context)
        if odds is None:
            output = DecisionOutput(
                action=DecisionAction.WATCH,
                risk_level=_risk_level(context.adjustment.adjusted_confidence),
                rationale=(
                    "complete_1x2_odds=false",
                    f"adjusted_confidence={context.adjustment.adjusted_confidence:.4f}",
                ),
            )
            return replace(context, decision=output)

        probabilities = {
            "home": context.consensus.home_probability,
            "draw": context.consensus.draw_probability,
            "away": context.consensus.away_probability,
        }
        expected_values = {
            outcome: probabilities[outcome] * price - 1.0 for outcome, price in odds.items()
        }
        selected_market = _select_market(expected_values)
        selected_ev = expected_values[selected_market]
        adjusted_confidence = context.adjustment.adjusted_confidence
        consensus_margin = context.consensus.margin

        passes_confidence = adjusted_confidence + _TOLERANCE >= self._minimum_adjusted_confidence
        passes_ev = selected_ev + _TOLERANCE >= self._minimum_expected_value
        passes_margin = consensus_margin + _TOLERANCE >= self._minimum_consensus_margin
        action = (
            DecisionAction.CANDIDATE
            if passes_confidence and passes_ev and passes_margin
            else DecisionAction.NO_BET
        )

        rationale = (
            f"selected_probability={probabilities[selected_market]:.6f}",
            f"selected_odds={odds[selected_market]:.6f}",
            f"expected_value={selected_ev:.6f}",
            f"adjusted_confidence={adjusted_confidence:.4f}",
            f"consensus_margin={consensus_margin:.6f}",
            f"minimum_adjusted_confidence={self._minimum_adjusted_confidence:.4f}",
            f"minimum_expected_value={self._minimum_expected_value:.6f}",
            f"minimum_consensus_margin={self._minimum_consensus_margin:.6f}",
        )
        output = DecisionOutput(
            action=action,
            selected_market=selected_market,
            expected_value=round(selected_ev, 6),
            risk_level=_risk_level(adjusted_confidence),
            rationale=rationale,
        )
        return replace(context, decision=output)


def _supported_odds(context: MatchContext) -> dict[str, float] | None:
    odds: dict[str, float] = {}
    present = 0
    for outcome, key in _MARKETS:
        raw = context.market.get(key)
        if raw is None:
            continue
        present += 1
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{key} must be numeric decimal odds")
        value = float(raw)
        if not isfinite(value) or value <= 1.0:
            raise ValueError(f"{key} must be finite decimal odds greater than 1")
        odds[outcome] = value

    if present == 0:
        return None
    if present != len(_MARKETS):
        return None
    return odds


def _select_market(expected_values: dict[str, float]) -> str:
    best_market = "home"
    best_value = expected_values[best_market]
    for market in ("draw", "away"):
        value = expected_values[market]
        if value > best_value + _TOLERANCE:
            best_market = market
            best_value = value
    return best_market


def _risk_level(adjusted_confidence: float) -> str:
    if adjusted_confidence >= 0.85:
        return "low"
    if adjusted_confidence >= 0.70:
        return "medium"
    return "high"


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be finite and between 0 and 1")
    return result
