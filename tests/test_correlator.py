"""Tests for TemporalCorrelator module."""

from common.events import AegisEvent, EvidenceKind, FailureType, Severity
from rca.correlator import TemporalCorrelator


def test_correlate_events_within_window():
    correlator = TemporalCorrelator(default_window_seconds=30)

    e1 = AegisEvent.create(
        failure_type=FailureType.SERVICE_FAILURE,
        source="systemd",
        severity=Severity.CRITICAL,
        raw_evidence=[{"kind": EvidenceKind.SERVICE_STATE.value, "unit": "nginx"}],
        affected_unit="nginx",
    )

    # Event 10 seconds later
    e2 = AegisEvent.create(
        failure_type=FailureType.MEMORY_EXHAUSTION,
        source="resource",
        severity=Severity.WARNING,
        raw_evidence=[{"kind": EvidenceKind.METRIC.value, "metric_name": "memory_utilization", "value": 96.0}],
    )

    correlated = correlator.correlate_events(e1, [e1, e2], window_seconds=30)
    assert len(correlated) == 1
    assert correlated[0].event_id == e2.event_id


def test_bundle_evidence():
    correlator = TemporalCorrelator()

    e1 = AegisEvent.create(
        failure_type=FailureType.SERVICE_FAILURE,
        source="systemd",
        severity=Severity.CRITICAL,
        raw_evidence=[{"kind": EvidenceKind.SERVICE_STATE.value, "unit": "nginx", "active_state": "failed"}],
    )
    e2 = AegisEvent.create(
        failure_type=FailureType.MEMORY_EXHAUSTION,
        source="resource",
        severity=Severity.WARNING,
        raw_evidence=[{"kind": EvidenceKind.METRIC.value, "metric_name": "memory_utilization", "value": 96.0}],
    )

    bundle = correlator.bundle_evidence(e1, [e2])
    assert bundle["kind_count"] == 2
    assert len(bundle["bullets"]) >= 2
    assert "nginx" in bundle["bullets"][0] or "nginx" in bundle["bullets"][1]
