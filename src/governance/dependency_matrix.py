"""Dependency matrix utilities for EvidenceFusion.

Stores declared dependency strengths and maps them to correlation coefficients
used when assembling the observation covariance matrix V.
"""
from __future__ import annotations

from typing import Mapping, Dict, Iterable

import math


class DependencyMatrix:
    """Holds a square map of provider_id -> provider_id -> dependency_strength.

    Values in the matrix are in [0,1]. The class provides symmetrization and
    mapping to correlation coefficients (rho) via a configurable scale kappa.
    """

    def __init__(self, kappa: float = 1.0) -> None:
        self._data: Dict[str, Dict[str, float]] = {}
        self.kappa = float(kappa)

    def set(self, a: str, b: str, strength: float) -> None:
        if strength < 0.0 or strength > 1.0:
            raise ValueError("dependency strength must be in [0,1]")
        self._data.setdefault(a, {})[b] = float(strength)

    def get(self, a: str, b: str) -> float:
        return float(self._data.get(a, {}).get(b, 0.0))

    def symmetrized_pairs(self) -> Iterable[tuple[str, str, float]]:
        """Yield (a,b,strength) for all known providers with symmetrized strength.

        Strength is max(D[a,b], D[b,a])."""
        keys = set(self._data.keys())
        for a in list(keys):
            keys.update(self._data.get(a, {}).keys())
        seen = set()
        for a in sorted(keys):
            for b in sorted(keys):
                if (a, b) in seen or (b, a) in seen:
                    continue
                seen.add((a, b))
                s1 = self._data.get(a, {}).get(b, 0.0)
                s2 = self._data.get(b, {}).get(a, 0.0)
                yield (a, b, float(max(s1, s2)))

    def correlation(self, a: str, b: str) -> float:
        """Return correlation coefficient rho in [0,1] mapped from dependency strength.

        rho = kappa * max(D[a,b], D[b,a])
        """
        s = max(self._data.get(a, {}).get(b, 0.0), self._data.get(b, {}).get(a, 0.0))
        rho = min(1.0, self.kappa * float(s))
        return float(rho)

    def providers(self) -> Iterable[str]:
        keys = set(self._data.keys())
        for a in list(keys):
            keys.update(self._data.get(a, {}).keys())
        return sorted(keys)
