"""Governed end-to-end runtime orchestration for PRISM."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from src.adjustment.engine import AdjustmentEngine
from src.confidence.engine import ConfidenceEngine
from src.consensus.engine import ConsensusEngine
from src.core.engine import Engine
from src.decision.engine import DecisionEngine
from src.domain.models import MatchContext
from src.rules.engine import RuleEngine

_CANONICAL_SEQUENCE = (
    "evidence",
    "consensus",
    "confidence",
    "rules",
    "adjustment",
    "decision",
)


@dataclass(frozen=True)
class EngineTrace:
    """One successfully completed runtime step."""

    name: str
    version: str
    status: str = "completed"


@dataclass(frozen=True)
class RuntimeResult:
    """Successful PRISM runtime result."""

    context: MatchContext
    engine_trace: tuple[EngineTrace, ...]
    runtime_version: str = "1.0.0"


class OrchestrationError(RuntimeError):
    """Wrap an engine failure while preserving the successful partial run."""

    def __init__(
        self,
        *,
        engine_name: str,
        engine_version: str,
        partial_context: MatchContext,
        completed_trace: tuple[EngineTrace, ...],
    ) -> None:
        self.engine_name = engine_name
        self.engine_version = engine_version
        self.partial_context = partial_context
        self.completed_trace = completed_trace
        super().__init__(f"PRISM engine failed: {engine_name} {engine_version}")


class PrismOrchestrator:
    """Execute the canonical PRISM V1 engine sequence."""

    version = "1.0.0"

    def __init__(self, engines: Iterable[Engine]) -> None:
        self._engines = tuple(engines)
        self._validate_engine_configuration()

    @classmethod
    def standard(
        cls,
        evidence_engine: Engine,
        *,
        decision_engine: Engine | None = None,
    ) -> PrismOrchestrator:
        """Build the canonical runtime using a configured Evidence Engine."""

        return cls(
            (
                evidence_engine,
                ConsensusEngine(),
                ConfidenceEngine(),
                RuleEngine(),
                AdjustmentEngine(),
                DecisionEngine() if decision_engine is None else decision_engine,
            )
        )

    @property
    def engines(self) -> tuple[Engine, ...]:
        return self._engines

    def run(self, context: MatchContext) -> RuntimeResult:
        self._preflight(context)
        current = context
        completed: list[EngineTrace] = []

        for engine in self._engines:
            try:
                current = engine.run(current)
            except Exception as exc:
                raise OrchestrationError(
                    engine_name=engine.name,
                    engine_version=engine.version,
                    partial_context=current,
                    completed_trace=tuple(completed),
                ) from exc
            completed.append(EngineTrace(name=engine.name, version=engine.version))

        return RuntimeResult(
            context=current,
            engine_trace=tuple(completed),
            runtime_version=self.version,
        )

    def _preflight(self, context: MatchContext) -> None:
        if not context.model_outputs:
            raise ValueError("PRISM runtime requires at least one model output")

    def _validate_engine_configuration(self) -> None:
        names: list[str] = []
        for engine in self._engines:
            name = getattr(engine, "name", "")
            version = getattr(engine, "version", "")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Every runtime engine requires a non-empty name")
            if not isinstance(version, str) or not version.strip():
                raise ValueError("Every runtime engine requires a non-empty version")
            names.append(name)

        if len(names) != len(set(names)):
            raise ValueError("PRISM runtime engine names must be unique")
        if tuple(names) != _CANONICAL_SEQUENCE:
            raise ValueError(
                "PRISM runtime engines must follow canonical sequence: "
                + " -> ".join(_CANONICAL_SEQUENCE)
            )
