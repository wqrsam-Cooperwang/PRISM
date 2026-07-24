from src.decision.engine import DecisionEngine
from src.runtime import build_runtime


def complete_evidence() -> dict[str, float]:
    return {
        "lineup": 1.0,
        "injuries": 1.0,
        "odds": 1.0,
        "weather": 1.0,
        "tactical_data": 1.0,
        "historical_data": 1.0,
        "market_data": 1.0,
        "motivation": 1.0,
    }


def test_build_runtime_assembles_canonical_engine_graph() -> None:
    runtime = build_runtime(complete_evidence())

    assert tuple(engine.name for engine in runtime.engines) == (
        "evidence",
        "consensus",
        "confidence",
        "rules",
        "adjustment",
        "decision",
    )


def test_build_runtime_copies_evidence_configuration() -> None:
    completeness = complete_evidence()
    runtime = build_runtime(completeness)
    completeness["lineup"] = 0.0

    evidence_engine = runtime.engines[0]
    assert evidence_engine._completeness["lineup"] == 1.0


def test_build_runtime_accepts_governed_decision_override() -> None:
    decision = DecisionEngine(
        minimum_adjusted_confidence=0.0,
        minimum_expected_value=-1.0,
        minimum_consensus_margin=0.0,
    )

    runtime = build_runtime(complete_evidence(), decision_engine=decision)

    assert runtime.engines[-1] is decision
