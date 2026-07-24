"""Execute PRISM benchmark comparison and promotion governance from frozen JSONL datasets."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.evaluation import (
    PromotionPolicy,
    compare_benchmarks,
    evaluate_promotion,
    import_evaluation_jsonl,
    release_gate_exit_code,
    render_comparison_json,
    render_comparison_markdown,
    render_promotion_json,
    render_promotion_markdown,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the governed PRISM benchmark promotion gate.")
    parser.add_argument("baseline", type=Path, help="Baseline evaluation JSONL dataset")
    parser.add_argument("candidate", type=Path, help="Candidate evaluation JSONL dataset")
    parser.add_argument("output_dir", type=Path, help="Directory for generated governance reports")
    parser.add_argument("--minimum-case-count", type=int, default=100)
    parser.add_argument("--minimum-brier-improvement", type=float, default=0.001)
    return parser


def run_gate(
    baseline_path: Path,
    candidate_path: Path,
    output_dir: Path,
    *,
    minimum_case_count: int = 100,
    minimum_brier_improvement: float = 0.001,
) -> int:
    """Run promotion governance, persist all reports, and return the governed exit code."""

    baseline_payload = baseline_path.read_text(encoding="utf-8")
    candidate_payload = candidate_path.read_text(encoding="utf-8")
    baseline_records = import_evaluation_jsonl(baseline_payload)
    candidate_records = import_evaluation_jsonl(candidate_payload)

    comparison = compare_benchmarks(baseline_records, candidate_records)
    promotion = evaluate_promotion(
        comparison,
        PromotionPolicy(
            minimum_case_count=minimum_case_count,
            minimum_brier_improvement=minimum_brier_improvement,
        ),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "comparison.json").write_text(
        render_comparison_json(comparison) + "\n",
        encoding="utf-8",
    )
    (output_dir / "comparison.md").write_text(
        render_comparison_markdown(comparison),
        encoding="utf-8",
    )
    (output_dir / "promotion-decision.json").write_text(
        render_promotion_json(promotion),
        encoding="utf-8",
    )
    (output_dir / "promotion-decision.md").write_text(
        render_promotion_markdown(promotion),
        encoding="utf-8",
    )
    return release_gate_exit_code(promotion)


def main() -> int:
    args = _parser().parse_args()
    return run_gate(
        args.baseline,
        args.candidate,
        args.output_dir,
        minimum_case_count=args.minimum_case_count,
        minimum_brier_improvement=args.minimum_brier_improvement,
    )


if __name__ == "__main__":
    raise SystemExit(main())
