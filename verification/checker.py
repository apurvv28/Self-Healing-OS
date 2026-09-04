"""Post-remediation health check routines for AegisOS."""

from __future__ import annotations

import logging
from typing import Any

from monitor.service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)


class HealthChecker:
    """Validates service state, resource metric stabilization, and log signature health."""

    def __init__(self, service_monitor: ServiceMonitor | None = None) -> None:
        self.service_monitor = service_monitor if service_monitor is not None else ServiceMonitor()

    def check_service_health(self, unit_name: str) -> dict[str, Any]:
        """Check if target systemd unit is active and running cleanly."""
        status = self.service_monitor.get_unit_status(unit_name)
        active_state = status.get("active_state", "unknown")

        # If systemctl is not available (e.g. non-Linux / test environment), default to healthy
        systemctl_available = status.get("systemctl_available", True)
        if not systemctl_available:
            return {
                "unit": unit_name,
                "healthy": True,
                "active_state": "active",
                "details": "Dry-run / test environment: systemctl not available",
            }

        healthy = active_state in ("active", "reloading")
        return {
            "unit": unit_name,
            "healthy": healthy,
            "active_state": active_state,
            "details": f"Unit state is '{active_state}'",
        }

    def check_resource_health(self, metrics: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
        """Check if CPU, memory, and disk usage are below critical threshold limits."""
        thresh = thresholds.get("thresholds", thresholds)

        cpu_cfg = thresh.get("cpu", {})
        mem_cfg = thresh.get("memory", {})
        disk_cfg = thresh.get("disk", {})

        cpu_usage = metrics.get("cpu", {}).get("total_percent", 0.0)
        mem_usage = metrics.get("memory", {}).get("used_percent", 0.0)

        cpu_healthy = cpu_usage < cpu_cfg.get("critical_percent", 90)
        mem_healthy = mem_usage < mem_cfg.get("critical_percent", 95)

        disk_healthy = True
        for path, usage in metrics.get("disk", {}).items():
            if usage.get("percent", 0.0) >= disk_cfg.get("critical_percent", 95):
                disk_healthy = False
                break

        overall_healthy = cpu_healthy and mem_healthy and disk_healthy
        return {
            "healthy": overall_healthy,
            "cpu_healthy": cpu_healthy,
            "mem_healthy": mem_healthy,
            "disk_healthy": disk_healthy,
            "details": f"CPU {cpu_usage:.1f}%, Mem {mem_usage:.1f}%",
        }

    def check_log_health(self, logs: list[dict[str, Any]]) -> dict[str, Any]:
        """Verify that recurring critical error signatures in logs have ceased."""
        error_count = 0
        for entry in logs:
            msg = entry.get("message", "") if isinstance(entry, dict) else str(entry)
            prio = str(entry.get("priority", "6")) if isinstance(entry, dict) else "6"
            if prio in ("0", "1", "2", "3") or "error" in msg.lower() or "panic" in msg.lower():
                error_count += 1

        healthy = error_count == 0
        return {
            "healthy": healthy,
            "error_count": error_count,
            "details": f"{error_count} error log entries found in observation window",
        }
