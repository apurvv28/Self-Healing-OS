"""Tests for RCAEngine module."""

from common.events import AegisEvent, EvidenceKind, FailureType, RiskLevel, Severity
from rca.engine import RCAEngine


def test_rca_engine_diagnose_service_failure():
    engine = RCAEngine(config_path="config/aegisos.yaml")

    target_event = AegisEvent.create(
        failure_type=FailureType.SERVICE_FAILURE,
        source="systemd",
        severity=Severity.CRITICAL,
        raw_evidence=[
            {"kind": EvidenceKind.SERVICE_STATE.value, "unit": "nginx.service", "active_state": "failed", "restarts": 3}
        ],
        affected_unit="nginx.service",
    )

    diagnosis = engine.diagnose(target_event)

    assert diagnosis.event_id == target_event.event_id
    assert diagnosis.failure_type == FailureType.SERVICE_FAILURE
    assert "nginx.service" in diagnosis.probable_root_cause
    assert diagnosis.recommended_remediation == "restart_service"
    assert diagnosis.risk_level == RiskLevel.LOW
    assert diagnosis.confidence_score >= 0.70


def test_rca_engine_diagnose_memory_exhaustion():
    engine = RCAEngine(config_path="config/aegisos.yaml")

    target_event = AegisEvent.create(
        failure_type=FailureType.MEMORY_EXHAUSTION,
        source="resource_monitor",
        severity=Severity.CRITICAL,
        raw_evidence=[
            {"kind": EvidenceKind.METRIC.value, "metric_name": "memory_utilization", "value": 98.0},
            {"kind": EvidenceKind.LOG_LINE.value, "message": "Out of memory: Kill process 999 (mysqld)"},
        ],
        affected_process="mysqld",
    )

    diagnosis = engine.diagnose(target_event)

    assert diagnosis.failure_type == FailureType.MEMORY_EXHAUSTION
    assert diagnosis.recommended_remediation == "cleanup_temp_files"
    assert diagnosis.risk_level == RiskLevel.MEDIUM
    assert len(diagnosis.evidence) >= 1
