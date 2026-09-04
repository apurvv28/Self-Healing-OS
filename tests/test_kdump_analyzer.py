"""Tests for CrashAnalyzer module."""

import tempfile
from pathlib import Path

from kdump.analyzer import CrashAnalyzer


def test_parse_crash_log_panic_and_module():
    analyzer = CrashAnalyzer()
    sample_dmesg = """
[ 1234.567890] SysRq : Trigger a Crash
[ 1234.567895] Kernel panic - not syncing: Fatal exception in interrupt
[ 1234.567900] CPU: 0 PID: 1234 Comm: sysrq_test Tainted: G        W [my_test_driver]
[ 1234.567905] RIP: 0010:[<ffffffff81001234>] my_test_driver_crash+0x1b/0x20
[ 1234.567910] Call Trace:
[ 1234.567915]  [<ffffffff81001234>] my_test_driver_crash+0x1b/0x20
[ 1234.567920]  [<ffffffff81005678>] sysrq_handle_crash+0x10/0x20
---[ end trace 1234567890 ]---
    """

    report = analyzer.parse_crash_log(sample_dmesg)

    assert "Fatal exception in interrupt" in report["panic_type"] or "Trigger a Crash" in report["panic_type"]
    assert report["suspect_module"] == "my_test_driver"
    assert report["instruction_pointer"] == "ffffffff81001234"
    assert len(report["call_trace"]) >= 1


def test_parse_vmcore_file():
    analyzer = CrashAnalyzer()
    with tempfile.TemporaryDirectory() as tmpdir:
        vmcore_file = Path(tmpdir) / "vmcore-dmesg.txt"
        vmcore_file.write_text("Kernel panic - not syncing: Out of memory in kernel space", encoding="utf-8")

        report = analyzer.parse_vmcore_file(vmcore_file)
        assert "Out of memory" in report["panic_type"]
