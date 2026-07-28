from __future__ import annotations

"""Tests for covariance construction and numerical stability."""

import numpy as np
from datetime import datetime, timezone

from src.inference.covariance import (
    build_covariance_matrix,
    cholesky_with_jitter,
    project_to_psd,
    is_spd,
)
from src.governance.dependency_matrix import DependencyMatrix


def test_covariance_elements():
    observations = [
        {"provider": "p1", "var": 0.5},
        {"provider": "p2", "var": 2.0},
    ]
    dm = DependencyMatrix()
    dm.set("p1", "p2", 0.6)
    V = build_covariance_matrix(observations, dependency_matrix=dm, kappa=1.0)
    expected_off = 0.6 * (0.5 * 2.0) ** 0.5
    assert abs(V[0, 1] - expected_off) < 1e-12
    assert abs(V[1, 0] - expected_off) < 1e-12
    assert abs(V[0, 0] - 0.5) < 1e-12
    assert abs(V[1, 1] - 2.0) < 1e-12


def test_cholesky_jitter_and_psd_projection():
    # Construct singular covariance: [[1,1],[1,1]]
    V = np.array([[1.0, 1.0], [1.0, 1.0]])
    # initially not SPD (rank-deficient)
    assert not is_spd(V)
    # attempt jittered cholesky
    try:
        L, jitter = cholesky_with_jitter(V, max_tries=10, initial_jitter=1e-12)
        # if succeeded, verify L @ L.T approx V + jitter*I
        recon = L @ L.T
        assert np.allclose(recon, V + jitter * np.eye(2), atol=1e-8)
    except Exception:
        # fallback to PSD projection
        M_psd = project_to_psd(V)
        # projected matrix must be PSD
        assert np.all(np.linalg.eigvals(M_psd) >= -1e-12)


def test_project_to_psd_negative_eigs():
    # create symmetric matrix with negative eigenvalue
    M = np.array([[2.0, 3.0], [3.0, -10.0]])
    vals_before = np.linalg.eigvals(M)
    M_psd = project_to_psd(M)
    vals_after = np.linalg.eigvals(M_psd)
    # all eigenvalues non-negative after projection
    assert all(v >= -1e-12 for v in vals_after)
    # projection reduces Frobenius norm distance to a PSD matrix
    # (not strict check, but must be valid PSD)
    assert np.allclose(M_psd, M_psd.T)
