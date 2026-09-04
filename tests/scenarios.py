"""Mock failure telemetry generators for Phase 3 controlled test scenarios."""

from __future__ import annotations

from typing import Any


def generate_mock_service_failure_telemetry(unit_name: str = "apache2.service") -> dict[str, Any]:
    """Generate telemetry for a failed systemd service."""
    return {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": 15.0},
            "memory": {"used_percent": 45.0},
            "disk": {"/": {"percent": 50.0}},
        },
        "top_processes": [],
        "monitored_services": [],
        "failed_services": [
            {
                "unit": unit_name,
                "active_state": "failed",
                "sub_state": "failed",
                "load_state": "loaded",
                "main_pid": 0,
                "restarts": 3,
                "exec_status": "1/FAILURE",
                "exec_code": "exited",
            }
        ],
        "journal_logs": [
            {"MESSAGE": f"Job for {unit_name} failed because the control process exited with error code."}
        ],
        "dmesg_logs": [],
    }


def generate_mock_cpu_overload_telemetry(cpu_percent: float = 95.0) -> dict[str, Any]:
    """Generate telemetry for severe CPU overload."""
    return {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": cpu_percent},
            "memory": {"used_percent": 40.0},
            "disk": {"/": {"percent": 50.0}},
        },
        "top_processes": [
            {"pid": 4321, "name": "stress-ng-cpu", "cpu_percent": 95.0, "memory_percent": 1.2}
        ],
        "monitored_services": [],
        "failed_services": [],
        "journal_logs": [],
        "dmesg_logs": [],
    }


def generate_mock_memory_exhaustion_telemetry(mem_percent: float = 98.0) -> dict[str, Any]:
    """Generate telemetry for severe memory pressure."""
    return {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": 25.0},
            "memory": {"used_percent": mem_percent},
            "disk": {"/": {"percent": 50.0}},
        },
        "top_processes": [
            {"pid": 8765, "name": "memory_hog", "cpu_percent": 10.0, "memory_percent": 85.0}
        ],
        "monitored_services": [],
        "failed_services": [],
        "journal_logs": [],
        "dmesg_logs": [],
    }


def generate_mock_disk_exhaustion_telemetry(path: str = "/tmp", percent: float = 98.5) -> dict[str, Any]:
    """Generate telemetry for disk full condition."""
    return {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": 10.0},
            "memory": {"used_percent": 30.0},
            "disk": {path: {"percent": percent}},
        },
        "top_processes": [],
        "monitored_services": [],
        "failed_services": [],
        "journal_logs": [],
        "dmesg_logs": [],
    }


def generate_mock_kernel_oom_telemetry() -> dict[str, Any]:
    """Generate telemetry containing kernel Out Of Memory (OOM) killer event."""
    return {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": 30.0},
            "memory": {"used_percent": 96.0},
            "disk": {"/": {"percent": 40.0}},
        },
        "top_processes": [],
        "monitored_services": [],
        "failed_services": [],
        "journal_logs": [],
        "dmesg_logs": [
            {"message": "[ 1234.567] Out of memory: Kill process 9999 (mysqld) score 850 or sacrifice child"}
        ],
    }


def generate_mock_kernel_segfault_telemetry() -> dict[str, Any]:
    """Generate telemetry containing segmentation fault crash in dmesg."""
    return {
        "timestamp": "2026-09-04T22:00:00Z",
        "system_metrics": {
            "cpu": {"total_percent": 12.0},
            "memory": {"used_percent": 25.0},
            "disk": {"/": {"percent": 30.0}},
        },
        "top_processes": [],
        "monitored_services": [],
        "failed_services": [],
        "journal_logs": [],
        "dmesg_logs": [
            {"message": "[ 2345.678] app_worker[4433]: segfault at 0 ip 00007f9a sp 00007fff error 4 in app_worker"}
        ],
    }
