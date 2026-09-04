"""Resource and process monitoring module for AegisOS.

Collects CPU, memory, disk, load average metrics and process table data
using psutil with fallback to /proc interfaces.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import psutil

from common.events import EvidenceKind

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitors system resource utilization and active processes."""

    def __init__(self, disk_paths: list[str] | None = None) -> None:
        self.disk_paths = disk_paths or ["/"]

    def collect_system_metrics(self) -> dict[str, Any]:
        """Collect high-level CPU, memory, disk, and load average metrics."""
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)

        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        disk_metrics: dict[str, dict[str, Any]] = {}
        for path in self.disk_paths:
            try:
                # Check path existence on target OS
                if os.path.exists(path):
                    usage = psutil.disk_usage(path)
                    disk_metrics[path] = {
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "percent": usage.percent,
                    }
            except Exception as exc:
                logger.warning("Failed to collect disk usage for %s: %s", path, exc)

        # Load average (fallback for platforms where psutil.getloadavg may fail)
        try:
            load_avg = list(psutil.getloadavg())
        except (AttributeError, OSError):
            load_avg = [0.0, 0.0, 0.0]

        return {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cpu": {
                "total_percent": cpu_percent,
                "per_core_percent": cpu_per_core,
                "core_count": psutil.cpu_count(logical=True) or 1,
            },
            "memory": {
                "total_bytes": mem.total,
                "used_bytes": mem.used,
                "free_bytes": mem.available,
                "used_percent": mem.percent,
                "swap_total_bytes": swap.total,
                "swap_used_bytes": swap.used,
                "swap_percent": swap.percent,
            },
            "disk": disk_metrics,
            "load_avg": {
                "1m": load_avg[0],
                "5m": load_avg[1],
                "15m": load_avg[2],
            },
        }

    def collect_top_processes(self, limit: int = 10, sort_by: str = "cpu") -> list[dict[str, Any]]:
        """Collect top processes sorted by CPU or memory usage."""
        processes: list[dict[str, Any]] = []

        attrs = ["pid", "name", "cpu_percent", "memory_percent", "status", "username"]
        for proc in psutil.process_iter(attrs=attrs):
            try:
                info = proc.info
                processes.append({
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu_percent": info["cpu_percent"] or 0.0,
                    "memory_percent": info["memory_percent"] or 0.0,
                    "status": info["status"] or "unknown",
                    "username": info.get("username") or "unknown",
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        key = "cpu_percent" if sort_by == "cpu" else "memory_percent"
        processes.sort(key=lambda p: p.get(key, 0.0), reverse=True)
        return processes[:limit]

    def normalize_resource_evidence(self, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert system metrics into evidence list."""
        evidence_list: list[dict[str, Any]] = []

        ts = metrics.get("timestamp", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))

        # CPU Metric Evidence
        evidence_list.append({
            "kind": EvidenceKind.METRIC.value,
            "timestamp": ts,
            "metric_name": "cpu_utilization",
            "value": metrics.get("cpu", {}).get("total_percent", 0.0),
            "unit": "percent",
        })

        # Memory Metric Evidence
        evidence_list.append({
            "kind": EvidenceKind.METRIC.value,
            "timestamp": ts,
            "metric_name": "memory_utilization",
            "value": metrics.get("memory", {}).get("used_percent", 0.0),
            "unit": "percent",
        })

        # Disk Metric Evidence
        for path, usage in metrics.get("disk", {}).items():
            evidence_list.append({
                "kind": EvidenceKind.METRIC.value,
                "timestamp": ts,
                "metric_name": f"disk_utilization:{path}",
                "value": usage.get("percent", 0.0),
                "unit": "percent",
            })

        return evidence_list
