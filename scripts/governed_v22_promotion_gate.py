"""Run the governed PRISM V2.2 promotion gate from formal ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from src.regression import (
    V22_PROMOTION_POLICY_VERSION,
    V22PromotionPolicy,
    evaluate_governed_v22_promotion,
)

GOVERNED_V22_PROMOTION_ARTIFACT_VERSION = "1.0.0"
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


def _ledger_fingerprint(root: Path) -> dict[str, object]:
    """Return deterministic provenance for the exact files consumed under one ledger root."""

    digest = hashlib.sha256()
    file_count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative_path = path.relative_to(root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
        file_count += 1
    return {
        "root": str(root),
        "file_count": file_count,
        "sha256": digest.hexdigest(),
    }


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
    exit_code = EXIT_CODES[result.decision]
    payload = result.to_dict()
    payload.update(
        {
            "artifact_version": GOVERNED_V22_PROMOTION_ARTIFACT_VERSION,
            "gate": "governed_v22_promotion",
            "policy": {
                "version": V22_PROMOTION_POLICY_VERSION,
                "minimum_scoreline_case_count": policy.minimum_scoreline_case_count,
                "minimum_full_stack_case_count": policy.minimum_full_stack_case_count,
                "require_full_stack_validation": policy.require_full_stack_validation,
            },
            "provenance": {
                "prediction_ledger": _ledger_fingerprint(prediction_root),
                "outcome_ledger": _ledger_fingerprint(outcome_root),
            },
            "release_gate": {
                "allowed": result.decision == "promote",
                "exit_code": exit_code,
            },
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True))
    return exit_code


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
