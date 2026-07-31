"""Governed validation for overlap-adjusted V2.2.1 dominant-tail mass."""

from __future__ import annotations

import pytest

from src.candidate_v2_2_1.dispersion import DispersionSignals, conditional_tail_width


def test_full_overlap_retains_only_stronger_weighted_directional_support() -> None:
    dominance_only = conditional_tail_width(
        DispersionSignals(dominance_risk=0.6)
    )
    fully_overlapping = conditional_tail_width(
        DispersionSignals(
            regime_break=0.6,
            dominance_risk=0.6,
            directional_evidence_overlap=1.0,
        )
    )

    assert fully_overlapping.dominant_tail_weight == pytest.approx(
        dominance_only.dominant_tail_weight
    )


def test_independent_directional_evidence_retains_additive_tail_support() -> None:
    regime_only = conditional_tail_width(
        DispersionSignals(regime_break=0.6)
    )
    dominance_only = conditional_tail_width(
        DispersionSignals(dominance_risk=0.6)
    )
    independent = conditional_tail_width(
        DispersionSignals(
            regime_break=0.6,
            dominance_risk=0.6,
            directional_evidence_overlap=0.0,
        )
    )

    assert independent.dominant_tail_weight == pytest.approx(
        regime_only.dominant_tail_weight + dominance_only.dominant_tail_weight
    )


def test_partial_overlap_reduces_tail_mass_monotonically() -> None:
    independent = conditional_tail_width(
        DispersionSignals(
            regime_break=0.6,
            dominance_risk=0.6,
            directional_evidence_overlap=0.0,
        )
    )
    partial = conditional_tail_width(
        DispersionSignals(
            regime_break=0.6,
            dominance_risk=0.6,
            directional_evidence_overlap=0.5,
        )
    )
    full = conditional_tail_width(
        DispersionSignals(
            regime_break=0.6,
            dominance_risk=0.6,
            directional_evidence_overlap=1.0,
        )
    )

    assert (
        full.dominant_tail_weight
        < partial.dominant_tail_weight
        < independent.dominant_tail_weight
    )


def test_overlap_adjustment_preserves_isolated_directional_tail_mass() -> None:
    no_overlap = conditional_tail_width(
        DispersionSignals(
            regime_break=0.7,
            directional_evidence_overlap=0.0,
        )
    )
    full_overlap = conditional_tail_width(
        DispersionSignals(
            regime_break=0.7,
            directional_evidence_overlap=1.0,
        )
    )

    assert full_overlap == no_overlap


def test_overlap_adjustment_reduces_conflicting_tail_allocation() -> None:
    independent = conditional_tail_width(
        DispersionSignals(
            regime_break=0.7,
            dominance_risk=0.7,
            low_event_risk=0.8,
            directional_evidence_overlap=0.0,
        )
    )
    overlapping = conditional_tail_width(
        DispersionSignals(
            regime_break=0.7,
            dominance_risk=0.7,
            low_event_risk=0.8,
            directional_evidence_overlap=1.0,
        )
    )

    assert overlapping.dominant_tail_weight < independent.dominant_tail_weight
    assert (
        overlapping.low_event_weight + overlapping.dominant_tail_weight
        <= 1.0
    )
