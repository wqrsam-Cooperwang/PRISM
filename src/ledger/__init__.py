"""Public autonomous performance-ledger API for PRISM.

This module re-exports ledger APIs, including the newly added prediction
archive functionality, while preserving the original public surface.
"""

from src.ledger.accepted import AcceptedPredictionResult, persist_accepted_formal_prediction
from src.ledger.cohort import load_formal_forward_testing_cohort
from src.ledger.formal import FormalPredictionResult, run_formal_acquired_prediction_path
from src.ledger.formal_contract import (
    validate_formal_prediction_snapshot,
    validate_persisted_formal_snapshot,
)
from src.ledger.models import LEDGER_SCHEMA_VERSION, PredictionLedgerSnapshot
from src.ledger.outcomes import FileSystemOutcomeLedgerStore, MatchOutcome
from src.ledger.shadow import V22_SHADOW_SCHEMA_VERSION, build_v22_shadow_payload
from src.ledger.snapshot import build_prediction_snapshot
from src.ledger.store import FileSystemPredictionLedgerStore, PredictionLedgerStore

# Archive exports
from src.ledger.archive import (
    ARCHIVE_SCHEMA_VERSION,
    PredictionArchiveRecord,
    FileSystemPredictionArchiveStore,
    build_archive_from_mapping,
)

__all__ = [
    "LEDGER_SCHEMA_VERSION",
    "V22_SHADOW_SCHEMA_VERSION",
    "AcceptedPredictionResult",
    "FileSystemOutcomeLedgerStore",
    "FileSystemPredictionLedgerStore",
    "FormalPredictionResult",
    "MatchOutcome",
    "PredictionLedgerSnapshot",
    "PredictionLedgerStore",
    "build_prediction_snapshot",
    "build_v22_shadow_payload",
    "load_formal_forward_testing_cohort",
    "persist_accepted_formal_prediction",
    "run_formal_acquired_prediction_path",
    "validate_formal_prediction_snapshot",
    "validate_persisted_formal_snapshot",
    # archive API
    "ARCHIVE_SCHEMA_VERSION",
    "PredictionArchiveRecord",
    "FileSystemPredictionArchiveStore",
    "build_archive_from_mapping",
]
