"""Tests for MetricsTracker module."""

import tempfile
from pathlib import Path

from common.events import AegisEvent, EvidenceKind, FailureType, Severity
from detector.storage import IncidentStorage
from remediation.audit import RemediationAuditLogger
from verification.metrics import MetricsTracker


def test_metrics_tracker():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        storage = IncidentStorage(db_path=db_path)
        audit = RemediationAuditLogger(db_path=db_path)

        # Save sample incident
        event = AegisEvent.create(
            failure_type=FailureType.SERVICE_FAILURE,
            source="systemd",
            severity=Severity.CRITICAL,
            raw_evidence=[{"kind": EvidenceKind.SERVICE_STATE.value, "unit": "test.service"}],
        )
        storage.save_incident(event)

        # Save sample audit record
        audit.log_remediation(
            event_id=event.event_id,
            action_name="restart_service",
            target="test.service",
            success=True,
            operator="auto",
        )

        tracker = MetricsTracker(db_path=db_path)
        metrics = tracker.get_metrics_summary()

        assert metrics["total_incidents"] == 1
        assert metrics["total_remediations"] == 1
        assert metrics["successful_remediations"] == 1
        assert metrics["remediation_success_rate_pct"] == 100.0
        assert "SERVICE_FAILURE" in metrics["incidents_by_failure_type"]
        assert "restart_service" in metrics["actions_by_type"]
