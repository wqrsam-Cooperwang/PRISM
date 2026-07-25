from dataclasses import replace
from datetime import datetime, timezone

from src.adjustment.engine import AdjustmentEngine
from src.collection import (
    CollectionGateDecision,
    CollectionReadinessGateResult,
    apply_collection_governance,
    collection_governance_effects,
)
from src.decision.engine import DecisionEngine
from src.domain.models import (
    AnalysisSession,
    ConfidenceBand,
    ConfidenceOutput,
    ConsensusOutput,
    DecisionAction,
    MatchContext,
    MatchInfo,
    TeamInfo,
)


def _gate(decision: CollectionGateDecision) -> CollectionReadinessGateResult:
    return CollectionReadinessGateResult(
        decision=decision,
        covered_core_categories=(),
        missing_core_categories=(),
        covered_optional_categories=(),
        source_ids=("source-a",),
        source_types=("official",),
        elo_baseline_available=True,
        market_baseline_available=True,
        reasons=("test reason",) if decision != CollectionGateDecision.READY else (),
    )


def _context(overall: float = 0.90) -> MatchContext:
    return MatchContext(
        session=AnalysisSession(
            session_id="degraded-governance-session",
            created_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
            prism_version="test",
        ),
        match=MatchInfo(
            match_id="degraded-governance-match",
            competition="Test League",
            kickoff=datetime(2026, 7, 25, 18, 0, tzinfo=timezone.utc),
        ),
        home_team=TeamInfo(team_id="home", name="Home FC"),
        away_team=TeamInfo(team_id="away", name="Away FC"),
        market={"home_odds": 2.0, "draw_odds": 4.0, "away_odds": 5.0},
        consensus=ConsensusOutput(
            model_count=2,
            model_ids=("elo_probability", "market_probability"),
            home_probability=0.60,
            draw_probability=0.20,
            away_probability=0.20,
            agreement=0.90,
            mean_pairwise_distance=0.10,
            max_spread=0.10,
            leading_outcome="home",
            margin=0.40,
        ),
        confidence=ConfidenceOutput(
            evidence=0.90,
            model=0.90,
            context=0.90,
            consensus=0.90,
            overall=overall,
            band=ConfidenceBand.VERY_HIGH,
        ),
    )


def _existing_rule(*effects: str) -> dict[str, object]:
    return {
        "rule_id": "EXISTING-RULE",
        "effective_effects": effects,
    }


def test_ready_collection_adds_no_restrictive_effect() -> None:
    gate = _gate(CollectionGateDecision.READY)
    context = apply_collection_governance(_context(), gate)

    assert collection_governance_effects(gate) == ()
    assert context.rule_outputs[-1]["effective_effects"] == ()

    adjusted = AdjustmentEngine().run(context)
    assert adjusted.adjustment is not None
    assert adjusted.adjustment.adjusted_confidence == 0.90
    assert adjusted.adjustment.confidence_cap is None


def test_degraded_collection_caps_confidence_and_prevents_candidate() -> None:
    gate = _gate(CollectionGateDecision.DEGRADED)
    context = apply_collection_governance(_context(), gate)

    adjusted = AdjustmentEngine().run(context)
    assert adjusted.adjustment is not None
    assert adjusted.adjustment.adjusted_confidence == 0.69
    assert adjusted.adjustment.confidence_cap == 0.69
    assert "restrict_high_confidence_action" in adjusted.adjustment.applied_effects

    decided = DecisionEngine().run(adjusted)
    assert decided.decision is not None
    assert decided.decision.action is DecisionAction.NO_BET


def test_rejected_collection_maps_to_active_decision_block() -> None:
    gate = _gate(CollectionGateDecision.REJECTED)
    context = apply_collection_governance(_context(), gate)

    adjusted = AdjustmentEngine().run(context)
    assert adjusted.adjustment is not None
    assert adjusted.adjustment.adjusted_confidence == 0.34
    assert adjusted.adjustment.decision_blocked is True

    decided = DecisionEngine().run(adjusted)
    assert decided.decision is not None
    assert decided.decision.action is DecisionAction.NO_DECISION


def test_collection_governance_never_relaxes_stricter_existing_rule() -> None:
    original = replace(
        _context(),
        rule_outputs=(_existing_rule("restrict_active_decision"),),
    )
    governed = apply_collection_governance(original, _gate(CollectionGateDecision.DEGRADED))
    adjusted = AdjustmentEngine().run(governed)

    assert adjusted.adjustment is not None
    assert adjusted.adjustment.adjusted_confidence == 0.49
    assert adjusted.adjustment.confidence_cap == 0.49


def test_collection_governance_injection_is_idempotent() -> None:
    gate = _gate(CollectionGateDecision.DEGRADED)
    first = apply_collection_governance(_context(), gate)
    second = apply_collection_governance(first, gate)

    records = [
        output
        for output in second.rule_outputs
        if output.get("governance_source") == "collection_readiness_gate"
    ]
    assert len(records) == 1
    assert records[0]["collection_gate_decision"] == "degraded"
