"""Small durable store for Phase 1 scenario runs.

SQLite is deliberate for the walking skeleton. The repository boundary lets a
later phase exchange it for PostgreSQL without changing the API contract.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from petravigil.models import CanonicalScenarioResponse, ScenarioRunRecord


class ScenarioRunRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scenario_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def create(self, scenario: CanonicalScenarioResponse) -> ScenarioRunRecord:
        record = ScenarioRunRecord(
            run_id=f"RUN-{str(uuid4()).upper()}",
            status="COMPLETED",
            created_at=datetime.now(timezone.utc),
            scenario=scenario,
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO scenario_runs (run_id, created_at, payload) VALUES (?, ?, ?)",
                (
                    record.run_id,
                    record.created_at.isoformat(),
                    json.dumps(record.model_dump(mode="json")),
                ),
            )
        return record

    def get(self, run_id: str) -> ScenarioRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM scenario_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return self._deserialize(row)

    def latest(self) -> ScenarioRunRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM scenario_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        return self._deserialize(row)

    @staticmethod
    def _deserialize(row: sqlite3.Row | None) -> ScenarioRunRecord | None:
        if row is None:
            return None
        return ScenarioRunRecord.model_validate_json(row["payload"])
