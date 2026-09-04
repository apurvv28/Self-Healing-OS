"""Tests for RemediationEngine module."""

import tempfile
from pathlib import Path

from common.events import AegisDiagnosis, FailureType, RiskLevel
from remediation.audit import RemediationAuditLogger
from remediation.engine import RemediationEngine


def test_execute_remediation_auto_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_rem.db"
        audit = RemediationAuditLogger(db_path=db_path)
        engine = RemediationEngine(config_path="config/aegisos.yaml", audit_logger=audit)

        diag = AegisDiagnosis(
            event_id="evt-200",
            failure_type=FailureType.SERVICE_FAILURE,
            probable_root_cause="Service apache2 crashed",
            evidence=["Service state 'apache2.service': failed"],
            confidence_score=0.95,
            recommended_remediation="restart_service",
            risk_level=RiskLevel.LOW,
        )

        res = engine.execute_remediation(diag, operator="auto")
        assert res["success"] is True
        assert res["action"] == "restart_service"

        history = audit.get_audit_history(event_id="evt-200")
        assert len(history) == 1
        assert history[0]["action_name"] == "restart_service"


def test_execute_remediation_low_confidence_escalates():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_rem.db"
        audit = RemediationAuditLogger(db_path=db_path)
        engine = RemediationEngine(config_path="config/aegisos.yaml", audit_logger=audit)

        diag = AegisDiagnosis(
            event_id="evt-201",
            failure_type=FailureType.SERVICE_FAILURE,
            probable_root_cause="Uncertain service failure",
            evidence=["Service state 'apache2.service': failed"],
            confidence_score=0.60,  # Below 0.90 auto threshold
            recommended_remediation="restart_service",
            risk_level=RiskLevel.LOW,
        )

        res = engine.execute_remediation(diag, operator="auto")
        assert res["action"] == "escalate"
        assert "below threshold" in res["reason"]


def test_execute_remediation_high_risk_blocked():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_rem.db"
        audit = RemediationAuditLogger(db_path=db_path)
        engine = RemediationEngine(config_path="config/aegisos.yaml", audit_logger=audit)

        diag = AegisDiagnosis(
            event_id="evt-202",
            failure_type=FailureType.KERNEL_ERROR,
            probable_root_cause="Kernel panic",
            evidence=["Kernel panic - not syncing"],
            confidence_score=0.98,
            recommended_remediation="investigate_kernel",
            risk_level=RiskLevel.CRITICAL,
        )

        res = engine.execute_remediation(diag, operator="auto")
        assert res["action"] == "escalate"
        assert "disabled by policy" in res["reason"]


def test_max_retries_limit():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_rem.db"
        audit = RemediationAuditLogger(db_path=db_path)
        engine = RemediationEngine(config_path="config/aegisos.yaml", audit_logger=audit)

        diag = AegisDiagnosis(
            event_id="evt-203",
            failure_type=FailureType.SERVICE_FAILURE,
            probable_root_cause="Service apache2 crashed",
            evidence=["Service state 'apache2.service': failed"],
            confidence_score=0.95,
            recommended_remediation="restart_service",
            risk_level=RiskLevel.LOW,
        )

        # Run 3 retries
        engine.execute_remediation(diag, operator="auto")
        engine.execute_remediation(diag, operator="auto")
        engine.execute_remediation(diag, operator="auto")

        # 4th retry should be blocked by max retry gate
        res4 = engine.execute_remediation(diag, operator="auto")
        assert res4["action"] == "escalate"
        assert "Max retry limit" in res4["reason"]
