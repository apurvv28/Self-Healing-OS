"""Kdump crash dump management and incident integration for AegisOS."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from common.events import AegisEvent, EvidenceKind, FailureType, Severity
from kdump.analyzer import CrashAnalyzer

logger = logging.getLogger(__name__)


class KdumpManager:
    """Monitors kdump dump directories, triggers crash analysis, and emits kernel panic incidents."""

    def __init__(
        self,
        crash_dirs: list[str] | None = None,
        analyzer: CrashAnalyzer | None = None,
    ) -> None:
        self.crash_dirs = crash_dirs or ["/var/crash", "/var/log/dump"]
        self.analyzer = analyzer if analyzer is not None else CrashAnalyzer()

    def scan_crash_dumps(self) -> list[AegisEvent]:
        """Scan configured crash dump directories for new panic dumps and emit AegisEvent incidents."""
        events: list[AegisEvent] = []

        for d in self.crash_dirs:
            dir_path = Path(d)
            if not dir_path.exists() or not dir_path.is_dir():
                continue

            for file_path in dir_path.glob("*"):
                if file_path.name.startswith("vmcore-dmesg") or file_path.name.endswith(".crash") or "dmesg" in file_path.name:
                    report = self.analyzer.parse_vmcore_file(file_path)
                    event = self._create_crash_event(report, str(file_path))
                    events.append(event)

        return events

    def process_crash_log_content(self, dmesg_content: str, source_label: str = "kdump_log") -> AegisEvent:
        """Process crash log content string directly and return an AegisEvent incident."""
        report = self.analyzer.parse_crash_log(dmesg_content)
        return self._create_crash_event(report, source_label)

    def _create_crash_event(self, report: dict[str, Any], source_label: str) -> AegisEvent:
        """Create a normalized KERNEL_ERROR AegisEvent from crash report data."""
        evidence = [
            {
                "kind": EvidenceKind.LOG_LINE.value,
                "source": "kdump",
                "panic_type": report.get("panic_type"),
                "suspect_module": report.get("suspect_module"),
                "instruction_pointer": report.get("instruction_pointer"),
                "call_trace": report.get("call_trace"),
                "message": report.get("summary"),
            }
        ]

        return AegisEvent.create(
            failure_type=FailureType.KERNEL_ERROR,
            source=source_label,
            severity=Severity.CRITICAL,
            raw_evidence=evidence,
            affected_unit=report.get("suspect_module", "kernel_core"),
            tags=["kernel", "kdump", "panic", "diagnosis_only"],
        )
