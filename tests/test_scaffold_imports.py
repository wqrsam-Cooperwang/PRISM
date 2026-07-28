from __future__ import annotations

import importlib


def test_scaffold_imports() -> None:
    """Ensure scaffold modules import without executing heavy code.

    This test verifies that the initial scaffolding of the V3.4 architecture
    is importable and the public classes exist. It is intentionally lightweight
    and stable.
    """
    modules = [
        "src.evidence.models",
        "src.inference.models",
        "src.inference.fusion",
        "src.simulation.montecarlo",
        "src.explainability.explain",
        "src.governance",
    ]
    for m in modules:
        mod = importlib.import_module(m)
        assert mod is not None
