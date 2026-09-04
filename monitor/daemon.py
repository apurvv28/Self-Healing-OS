"""Main monitoring daemon (`aegis-monitor`) for AegisOS.

Orchestrates real-time telemetry collection across logs, services, and resources,
evaluating metrics against system thresholds and streaming aggregated events.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from datetime import UTC, datetime
from typing import Any

from common.config_loader import load_config
from common.events import EvidenceKind, FailureType, Severity
from common.logging_config import setup_logging
from monitor.log_monitor import LogMonitor
from monitor.resource_monitor import ResourceMonitor
from monitor.service_monitor import ServiceMonitor

logger = logging.getLogger(__name__)


class MonitoringDaemon:
    """Daemon that continuously collects OS health telemetry and checks threshold alerts."""

    def __init__(self, config_path: str = "config/aegisos.yaml") -> None:
        self.config = load_config(config_path)
        self._running = False

        mon_cfg = self.config.get("monitoring", {})
        self.poll_interval = mon_cfg.get("poll_interval_seconds", 10)
        self.journal_lookback = mon_cfg.get("journal_lookback_minutes", 5)

        thresh_cfg = self.config.get("thresholds", {}).get("thresholds", {})
        self.thresholds = thresh_cfg

        disk_paths = self.thresholds.get("disk", {}).get("paths", ["/"])
        monitored_units = mon_cfg.get("monitored_units", ["ssh", "cron", "systemd-journald"])

        self.log_monitor = LogMonitor(journal_lookback_minutes=self.journal_lookback)
        self.service_monitor = ServiceMonitor(monitored_units=monitored_units)
        self.resource_monitor = ResourceMonitor(disk_paths=disk_paths)

    def collect_telemetry_snapshot(self) -> dict[str, Any]:
        """Collect a unified health telemetry snapshot from all monitors."""
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        metrics = self.resource_monitor.collect_system_metrics()
        top_procs = self.resource_monitor.collect_top_processes(limit=10)

        service_states = self.service_monitor.check_all_monitored_units()
        failed_services = self.service_monitor.list_failed_units()

        journal_logs = self.log_monitor.fetch_journal_logs(since_minutes=self.journal_lookback)
        dmesg_logs = self.log_monitor.fetch_dmesg_logs(max_lines=50)

        alerts = self.check_thresholds(metrics, failed_services)

        return {
            "timestamp": ts,
            "system_metrics": metrics,
            "top_processes": top_procs,
            "monitored_services": service_states,
            "failed_services": failed_services,
            "journal_logs_sample_count": len(journal_logs),
            "dmesg_logs_sample_count": len(dmesg_logs),
            "threshold_alerts": alerts,
        }

    def check_thresholds(
        self,
        metrics: dict[str, Any],
        failed_services: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Evaluate current system state against configured resource and service thresholds."""
        alerts: list[dict[str, Any]] = []

        # CPU Check
        cpu_cfg = self.thresholds.get("cpu", {})
        cpu_usage = metrics.get("cpu", {}).get("total_percent", 0.0)
        if cpu_usage >= cpu_cfg.get("critical_percent", 90):
            alerts.append({
                "type": FailureType.CPU_OVERLOAD.value,
                "severity": Severity.CRITICAL.value,
                "message": f"CPU usage ({cpu_usage:.1f}%) exceeded critical threshold ({cpu_cfg.get('critical_percent', 90)}%)",
                "value": cpu_usage,
            })
        elif cpu_usage >= cpu_cfg.get("warning_percent", 80):
            alerts.append({
                "type": FailureType.CPU_OVERLOAD.value,
                "severity": Severity.WARNING.value,
                "message": f"CPU usage ({cpu_usage:.1f}%) exceeded warning threshold ({cpu_cfg.get('warning_percent', 80)}%)",
                "value": cpu_usage,
            })

        # Memory Check
        mem_cfg = self.thresholds.get("memory", {})
        mem_usage = metrics.get("memory", {}).get("used_percent", 0.0)
        if mem_usage >= mem_cfg.get("critical_percent", 95):
            alerts.append({
                "type": FailureType.MEMORY_EXHAUSTION.value,
                "severity": Severity.CRITICAL.value,
                "message": f"Memory usage ({mem_usage:.1f}%) exceeded critical threshold ({mem_cfg.get('critical_percent', 95)}%)",
                "value": mem_usage,
            })
        elif mem_usage >= mem_cfg.get("warning_percent", 85):
            alerts.append({
                "type": FailureType.MEMORY_EXHAUSTION.value,
                "severity": Severity.WARNING.value,
                "message": f"Memory usage ({mem_usage:.1f}%) exceeded warning threshold ({mem_cfg.get('warning_percent', 85)}%)",
                "value": mem_usage,
            })

        # Disk Check
        disk_cfg = self.thresholds.get("disk", {})
        for path, usage in metrics.get("disk", {}).items():
            pct = usage.get("percent", 0.0)
            if pct >= disk_cfg.get("critical_percent", 95):
                alerts.append({
                    "type": FailureType.DISK_EXHAUSTION.value,
                    "severity": Severity.CRITICAL.value,
                    "message": f"Disk usage on {path} ({pct:.1f}%) exceeded critical threshold ({disk_cfg.get('critical_percent', 95)}%)",
                    "path": path,
                    "value": pct,
                })
            elif pct >= disk_cfg.get("warning_percent", 85):
                alerts.append({
                    "type": FailureType.DISK_EXHAUSTION.value,
                    "severity": Severity.WARNING.value,
                    "message": f"Disk usage on {path} ({pct:.1f}%) exceeded warning threshold ({disk_cfg.get('warning_percent', 85)}%)",
                    "path": path,
                    "value": pct,
                })

        # Failed Service Check
        for svc in failed_services:
            unit_name = svc.get("unit", "unknown")
            alerts.append({
                "type": FailureType.SERVICE_FAILURE.value,
                "severity": Severity.CRITICAL.value,
                "message": f"Systemd service '{unit_name}' is in failed state",
                "unit": unit_name,
            })

        return alerts

    def run(self, once: bool = False) -> None:
        """Run the monitoring loop or single-shot execution."""
        setup_logging(self.config.get("aegisos", {}).get("log_level", "INFO"))
        logger.info("Starting AegisOS Monitoring Daemon (poll interval: %ds)", self.poll_interval)

        def handle_signal(signum: int, frame: Any) -> None:
            logger.info("Received signal %d, shutting down daemon gracefully...", signum)
            self._running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        self._running = True
        while self._running:
            try:
                snapshot = self.collect_telemetry_snapshot()
                logger.info(
                    "Collected snapshot: CPU %.1f%% | Mem %.1f%% | Alerts: %d",
                    snapshot["system_metrics"]["cpu"]["total_percent"],
                    snapshot["system_metrics"]["memory"]["used_percent"],
                    len(snapshot["threshold_alerts"]),
                )
                if once:
                    print(json.dumps(snapshot, indent=2))
                    break
            except Exception as exc:
                logger.error("Unexpected error in monitoring daemon loop: %s", exc, exc_info=True)

            if not once and self._running:
                time.sleep(self.poll_interval)

        logger.info("AegisOS Monitoring Daemon stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisOS Real-Time Monitoring Daemon")
    parser.add_argument("--config", default="config/aegisos.yaml", help="Path to main configuration file")
    parser.add_argument("--once", action="store_true", help="Collect single telemetry snapshot and exit")
    args = parser.parse_args()

    daemon = MonitoringDaemon(config_path=args.config)
    daemon.run(once=args.once)


if __name__ == "__main__":
    main()
