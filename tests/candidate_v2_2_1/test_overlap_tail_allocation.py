"""Governed overlap tests for V2.2.1 dominant-tail allocation."""

from __future__ import annotations

import pytest

from src.candidate_v2_2_1.dispersion import DispersionSignals, conditional_tail_width


def test_full_overlap_discounts_explicit_dominant_tail_mass() -> None:
    independent = conditional_tail_width(
        DispersionSignals(
            regime_break=0.5,
            dominance_risk=0.5,
            directional_evidence_overlap=0.0,
        )
    )
    overlapping = conditional_tail_width(
        DispersionSignals(
            regime_break=0.5,
            dominance_risk=0.5,
            directional_evidence_overlap=1.0,
        )
    )

    assert overlapping.dominant_tail_weight < independent.dominant_tail_weight
    assert overlapping.dominant_tail_weight > 0.0


def test_partial_overlap_discounts_tail_mass_smoothly() -> None:
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

    assert full.dominant_tail_weight < partial.dominant_tail_weight
    assert partial.dominant_tail_weight < independent.dominant_tail_weight


def test_full_overlap_falls_back_to_stronger_activated_contribution() -> None:
    dominance_only = conditional_tail_width(DispersionSignals(dominance_risk=0.7))
    fully_overlapping = conditional_tail_width(
        DispersionSignals(
            regime_break=0.7,
            dominance_risk=0.7,
            directional_evidence_overlap=1.0,
        )
    )

    assert fully_overlapping.dominant_tail_weight == pytest.approx(
        dominance_only.dominant_tail_weight
    )
