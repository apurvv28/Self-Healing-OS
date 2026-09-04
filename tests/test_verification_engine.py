"""Tests for VerificationEngine module."""

from common.events import AegisDiagnosis, FailureType, RiskLevel
from verification.engine import VerificationEngine


def test_verification_engine_verify_recovery():
    engine = VerificationEngine(config_path="config/aegisos.yaml")

    diag = AegisDiagnosis(
        event_id="evt-300",
        failure_type=FailureType.SERVICE_FAILURE,
        probable_root_cause="Service crashed",
        evidence=["Service apache2 failed"],
        confidence_score=0.95,
        recommended_remediation="restart_service",
        risk_level=RiskLevel.LOW,
    )

    rem_result = {
        "action": "restart_service",
        "target": "apache2.service",
        "success": True,
    }

    telemetry = {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": 10.0},
            "memory": {"used_percent": 30.0},
            "disk": {"/": {"percent": 40.0}},
        },
        "journal_logs": [],
        "dmesg_logs": [],
    }

    v_record = engine.verify_recovery(diag, rem_result, telemetry, initial_timestamp="2026-09-04T22:00:00Z")
    assert v_record["recovered"] is True
    assert v_record["status"] == "RECOVERED"
    assert v_record["mttr_seconds"] >= 0.0
