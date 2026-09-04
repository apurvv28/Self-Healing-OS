"""Tests for RemediationAuditLogger module."""

import tempfile
from pathlib import Path

from remediation.audit import RemediationAuditLogger


def test_audit_log_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_audit.db"
        audit = RemediationAuditLogger(db_path=db_path)

        rem_id = audit.log_remediation(
            event_id="evt-100",
            action_name="restart_service",
            target="nginx.service",
            success=True,
            operator="auto",
            details={"restarts": 1},
        )

        assert isinstance(rem_id, str)

        history = audit.get_audit_history(event_id="evt-100")
        assert len(history) == 1
        record = history[0]
        assert record["remediation_id"] == rem_id
        assert record["event_id"] == "evt-100"
        assert record["action_name"] == "restart_service"
        assert record["success"] is True
        assert record["details"]["restarts"] == 1
