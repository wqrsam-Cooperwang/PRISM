"""Shared engine contract for the PRISM runtime."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.models import MatchContext


@runtime_checkable
class Engine(Protocol):
    """Protocol implemented by every PRISM processing engine."""

    name: str
    version: str

    def run(self, context: MatchContext) -> MatchContext:
        """Process one immutable context and return a new context."""
        ...
