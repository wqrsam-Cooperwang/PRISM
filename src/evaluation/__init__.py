"""Post-match evaluation of governed PRISM predictions."""

from src.evaluation.comparison import (
    BenchmarkComparison,
    MetricComparison,
    compare_benchmarks,
)
from src.evaluation.comparison_report import (
    COMPARISON_REPORT_VERSION,
    comparison_report_payload,
    render_comparison_json,
    render_comparison_markdown,
)
from src.evaluation.dataset import (
    DATASET_SCHEMA_VERSION,
    EXPORT_VERSION,
    DatasetExport,
    DatasetManifest,
    EvaluationRecord,
    export_evaluation_csv,
    export_evaluation_jsonl,
    records_from_summary,
)
from src.evaluation.harness import RealMatchEvaluationHarness
from src.evaluation.importer import (
    BenchmarkSummary,
    import_evaluation_csv,
    import_evaluation_jsonl,
    load_benchmark,
)
from src.evaluation.models import EvaluationCase, EvaluationResult, EvaluationSummary

__all__ = [
    "COMPARISON_REPORT_VERSION",
    "DATASET_SCHEMA_VERSION",
    "EXPORT_VERSION",
    "BenchmarkComparison",
    "BenchmarkSummary",
    "DatasetExport",
    "DatasetManifest",
    "EvaluationCase",
    "EvaluationRecord",
    "EvaluationResult",
    "EvaluationSummary",
    "MetricComparison",
    "RealMatchEvaluationHarness",
    "compare_benchmarks",
    "comparison_report_payload",
    "export_evaluation_csv",
    "export_evaluation_jsonl",
    "import_evaluation_csv",
    "import_evaluation_jsonl",
    "load_benchmark",
    "records_from_summary",
    "render_comparison_json",
    "render_comparison_markdown",
]
