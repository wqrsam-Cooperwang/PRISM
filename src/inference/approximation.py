"""Approximation utilities for non-Gaussian evidence.

Provides Laplace approximation helpers for common likelihoods (e.g., logistic).
"""
from __future__ import annotations

import math
from typing import Tuple


def logit(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be in (0,1) for logit")
    return math.log(p / (1.0 - p))


def laplace_approx_logistic(p_obs: float, n: int = 1) -> Tuple[float, float]:
    """Laplace approximation for logistic parameter theta given observed proportion p_obs.

    Assumes Bernoulli observations with success proportion p_obs over n trials.
    MAP approx: theta_hat = logit(p_obs)
    Observed Fisher information: I = n * p_obs * (1 - p_obs)
    Approx posterior: theta ~ N(theta_hat, 1/I)
    """
    if p_obs <= 0.0 or p_obs >= 1.0:
        raise ValueError("p_obs must be in (0,1) for Laplace logistic")
    theta_hat = logit(p_obs)
    I = float(n) * p_obs * (1.0 - p_obs)
    if I <= 0.0:
        raise ValueError("Fisher information non-positive")
    var = 1.0 / I
    return theta_hat, var
