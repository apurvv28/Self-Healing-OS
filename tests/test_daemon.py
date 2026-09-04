"""Tests for MonitoringDaemon module."""

from monitor.daemon import MonitoringDaemon


def test_monitoring_daemon_initialization():
    daemon = MonitoringDaemon(config_path="config/aegisos.yaml")
    assert daemon.poll_interval == 10
    assert daemon.journal_lookback == 5


def test_collect_telemetry_snapshot():
    daemon = MonitoringDaemon(config_path="config/aegisos.yaml")
    snapshot = daemon.collect_telemetry_snapshot()

    assert "timestamp" in snapshot
    assert "system_metrics" in snapshot
    assert "top_processes" in snapshot
    assert "failed_services" in snapshot
    assert "threshold_alerts" in snapshot


def test_check_thresholds_cpu_alert():
    daemon = MonitoringDaemon(config_path="config/aegisos.yaml")
    metrics = {
        "cpu": {"total_percent": 95.0},
        "memory": {"used_percent": 50.0},
        "disk": {},
    }
    alerts = daemon.check_thresholds(metrics, [])
    assert len(alerts) == 1
    assert alerts[0]["type"] == "CPU_OVERLOAD"
    assert alerts[0]["severity"] == "CRITICAL"


def test_check_thresholds_failed_service_alert():
    daemon = MonitoringDaemon(config_path="config/aegisos.yaml")
    metrics = {
        "cpu": {"total_percent": 10.0},
        "memory": {"used_percent": 20.0},
        "disk": {},
    }
    failed_svcs = [{"unit": "crashed.service", "active_state": "failed"}]
    alerts = daemon.check_thresholds(metrics, failed_svcs)

    assert len(alerts) == 1
    assert alerts[0]["type"] == "SERVICE_FAILURE"
    assert alerts[0]["unit"] == "crashed.service"


def test_daemon_once_execution():
    daemon = MonitoringDaemon(config_path="config/aegisos.yaml")
    daemon.run(once=True)
