"""Observation covariance utilities for EvidenceFusionEngine.

Provides functions to construct the observation covariance matrix V from
per-observation variances and a DependencyMatrix, and numerical helpers to
ensure SPD/PSD properties with Cholesky jitter and SVD fallback.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence, Tuple

import numpy as np
from numpy.linalg import LinAlgError

from src.governance.dependency_matrix import DependencyMatrix

EPS = 1e-12


def build_covariance_matrix(observations: Sequence[Mapping[str, object]], dependency_matrix: DependencyMatrix | None = None, kappa: float = 1.0) -> np.ndarray:
    """Construct full observation covariance matrix V.

    observations: sequence of dicts with keys:
        - 'provider': provider id str
        - 'var': variance (float)

    dependency_matrix: optional DependencyMatrix instance mapping provider pairs
    to dependency strengths in [0,1]. If None, observations are treated as independent.

    Returns: V as (n,n) ndarray.
    """
    n = len(observations)
    V = np.zeros((n, n), dtype=float)
    for i in range(n):
        v_i = float(observations[i]["var"])
        V[i, i] = max(v_i, EPS)
    if dependency_matrix is None:
        return V
    for i in range(n):
        for j in range(i + 1, n):
            prov_i = observations[i]["provider"]
            prov_j = observations[j]["provider"]
            s = dependency_matrix.get(prov_i, prov_j)
            rho = min(1.0, float(kappa) * float(s))
            cov = rho * np.sqrt(max(EPS, float(observations[i]["var"]) * float(observations[j]["var"])))
            V[i, j] = cov
            V[j, i] = cov
    return V


def is_spd(mat: np.ndarray, tol: float = 1e-12) -> bool:
    """Check if a matrix is symmetric positive definite (SPD).

    Uses attempt at Cholesky decomposition.
    """
    try:
        if mat.shape[0] == 0:
            return False
        # ensure symmetry
        if not np.allclose(mat, mat.T, atol=1e-12, rtol=1e-8):
            return False
        np.linalg.cholesky(mat + tol * np.eye(mat.shape[0]))
        return True
    except LinAlgError:
        return False


def cholesky_with_jitter(mat: np.ndarray, max_tries: int = 5, initial_jitter: float = 1e-10) -> Tuple[np.ndarray, float]:
    """Attempt Cholesky decomposition, adding increasing diagonal jitter until success.

    Returns: (L, jitter) where L is lower-triangular Cholesky factor of (mat + jitter*I).
    Raises LinAlgError if decomposition fails after max_tries.
    """
    n = mat.shape[0]
    jitter = float(initial_jitter)
    for attempt in range(max_tries):
        try:
            L = np.linalg.cholesky(mat + jitter * np.eye(n))
            return L, jitter
        except LinAlgError:
            jitter *= 10.0
    # final attempt with SVD fallback will be handled by caller
    raise LinAlgError("Cholesky failed after jitter attempts")


def project_to_psd(mat: np.ndarray) -> np.ndarray:
    """Project a symmetric matrix to the nearest PSD matrix via eigenvalue clipping.

    This returns a symmetric PSD matrix.
    """
    # ensure symmetry
    M = 0.5 * (mat + mat.T)
    vals, vecs = np.linalg.eigh(M)
    vals_clipped = np.clip(vals, a_min=0.0, a_max=None)
    M_psd = (vecs * vals_clipped) @ vecs.T
    # symmetrize again
    M_psd = 0.5 * (M_psd + M_psd.T)
    return M_psd


def safe_matrix_inverse(mat: np.ndarray) -> np.ndarray:
    """Compute a numerically stable inverse: try inverse, else pseudo-inverse via SVD.

    Returns the inverse or pseudo-inverse.
    """
    try:
        return np.linalg.inv(mat)
    except LinAlgError:
        # fallback to pseudo-inverse
        return np.linalg.pinv(mat)
