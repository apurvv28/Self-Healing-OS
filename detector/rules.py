"""Rule-based failure detectors for AegisOS.

Analyzes monitoring telemetry snapshots to detect service failures,
resource exhaustion, and kernel/driver errors, emitting normalized AegisEvent objects.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from common.events import AegisEvent, EvidenceKind, FailureType, Severity

logger = logging.getLogger(__name__)


class BaseDetector:
    """Base interface for all rule-based failure detectors."""

    def detect(self, telemetry: dict[str, Any], thresholds: dict[str, Any] | None = None) -> list[AegisEvent]:
        raise NotImplementedError


class ServiceDetector(BaseDetector):
    """Detects failed systemd services and excessive service restarts."""

    def detect(self, telemetry: dict[str, Any], thresholds: dict[str, Any] | None = None) -> list[AegisEvent]:
        events: list[AegisEvent] = []
        svc_thresh = (thresholds or {}).get("service", {})
        max_restarts = svc_thresh.get("max_restarts", 3)

        # 1. Failed services
        failed_services = telemetry.get("failed_services", [])
        for svc in failed_services:
            unit = svc.get("unit", "unknown")
            evidence = [
                {
                    "kind": EvidenceKind.SERVICE_STATE.value,
                    "unit": unit,
                    "active_state": svc.get("active_state", "failed"),
                    "sub_state": svc.get("sub_state", "failed"),
                    "restarts": svc.get("restarts", 0),
                    "exec_code": svc.get("exec_code", "unknown"),
                    "exec_status": svc.get("exec_status", "unknown"),
                }
            ]
            events.append(
                AegisEvent.create(
                    failure_type=FailureType.SERVICE_FAILURE,
                    source="systemd",
                    severity=Severity.CRITICAL,
                    raw_evidence=evidence,
                    affected_unit=unit,
                    tags=["service", "systemd", "failed"],
                )
            )

        # 2. Monitored service restart loops / inactive states
        monitored_services = telemetry.get("monitored_services", [])
        for svc in monitored_services:
            unit = svc.get("unit", "unknown")
            active_state = svc.get("active_state")
            restarts = svc.get("restarts", 0)

            # Skip if already reported in failed_services
            if any(e.affected_unit == unit for e in events):
                continue

            if restarts >= max_restarts:
                evidence = [
                    {
                        "kind": EvidenceKind.SERVICE_STATE.value,
                        "unit": unit,
                        "restarts": restarts,
                        "max_restarts": max_restarts,
                        "active_state": active_state,
                    }
                ]
                events.append(
                    AegisEvent.create(
                        failure_type=FailureType.SERVICE_FAILURE,
                        source="systemd",
                        severity=Severity.WARNING,
                        raw_evidence=evidence,
                        affected_unit=unit,
                        tags=["service", "systemd", "restart_loop"],
                    )
                )

        return events


class ResourceDetector(BaseDetector):
    """Detects CPU overload, memory exhaustion, and disk space depletion."""

    def detect(self, telemetry: dict[str, Any], thresholds: dict[str, Any] | None = None) -> list[AegisEvent]:
        events: list[AegisEvent] = []
        thresh = thresholds or {}
        metrics = telemetry.get("system_metrics", {})
        top_procs = telemetry.get("top_processes", [])

        # 1. CPU Overload
        cpu_metrics = metrics.get("cpu", {})
        cpu_pct = cpu_metrics.get("total_percent", 0.0)
        cpu_cfg = thresh.get("cpu", {})
        crit_cpu = cpu_cfg.get("critical_percent", 90)
        warn_cpu = cpu_cfg.get("warning_percent", 80)

        if cpu_pct >= warn_cpu:
            sev = Severity.CRITICAL if cpu_pct >= crit_cpu else Severity.WARNING
            top_cpu_proc = top_procs[0]["name"] if top_procs else None
            evidence = [
                {
                    "kind": EvidenceKind.METRIC.value,
                    "metric_name": "cpu_utilization",
                    "value": cpu_pct,
                    "threshold": crit_cpu if sev == Severity.CRITICAL else warn_cpu,
                }
            ]
            if top_procs:
                evidence.append({
                    "kind": EvidenceKind.PROCESS.value,
                    "top_processes": top_procs[:3],
                })

            events.append(
                AegisEvent.create(
                    failure_type=FailureType.CPU_OVERLOAD,
                    source="resource_monitor",
                    severity=sev,
                    raw_evidence=evidence,
                    affected_process=top_cpu_proc,
                    tags=["resource", "cpu"],
                )
            )

        # 2. Memory Exhaustion
        mem_metrics = metrics.get("memory", {})
        mem_pct = mem_metrics.get("used_percent", 0.0)
        mem_cfg = thresh.get("memory", {})
        crit_mem = mem_cfg.get("critical_percent", 95)
        warn_mem = mem_cfg.get("warning_percent", 85)

        if mem_pct >= warn_mem:
            sev = Severity.CRITICAL if mem_pct >= crit_mem else Severity.WARNING
            top_mem_proc = (
                max(top_procs, key=lambda p: p.get("memory_percent", 0.0))["name"]
                if top_procs
                else None
            )
            evidence = [
                {
                    "kind": EvidenceKind.METRIC.value,
                    "metric_name": "memory_utilization",
                    "value": mem_pct,
                    "threshold": crit_mem if sev == Severity.CRITICAL else warn_mem,
                }
            ]
            if top_procs:
                evidence.append({
                    "kind": EvidenceKind.PROCESS.value,
                    "top_processes": top_procs[:3],
                })

            events.append(
                AegisEvent.create(
                    failure_type=FailureType.MEMORY_EXHAUSTION,
                    source="resource_monitor",
                    severity=sev,
                    raw_evidence=evidence,
                    affected_process=top_mem_proc,
                    tags=["resource", "memory"],
                )
            )

        # 3. Disk Exhaustion
        disk_metrics = metrics.get("disk", {})
        disk_cfg = thresh.get("disk", {})
        crit_disk = disk_cfg.get("critical_percent", 95)
        warn_disk = disk_cfg.get("warning_percent", 85)

        for path, usage in disk_metrics.items():
            disk_pct = usage.get("percent", 0.0)
            if disk_pct >= warn_disk:
                sev = Severity.CRITICAL if disk_pct >= crit_disk else Severity.WARNING
                evidence = [
                    {
                        "kind": EvidenceKind.METRIC.value,
                        "metric_name": f"disk_utilization:{path}",
                        "value": disk_pct,
                        "path": path,
                        "threshold": crit_disk if sev == Severity.CRITICAL else warn_disk,
                    }
                ]
                events.append(
                    AegisEvent.create(
                        failure_type=FailureType.DISK_EXHAUSTION,
                        source="resource_monitor",
                        severity=sev,
                        raw_evidence=evidence,
                        affected_unit=path,
                        tags=["resource", "disk"],
                    )
                )

        return events


class KernelDetector(BaseDetector):
    """Detects kernel panics, OOM killer invocations, segfaults, and driver errors."""

    OOM_PATTERNS = [
        re.compile(r"out of memory: kill process", re.IGNORECASE),
        re.compile(r"oom-killer", re.IGNORECASE),
        re.compile(r"invoked oom-killer", re.IGNORECASE),
    ]

    SEGFAULT_PATTERNS = [
        re.compile(r"segfault at", re.IGNORECASE),
        re.compile(r"segmentation fault", re.IGNORECASE),
        re.compile(r"general protection fault", re.IGNORECASE),
    ]

    IO_PATTERNS = [
        re.compile(r"i/o error", re.IGNORECASE),
        re.compile(r"blk_update_request", re.IGNORECASE),
        re.compile(r"ext4-fs error", re.IGNORECASE),
        re.compile(r"btrfs error", re.IGNORECASE),
    ]

    KERNEL_PANIC_PATTERNS = [
        re.compile(r"kernel panic", re.IGNORECASE),
        re.compile(r"call trace:", re.IGNORECASE),
        re.compile(r"bug: unable to handle kernel", re.IGNORECASE),
    ]

    DRIVER_PATTERNS = [
        re.compile(r"gpu lockup", re.IGNORECASE),
        re.compile(r"driver error", re.IGNORECASE),
        re.compile(r"firmware failed to load", re.IGNORECASE),
    ]

    def detect(self, telemetry: dict[str, Any], thresholds: dict[str, Any] | None = None) -> list[AegisEvent]:
        events: list[AegisEvent] = []

        # Merge dmesg and journal logs into log stream
        logs = telemetry.get("dmesg_logs", []) + telemetry.get("journal_logs", [])
        raw_log_entries = telemetry.get("log_entries", []) + logs

        for entry in raw_log_entries:
            msg = entry.get("message", "") if isinstance(entry, dict) else str(entry)
            if not msg:
                continue

            # 1. OOM Killer Check
            if any(p.search(msg) for p in self.OOM_PATTERNS):
                evidence = [{"kind": EvidenceKind.LOG_LINE.value, "log_entry": entry}]
                events.append(
                    AegisEvent.create(
                        failure_type=FailureType.MEMORY_EXHAUSTION,
                        source="kernel_dmesg",
                        severity=Severity.CRITICAL,
                        raw_evidence=evidence,
                        tags=["kernel", "oom_killer"],
                    )
                )
                continue

            # 2. Kernel Panic / Call Trace Check
            if any(p.search(msg) for p in self.KERNEL_PANIC_PATTERNS):
                evidence = [{"kind": EvidenceKind.LOG_LINE.value, "log_entry": entry}]
                events.append(
                    AegisEvent.create(
                        failure_type=FailureType.KERNEL_ERROR,
                        source="kernel_dmesg",
                        severity=Severity.CRITICAL,
                        raw_evidence=evidence,
                        tags=["kernel", "panic"],
                    )
                )
                continue

            # 3. Segfault Check
            if any(p.search(msg) for p in self.SEGFAULT_PATTERNS):
                evidence = [{"kind": EvidenceKind.LOG_LINE.value, "log_entry": entry}]
                events.append(
                    AegisEvent.create(
                        failure_type=FailureType.KERNEL_ERROR,
                        source="kernel_dmesg",
                        severity=Severity.WARNING,
                        raw_evidence=evidence,
                        tags=["kernel", "segfault"],
                    )
                )
                continue

            # 4. Driver Failure Check
            if any(p.search(msg) for p in self.DRIVER_PATTERNS):
                evidence = [{"kind": EvidenceKind.LOG_LINE.value, "log_entry": entry}]
                events.append(
                    AegisEvent.create(
                        failure_type=FailureType.DRIVER_FAILURE,
                        source="kernel_dmesg",
                        severity=Severity.WARNING,
                        raw_evidence=evidence,
                        tags=["kernel", "driver"],
                    )
                )

        return events
