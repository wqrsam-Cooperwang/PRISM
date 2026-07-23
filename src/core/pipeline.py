"""Composable immutable engine pipeline."""

from __future__ import annotations

from collections.abc import Iterable

from src.core.engine import Engine
from src.domain.models import MatchContext


class Pipeline:
    """Run registered engines in order against one MatchContext."""

    def __init__(self, engines: Iterable[Engine]) -> None:
        self._engines = tuple(engines)

    @property
    def engines(self) -> tuple[Engine, ...]:
        return self._engines

    def run(self, context: MatchContext) -> MatchContext:
        current = context
        for engine in self._engines:
            current = engine.run(current)
        return current
