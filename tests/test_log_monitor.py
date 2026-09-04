"""Tests for LogMonitor module."""

from unittest.mock import MagicMock, patch

from monitor.log_monitor import LogMonitor


def test_log_monitor_initialization():
    monitor = LogMonitor(journal_lookback_minutes=10)
    assert monitor.journal_lookback_minutes == 10


def test_normalize_journal_entry():
    monitor = LogMonitor()
    raw = {
        "MESSAGE": "Test failure log line",
        "_SYSTEMD_UNIT": "test-service.service",
        "PRIORITY": "3",
        "__REALTIME_TIMESTAMP": "1700000000000000",
        "_PID": "1234",
    }
    normalized = monitor.normalize_journal_entry(raw)
    assert normalized["kind"] == "log_line"
    assert normalized["source"] == "journald"
    assert normalized["message"] == "Test failure log line"
    assert normalized["unit"] == "test-service.service"
    assert normalized["priority"] == "3"
    assert normalized["pid"] == "1234"


def test_normalize_dmesg_line():
    monitor = LogMonitor()
    line = "[   12.345678] Out of memory: Kill process 5678 (python)"
    normalized = monitor.normalize_dmesg_line(line)
    assert normalized["kind"] == "log_line"
    assert normalized["source"] == "dmesg"
    assert "Out of memory" in normalized["message"]


@patch("shutil.which")
def test_fetch_logs_when_binary_missing(mock_which):
    mock_which.return_value = None
    monitor = LogMonitor()

    assert monitor.fetch_journal_logs() == []
    assert monitor.fetch_dmesg_logs() == []
