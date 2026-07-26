"""Build immutable pre-match performance-ledger snapshots."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from src.collection.readiness import CollectionReadinessGateResult
from src.features.models import FeatureVector
from src.intelligence.models import Observation
from src.ledger.models import PredictionLedgerSnapshot
from src.report.models import PredictionReport


def _observation_dict(item: Observation) -> dict[str, Any]:
    return {
        "observation_id": item.observation_id,
        "category": item.category.value,
        "claim_key": item.claim_key,
        "value": item.value,
        "source": {
            "source_id": item.source.source_id,
            "source_type": item.source.source_type.value,
            "uri": item.source.uri,
            "publisher": item.source.publisher,
        },
        "observed_at": item.observed_at.isoformat(),
        "collected_at": item.collected_at.isoformat(),
        "subject": item.subject,
        "confidence": item.confidence,
        "notes": item.notes,
    }


def _gate_dict(gate: CollectionReadinessGateResult) -> dict[str, Any]:
    return {
        "decision": gate.decision.value,
        "covered_core_categories": [item.value for item in gate.covered_core_categories],
        "missing_core_categories": [item.value for item in gate.missing_core_categories],
        "covered_optional_categories": [item.value for item in gate.covered_optional_categories],
        "source_ids": list(gate.source_ids),
        "source_types": list(gate.source_types),
        "elo_baseline_available": gate.elo_baseline_available,
        "market_baseline_available": gate.market_baseline_available,
        "reasons": list(gate.reasons),
    }


def _feature_dict(features: FeatureVector) -> dict[str, Any]:
    return {
        "schema_version": features.schema_version,
        "values": dict(features.values),
        "missing_features": list(features.missing_features),
        "intelligence_fingerprint": features.intelligence_fingerprint,
        "readiness": features.readiness.value,
        "fingerprint": features.fingerprint,
    }


def _prediction_id(report: PredictionReport) -> str:
    identity = "|".join(
        (
            report.match.match_id,
            report.provenance.session_id,
            report.provenance.git_commit or "",
            report.match.kickoff.isoformat(),
        )
    )
    return f"pred-{sha256(identity.encode()).hexdigest()[:20]}"


def build_prediction_snapshot(
    report: PredictionReport,
    observations: tuple[Observation, ...],
    gate: CollectionReadinessGateResult,
    features: FeatureVector,
    *,
    frozen_at,
) -> PredictionLedgerSnapshot:
    """Project one governed production result into a durable frozen snapshot."""

    if frozen_at.tzinfo is None or frozen_at.utcoffset() is None:
        raise ValueError("frozen_at must be timezone-aware")
    if frozen_at >= report.match.kickoff:
        raise ValueError("A pre-match prediction snapshot must be frozen before kickoff")

    payload = {
        "report": report.to_dict(),
        "observations": [_observation_dict(item) for item in observations],
        "collection_gate": _gate_dict(gate),
        "features": _feature_dict(features),
    }
    return PredictionLedgerSnapshot(
        prediction_id=_prediction_id(report),
        match_id=report.match.match_id,
        frozen_at=frozen_at,
        payload=payload,
    )
