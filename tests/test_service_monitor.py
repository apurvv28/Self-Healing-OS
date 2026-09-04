"""Tests for ServiceMonitor module."""

from unittest.mock import patch

from monitor.service_monitor import ServiceMonitor


def test_service_monitor_initialization():
    monitor = ServiceMonitor(monitored_units=["ssh", "nginx"])
    assert monitor.monitored_units == ["ssh", "nginx"]


@patch("shutil.which")
def test_unit_status_when_systemctl_missing(mock_which):
    mock_which.return_value = None
    monitor = ServiceMonitor()
    status = monitor.get_unit_status("nginx.service")

    assert status["unit"] == "nginx.service"
    assert status["active_state"] == "unknown"
    assert status["systemctl_available"] is False
    assert monitor.list_failed_units() == []


def test_normalize_service_evidence():
    monitor = ServiceMonitor()
    status = {
        "unit": "cron.service",
        "active_state": "active",
        "sub_state": "running",
        "load_state": "loaded",
        "main_pid": 123,
        "restarts": 0,
    }
    evidence = monitor.normalize_service_evidence(status)
    assert evidence["kind"] == "service_state"
    assert evidence["unit"] == "cron.service"
    assert evidence["active_state"] == "active"
    assert evidence["is_failed"] is False
