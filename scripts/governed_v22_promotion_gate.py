"""Run the governed PRISM V2.2 promotion gate from formal ledgers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.regression import V22PromotionPolicy, evaluate_governed_v22_promotion

EXIT_CODES = {
    "promote": 0,
    "hold": 2,
    "reject": 3,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run governed V2.2 promotion from formal prediction/outcome ledgers."
    )
    parser.add_argument(
        "prediction_root",
        type=Path,
        help="Formal performance-ledger directory",
    )
    parser.add_argument(
        "outcome_root",
        type=Path,
        help="Verified outcome-ledger directory",
    )
    parser.add_argument(
        "output_path",
        type=Path,
        help="Machine-readable promotion decision JSON path",
    )
    parser.add_argument("--minimum-scoreline-cases", type=int, default=30)
    parser.add_argument("--minimum-full-stack-cases", type=int, default=30)
    return parser


def run_gate(
    prediction_root: Path,
    outcome_root: Path,
    output_path: Path,
    *,
    minimum_scoreline_cases: int = 30,
    minimum_full_stack_cases: int = 30,
) -> int:
    """Persist one governed decision artifact and return its enforcement exit code."""

    policy = V22PromotionPolicy(
        minimum_scoreline_case_count=minimum_scoreline_cases,
        minimum_full_stack_case_count=minimum_full_stack_cases,
    )
    result = evaluate_governed_v22_promotion(
        prediction_root,
        outcome_root,
        policy=policy,
    )
    payload = result.to_dict()
    payload["gate"] = "governed_v22_promotion"
    payload["prediction_root"] = str(prediction_root)
    payload["outcome_root"] = str(outcome_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return EXIT_CODES[result.decision]


def main() -> int:
    args = _parser().parse_args()
    return run_gate(
        args.prediction_root,
        args.outcome_root,
        args.output_path,
        minimum_scoreline_cases=args.minimum_scoreline_cases,
        minimum_full_stack_cases=args.minimum_full_stack_cases,
    )


if __name__ == "__main__":
    raise SystemExit(main())
