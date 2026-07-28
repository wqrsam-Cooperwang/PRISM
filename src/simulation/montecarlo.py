from __future__ import annotations

"""Monte Carlo engine stub for PRISM Enterprise.

This module defines the MonteCarloEngine interface. The full Monte Carlo
simulation will be implemented in Phase E following the Architecture Freeze.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from src.inference.models import PosteriorMatchState


@dataclass(frozen=True)
class SimulationResult:
    match_id: str
    n_sims: int
    score_distribution: Mapping[str, int]
    win_probabilities: Mapping[str, float]
    btts_prob: float
    over_under_cdf: Mapping[float, float]
    goal_distribution: Mapping[int, int]
    sample_entropy: float
    stats: Mapping[str, float]


class MonteCarloEngine:
    """Monte Carlo simulator interface.

    The actual vectorized implementation will be completed in Phase E.
    """

    def __init__(self) -> None:
        pass

    def simulate(self, posterior: PosteriorMatchState, goalstate_model: object, scenario_mixture: object, n_sims: int = 1000, seed: int | None = None) -> SimulationResult:
        raise NotImplementedError("MonteCarloEngine.simulate is not implemented yet")
