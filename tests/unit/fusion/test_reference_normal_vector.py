from __future__ import annotations

import numpy as np

from src.inference.posterior import compute_posterior


def test_normal_normal_vector_reference():
    # Analytic example:
    # prior Sigma0 = diag(1.0, 4.0), mu0 = [0,2]
    # H = identity, Y = [1,1], V = identity
    mu0 = np.array([0.0, 2.0])
    Sigma0 = np.diag([1.0, 4.0])
    H = np.eye(2)
    Y = np.array([1.0, 1.0])
    V = np.eye(2)

    mu_post, Sigma_post = compute_posterior(mu0, Sigma0, H, Y, V)

    # Expected: A = [[2,0],[0,1.25]] => Sigma_post = [[0.5,0],[0,0.8]]
    # mu_post = [0.5, 1.2]
    assert abs(mu_post[0] - 0.5) < 1e-12
    assert abs(mu_post[1] - 1.2) < 1e-12
    assert abs(Sigma_post[0, 0] - 0.5) < 1e-12
    assert abs(Sigma_post[1, 1] - 0.8) < 1e-12
    assert abs(Sigma_post[0, 1]) < 1e-12
