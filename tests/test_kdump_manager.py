"""Tests for KdumpManager module."""

import tempfile
from pathlib import Path

from common.events import FailureType, Severity
from kdump.manager import KdumpManager


def test_kdump_manager_scan_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        crash_file = Path(tmpdir) / "vmcore-dmesg.txt"
        crash_file.write_text("Kernel panic - not syncing: Fatal hardware MCE", encoding="utf-8")

        manager = KdumpManager(crash_dirs=[tmpdir])
        events = manager.scan_crash_dumps()

        assert len(events) == 1
        event = events[0]
        assert event.failure_type == FailureType.KERNEL_ERROR
        assert event.severity == Severity.CRITICAL
        assert "diagnosis_only" in event.tags


def test_kdump_manager_process_content():
    manager = KdumpManager()
    dmesg_str = "Kernel panic - not syncing: Attempted to kill init!"

    event = manager.process_crash_log_content(dmesg_str, source_label="manual_test")
    assert event.failure_type == FailureType.KERNEL_ERROR
    assert event.source == "manual_test"
    assert event.severity == Severity.CRITICAL
