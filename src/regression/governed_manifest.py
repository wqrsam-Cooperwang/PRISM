"""Deterministic identity manifest for governed settled promotion cohorts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from src.regression.governed_dataset import load_governed_settled_ledger_pairs


@dataclass(frozen=True)
class GovernedCohortManifest:
    """Stable identity for the exact settled cases admitted to promotion evaluation."""

    case_count: int
    prediction_ids: tuple[str, ...]
    match_ids: tuple[str, ...]
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "case_count": self.case_count,
            "prediction_ids": list(self.prediction_ids),
            "match_ids": list(self.match_ids),
            "sha256": self.sha256,
        }


def build_governed_cohort_manifest(
    prediction_root: Path | str = "data/performance-ledger",
    outcome_root: Path | str = "data/outcome-ledger",
) -> GovernedCohortManifest:
    """Identify the exact contract-valid settled cohort with a canonical digest."""

    pairs = load_governed_settled_ledger_pairs(prediction_root, outcome_root)
    identities = sorted((snapshot.prediction_id, snapshot.match_id) for snapshot, _ in pairs)
    prediction_ids = tuple(prediction_id for prediction_id, _ in identities)
    match_ids = tuple(match_id for _, match_id in identities)
    _require_unique(prediction_ids, "prediction_id")
    _require_unique(match_ids, "match_id")
    canonical = json.dumps(identities, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return GovernedCohortManifest(
        case_count=len(identities),
        prediction_ids=prediction_ids,
        match_ids=match_ids,
        sha256=digest,
    )


def _require_unique(values: tuple[str, ...], field: str) -> None:
    duplicates = sorted(value for value in set(values) if values.count(value) > 1)
    if duplicates:
        joined = ", ".join(duplicates)
        raise ValueError(f"governed promotion cohort contains duplicate {field}: {joined}")
