"""SQLite storage manager for AegisOS incidents."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from common.events import AegisEvent

logger = logging.getLogger(__name__)


class IncidentStorage:
    """Manages persistence of normalized failure incidents in SQLite."""

    def __init__(self, db_path: str | Path = "data/aegisos.db") -> None:
        self.db_path = Path(db_path)
        if not self.db_path.is_absolute():
            # Place data relative to project root if relative
            self.db_path = Path.cwd() / self.db_path

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema if it doesn't exist."""
        query = """
        CREATE TABLE IF NOT EXISTS incidents (
            event_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            failure_type TEXT NOT NULL,
            source TEXT NOT NULL,
            severity TEXT NOT NULL,
            affected_unit TEXT,
            affected_process TEXT,
            raw_evidence TEXT NOT NULL,
            tags TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp);
        CREATE INDEX IF NOT EXISTS idx_incidents_failure_type ON incidents(failure_type);
        """
        with self._connection() as conn:
            conn.executescript(query)
            conn.commit()

    def save_incident(self, event: AegisEvent) -> str:
        """Save an AegisEvent incident to SQLite."""
        query = """
        INSERT INTO incidents (
            event_id, timestamp, failure_type, source, severity,
            affected_unit, affected_process, raw_evidence, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        raw_evidence_str = json.dumps(event.raw_evidence)
        tags_str = json.dumps(event.tags)

        with self._connection() as conn:
            conn.execute(
                query,
                (
                    event.event_id,
                    event.timestamp,
                    event.failure_type.value if hasattr(event.failure_type, "value") else str(event.failure_type),
                    event.source,
                    event.severity.value if hasattr(event.severity, "value") else str(event.severity),
                    event.affected_unit,
                    event.affected_process,
                    raw_evidence_str,
                    tags_str,
                ),
            )
            conn.commit()

        logger.info("Saved incident %s (%s)", event.event_id, event.failure_type)
        return event.event_id

    def get_recent_incidents(
        self,
        limit: int = 50,
        failure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent incidents sorted by timestamp descending."""
        query = "SELECT * FROM incidents"
        params: list[Any] = []

        if failure_type:
            query += " WHERE failure_type = ?"
            params.append(failure_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        incidents: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            try:
                item["raw_evidence"] = json.loads(item["raw_evidence"])
            except json.JSONDecodeError:
                pass
            try:
                item["tags"] = json.loads(item["tags"])
            except json.JSONDecodeError:
                pass
            incidents.append(item)

        return incidents

    def get_incident_by_id(self, event_id: str) -> dict[str, Any] | None:
        """Fetch a single incident by event_id."""
        query = "SELECT * FROM incidents WHERE event_id = ?"
        with self._connection() as conn:
            cursor = conn.execute(query, (event_id,))
            row = cursor.fetchone()

        if not row:
            return None

        item = dict(row)
        try:
            item["raw_evidence"] = json.loads(item["raw_evidence"])
        except json.JSONDecodeError:
            pass
        try:
            item["tags"] = json.loads(item["tags"])
        except json.JSONDecodeError:
            pass
        return item

    def count_incidents(self) -> int:
        """Return total number of recorded incidents."""
        with self._connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM incidents")
            return cursor.fetchone()[0]
