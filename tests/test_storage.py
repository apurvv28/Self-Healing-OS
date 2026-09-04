"""Tests for IncidentStorage SQLite persistence."""

import tempfile
from pathlib import Path

from common.events import AegisEvent, EvidenceKind, FailureType, Severity
from detector.storage import IncidentStorage


def test_storage_save_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_aegisos.db"
        storage = IncidentStorage(db_path=db_path)

        assert storage.count_incidents() == 0

        event = AegisEvent.create(
            failure_type=FailureType.SERVICE_FAILURE,
            source="systemd",
            severity=Severity.CRITICAL,
            raw_evidence=[{"kind": EvidenceKind.SERVICE_STATE.value, "unit": "test.service"}],
            affected_unit="test.service",
            tags=["test"],
        )

        event_id = storage.save_incident(event)
        assert event_id == event.event_id
        assert storage.count_incidents() == 1

        recent = storage.get_recent_incidents(limit=10)
        assert len(recent) == 1
        assert recent[0]["event_id"] == event.event_id
        assert recent[0]["failure_type"] == "SERVICE_FAILURE"
        assert recent[0]["affected_unit"] == "test.service"
        assert recent[0]["tags"] == ["test"]

        fetched = storage.get_incident_by_id(event.event_id)
        assert fetched is not None
        assert fetched["event_id"] == event.event_id
