"""Append-only, local-only approval records for Phase 6."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from petravigil.models import ApprovalCreateRequest, ApprovalRecord


class ApprovalRepository:
    """Stores human decisions without attempting external execution."""

    def __init__(self, database_path: Path) -> None:
        self.path = database_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS approval_records "
                "(approval_id TEXT PRIMARY KEY, recommendation_id TEXT NOT NULL, decided_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, recommendation_id: str, request: ApprovalCreateRequest) -> ApprovalRecord:
        record = ApprovalRecord(
            approval_id=f"AP-{str(uuid4()).upper()}",
            recommendation_id=recommendation_id,
            decision=request.decision,
            decided_by=request.decided_by,
            decided_at=datetime.now(timezone.utc),
            justification=request.justification,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO approval_records (approval_id, recommendation_id, decided_at, payload) VALUES (?, ?, ?, ?)",
                (record.approval_id, record.recommendation_id, record.decided_at.isoformat(), json.dumps(record.model_dump(mode="json"))),
            )
        return record

    def latest(self, limit: int = 12) -> list[ApprovalRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM approval_records ORDER BY decided_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [ApprovalRecord.model_validate_json(row["payload"]) for row in rows]
