"""Evidence aging utilities.

Provide decay functions and application that compute decayed reliability for
EvidenceResult items according to the Architecture Freeze.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

import math
from src.evidence.models import EvidenceResult


def _iso_to_dt(s: str) -> datetime:
    # Expect ISO with Z or offset
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def decay_exponential(r0: float, delta_seconds: float, half_life: float) -> float:
    if half_life is None or half_life <= 0:
        return float(r0)
    # r(t) = r0 * 2^{-delta / half_life}
    factor = math.pow(2.0, -float(delta_seconds) / float(half_life))
    return float(r0 * factor)


def decay_linear(r0: float, delta_seconds: float, half_life: float, k: float = 1.0) -> float:
    if half_life is None or half_life <= 0:
        return float(r0)
    max_seconds = float(k * half_life)
    frac = min(1.0, max(0.0, float(delta_seconds) / max_seconds))
    return float(max(0.0, r0 * (1.0 - frac)))


def apply_decay(e: EvidenceResult, now: datetime | None = None) -> float:
    """Return decayed reliability for an EvidenceResult.

    This does not mutate the EvidenceResult; it returns the decayed reliability
    as a float in [0,1]. If required fields are missing, raises ValueError.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if not e.timestamp:
        raise ValueError("EvidenceResult missing timestamp for decay")
    if e.half_life is None:
        # fallback: extremely long half-life -> near-constant
        half_life = float(365 * 24 * 3600)
    else:
        half_life = float(e.half_life)

    t0 = _iso_to_dt(e.timestamp)
    delta = (now - t0).total_seconds()
    r0 = float(e.reliability)

    df = e.decay_function or "exponential"
    if df == "exponential":
        return decay_exponential(r0, delta, half_life)
    if df == "linear":
        return decay_linear(r0, delta, half_life)
    # custom not supported in scaffold; fall back to exponential
    return decay_exponential(r0, delta, half_life)
