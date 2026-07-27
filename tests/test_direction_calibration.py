import pytest

from src.consensus import DirectionCalibrator
from src.domain.models import ConsensusOutput, EvidenceGate, EvidenceOutput


def _consensus(*, agreement: float = 0.81) -> ConsensusOutput:
    return ConsensusOutput(
        model_count=2,
        model_ids=("a", "b"),
        home_probability=0.60,
        draw_probability=0.25,
        away_probability=0.15,
        agreement=agreement,
        mean_pairwise_distance=0.10,
        max_spread=0.12,
        leading_outcome="home",
        margin=0.35,
        method="test",
    )


def _evidence(score: int = 81) -> EvidenceOutput:
    return EvidenceOutput(
        score=score,
        raw_score=float(score),
        gate=EvidenceGate.ACCEPTED,
    )


def test_direction_calibration_preserves_order_and_reduces_concentration() -> None:
    output = DirectionCalibrator().run(_consensus(), _evidence())

    assert output.reliability == pytest.approx(0.81)
    assert output.home_probability == pytest.approx(0.5493333333333333)
    assert output.draw_probability == pytest.approx(0.2658333333333333)
    assert output.away_probability == pytest.approx(0.18483333333333332)
    assert output.home_probability > output.draw_probability > output.away_probability
    assert output.calibrated_leading_probability < output.raw_leading_probability


def test_perfect_support_leaves_consensus_unchanged() -> None:
    output = DirectionCalibrator().run(_consensus(agreement=1.0), _evidence(100))

    assert output.reliability == pytest.approx(1.0)
    assert output.home_probability == pytest.approx(0.60)
    assert output.draw_probability == pytest.approx(0.25)
    assert output.away_probability == pytest.approx(0.15)


def test_zero_support_returns_uniform_distribution() -> None:
    output = DirectionCalibrator().run(_consensus(agreement=0.0), _evidence(0))

    assert output.reliability == 0.0
    assert output.home_probability == pytest.approx(1.0 / 3.0)
    assert output.draw_probability == pytest.approx(1.0 / 3.0)
    assert output.away_probability == pytest.approx(1.0 / 3.0)
