"""Tests for rule-based failure detectors."""

from common.events import FailureType, Severity
from detector.rules import KernelDetector, ResourceDetector, ServiceDetector
from tests.scenarios import (
    generate_mock_cpu_overload_telemetry,
    generate_mock_disk_exhaustion_telemetry,
    generate_mock_kernel_oom_telemetry,
    generate_mock_kernel_segfault_telemetry,
    generate_mock_memory_exhaustion_telemetry,
    generate_mock_service_failure_telemetry,
)


def test_service_detector_failed_service():
    detector = ServiceDetector()
    telemetry = generate_mock_service_failure_telemetry(unit_name="nginx.service")
    events = detector.detect(telemetry)

    assert len(events) == 1
    event = events[0]
    assert event.failure_type == FailureType.SERVICE_FAILURE
    assert event.severity == Severity.CRITICAL
    assert event.affected_unit == "nginx.service"


def test_resource_detector_cpu_and_memory():
    detector = ResourceDetector()

    # CPU Test
    cpu_telemetry = generate_mock_cpu_overload_telemetry(cpu_percent=95.0)
    cpu_events = detector.detect(cpu_telemetry, thresholds={"cpu": {"critical_percent": 90, "warning_percent": 80}})
    assert len(cpu_events) == 1
    assert cpu_events[0].failure_type == FailureType.CPU_OVERLOAD
    assert cpu_events[0].severity == Severity.CRITICAL
    assert cpu_events[0].affected_process == "stress-ng-cpu"

    # Memory Test
    mem_telemetry = generate_mock_memory_exhaustion_telemetry(mem_percent=99.0)
    mem_events = detector.detect(mem_telemetry, thresholds={"memory": {"critical_percent": 95, "warning_percent": 85}})
    assert len(mem_events) == 1
    assert mem_events[0].failure_type == FailureType.MEMORY_EXHAUSTION
    assert mem_events[0].severity == Severity.CRITICAL
    assert mem_events[0].affected_process == "memory_hog"


def test_resource_detector_disk_exhaustion():
    detector = ResourceDetector()
    disk_telemetry = generate_mock_disk_exhaustion_telemetry(path="/tmp", percent=99.0)
    events = detector.detect(disk_telemetry, thresholds={"disk": {"critical_percent": 95, "warning_percent": 85}})

    assert len(events) == 1
    assert events[0].failure_type == FailureType.DISK_EXHAUSTION
    assert events[0].affected_unit == "/tmp"


def test_kernel_detector_oom_and_segfault():
    detector = KernelDetector()

    # OOM Test
    oom_telemetry = generate_mock_kernel_oom_telemetry()
    oom_events = detector.detect(oom_telemetry)
    assert len(oom_events) == 1
    assert oom_events[0].failure_type == FailureType.MEMORY_EXHAUSTION

    # Segfault Test
    seg_telemetry = generate_mock_kernel_segfault_telemetry()
    seg_events = detector.detect(seg_telemetry)
    assert len(seg_events) == 1
    assert seg_events[0].failure_type == FailureType.KERNEL_ERROR
