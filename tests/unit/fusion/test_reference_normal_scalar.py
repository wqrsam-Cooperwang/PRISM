from __future__ import annotations

import numpy as np

from src.inference.fusion_core import (
    FusionConfig,
    EvidenceFusionEngine,
)
from src.governance.dependency_matrix import DependencyMatrix
from src.evidence.models import EvidenceResult


def test_normal_normal_scalar_reference():
    # Analytic reference: prior mu0=1.0, sigma0^2=4.0, observation y=2.0 var=1.0
    prior_means = {"theta": 1.0}
    prior_vars = {"theta": 4.0}
    dm = DependencyMatrix()
    cfg = FusionConfig(prior_means=prior_means, prior_variances=prior_vars, dependency_matrix=dm)
    engine = EvidenceFusionEngine(cfg)

    # Build EvidenceResult-like object by constructing a minimal object
    e = EvidenceResult(
        provider_id="p1",
        source="test",
        timestamp="2026-01-01T00:00:00Z",
        evidence_id="p1:theta",
        targets=("theta",),
        suggestion={"theta": 2.0},
        variance={"theta": 1.0},
        reliability=1.0,
        weight=1.0,
        direction={"theta": 1.0},
        confidence=1.0,
        metadata={},
        freshness=None,
        half_life=3600,
        decay_function="exponential",
        dependency_vector=None,
        units={"theta": "unitless"},
        ranges={"theta": (-10.0, 10.0)},
    )

    posterior = engine.fuse([e])
    # Expected posterior variance = 0.8, mean = 1.8
    lam = posterior.lambda_home  # engine maps first latent to lambda_home position
    assert abs(lam.posterior_mean - 1.8) < 1e-9
    assert abs(lam.posterior_variance - 0.8) < 1e-9
