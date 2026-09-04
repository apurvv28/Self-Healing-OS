"""Tests for normalized event and diagnosis structures."""

from common.events import (
    AegisDiagnosis,
    AegisEvent,
    FailureType,
    RiskLevel,
    Severity,
)


def test_aegis_event_create_and_to_dict():
    event = AegisEvent.create(
        failure_type=FailureType.SERVICE_FAILURE,
        source="systemctl",
        severity=Severity.CRITICAL,
        raw_evidence=[{"kind": "service_state", "data": {"unit": "nginx.service"}}],
        affected_unit="nginx.service",
    )
    data = event.to_dict()
    assert data["failure_type"] == "SERVICE_FAILURE"
    assert data["severity"] == "CRITICAL"
    assert data["affected_unit"] == "nginx.service"
    assert len(data["event_id"]) == 36
    assert data["timestamp"].endswith("Z")


def test_aegis_event_requires_evidence():
    try:
        AegisEvent.create(
            failure_type=FailureType.UNKNOWN_FAILURE,
            source="test",
            severity=Severity.INFO,
            raw_evidence=[],
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_aegis_diagnosis_to_dict():
    diagnosis = AegisDiagnosis(
        event_id="abc-123",
        failure_type=FailureType.MEMORY_EXHAUSTION,
        probable_root_cause="OOM killer terminated java process",
        evidence=["Memory > 95%", "OOM in dmesg"],
        confidence_score=0.94,
        recommended_remediation="restart_service",
        risk_level=RiskLevel.MEDIUM,
    )
    data = diagnosis.to_dict()
    assert data["confidence_score"] == 0.94
    assert data["risk_level"] == "MEDIUM"
