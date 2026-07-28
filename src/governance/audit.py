"""Simple audit logger and record for governance/audit.

In production this should persist to an audit store; for Phase C we provide a
lightweight in-memory logger suitable for testing and demonstration.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class AuditRecord:
    event_type: str
    message: str
    timestamp: str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata: Dict[str, Any] = None


class AuditLogger:
    def __init__(self) -> None:
        self.records: List[AuditRecord] = []

    def record(self, rec: AuditRecord) -> None:
        self.records.append(rec)
