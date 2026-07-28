"""Posterior computation utilities for EvidenceFusionEngine.

Provides numerically stable computation of the Normal-Normal posterior update:

    Sigma_post = (Sigma0^{-1} + H^T V^{-1} H)^{-1}
    mu_post = Sigma_post (Sigma0^{-1} mu0 + H^T V^{-1} Y)

Includes safe inversion, jitter, and PSD enforcement.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
from numpy.linalg import LinAlgError

from src.inference.covariance import safe_matrix_inverse, project_to_psd

EPS = 1e-12


def compute_posterior(mu0: np.ndarray, Sigma0: np.ndarray, H: np.ndarray, Y: np.ndarray, V: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Compute posterior mean and covariance in a numerically stable way.

    Returns (mu_post, Sigma_post).
    """
    # Ensure shapes
    mu0 = np.asarray(mu0, dtype=float)
    Sigma0 = np.asarray(Sigma0, dtype=float)
    H = np.asarray(H, dtype=float)
    Y = np.asarray(Y, dtype=float)
    V = np.asarray(V, dtype=float)

    # invert Sigma0 safely
    try:
        Sigma0_inv = np.linalg.inv(Sigma0)
    except LinAlgError:
        Sigma0_inv = np.linalg.pinv(Sigma0)

    # invert V safely
    try:
        V_inv = np.linalg.inv(V)
    except LinAlgError:
        V_inv = np.linalg.pinv(V)

    # compute precision
    A = Sigma0_inv + H.T @ V_inv @ H
    A = 0.5 * (A + A.T)
    # invert A safely
    try:
        Sigma_post = np.linalg.inv(A)
    except LinAlgError:
        Sigma_post = np.linalg.pinv(A)

    # enforce PSD
    Sigma_post = project_to_psd(Sigma_post)

    mu_post = Sigma_post @ (Sigma0_inv @ mu0 + H.T @ V_inv @ Y)

    # clip variances
    diag = np.diag(Sigma_post)
    diag = np.clip(diag, a_min=EPS, a_max=None)
    for i in range(len(diag)):
        Sigma_post[i, i] = diag[i]

    return mu_post, Sigma_post
