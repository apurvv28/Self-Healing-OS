"""Audit logging manager for AegisOS remediation executions."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Generator
from uuid import uuid4

logger = logging.getLogger(__name__)


class RemediationAuditLogger:
    """Records full audit trail of recovery actions in SQLite."""

    def __init__(self, db_path: str | Path = "data/aegisos.db") -> None:
        self.db_path = Path(db_path)
        if not self.db_path.is_absolute():
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
        """Initialize remediation audit database schema."""
        query = """
        CREATE TABLE IF NOT EXISTS remediation_audit (
            remediation_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            action_name TEXT NOT NULL,
            target TEXT NOT NULL,
            success INTEGER NOT NULL,
            operator TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_remediation_event_id ON remediation_audit(event_id);
        CREATE INDEX IF NOT EXISTS idx_remediation_timestamp ON remediation_audit(timestamp);
        """
        with self._connection() as conn:
            conn.executescript(query)
            conn.commit()

    def log_remediation(
        self,
        event_id: str,
        action_name: str,
        target: str,
        success: bool,
        operator: str = "auto",
        details: dict[str, Any] | None = None,
    ) -> str:
        """Save a remediation execution record to SQLite audit table."""
        remediation_id = str(uuid4())
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        details_str = json.dumps(details or {})

        query = """
        INSERT INTO remediation_audit (
            remediation_id, event_id, action_name, target, success, operator, timestamp, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self._connection() as conn:
            conn.execute(
                query,
                (
                    remediation_id,
                    event_id,
                    action_name,
                    target,
                    1 if success else 0,
                    operator,
                    ts,
                    details_str,
                ),
            )
            conn.commit()

        logger.info(
            "Logged remediation audit record %s: Action='%s', Target='%s', Success=%s",
            remediation_id,
            action_name,
            target,
            success,
        )
        return remediation_id

    def get_audit_history(
        self,
        limit: int = 50,
        event_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent remediation audit records."""
        query = "SELECT * FROM remediation_audit"
        params: list[Any] = []

        if event_id:
            query += " WHERE event_id = ?"
            params.append(event_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        records: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["success"] = bool(item["success"])
            try:
                item["details"] = json.loads(item["details"])
            except json.JSONDecodeError:
                pass
            records.append(item)

        return records
