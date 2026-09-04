"""Tests for HealthChecker module."""

from verification.checker import HealthChecker


def test_health_checker_service():
    checker = HealthChecker()
    res = checker.check_service_health("nginx.service")
    assert res["healthy"] is True
    assert "unit" in res


def test_health_checker_resource():
    checker = HealthChecker()
    metrics = {
        "cpu": {"total_percent": 25.0},
        "memory": {"used_percent": 50.0},
        "disk": {"/": {"percent": 60.0}},
    }
    thresholds = {
        "thresholds": {
            "cpu": {"critical_percent": 90},
            "memory": {"critical_percent": 95},
            "disk": {"critical_percent": 95},
        }
    }
    res = checker.check_resource_health(metrics, thresholds)
    assert res["healthy"] is True
    assert res["cpu_healthy"] is True
    assert res["mem_healthy"] is True


def test_health_checker_log():
    checker = HealthChecker()
    logs = [{"message": "System running smoothly", "priority": "6"}]
    res = checker.check_log_health(logs)
    assert res["healthy"] is True
    assert res["error_count"] == 0
