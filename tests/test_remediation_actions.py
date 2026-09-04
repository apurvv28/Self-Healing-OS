"""Tests for core remediation action handlers."""

import tempfile
from pathlib import Path

from remediation.actions import (
    apply_safe_sysctl,
    cleanup_temp_files,
    escalate,
    restart_service,
    restore_configuration,
)


def test_restart_service():
    res = restart_service("nginx.service")
    assert res["action"] == "restart_service"
    assert res["target"] == "nginx.service"
    assert "success" in res


def test_restore_configuration():
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = Path(tmpdir) / "app.conf"
        backup_file = Path(tmpdir) / "app.conf.bak"

        # Create original backup
        backup_file.write_text("port=8080", encoding="utf-8")
        target_file.write_text("port=CORRUPTED", encoding="utf-8")

        res = restore_configuration(str(target_file), str(backup_file))
        assert res["success"] is True
        assert target_file.read_text(encoding="utf-8") == "port=8080"


def test_cleanup_temp_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        old_file = Path(tmpdir) / "old.tmp"
        old_file.write_text("temp data", encoding="utf-8")

        res = cleanup_temp_files(dirs=[tmpdir], max_age_hours=0)
        assert res["success"] is True
        assert res["files_removed"] >= 1


def test_apply_safe_sysctl():
    res = apply_safe_sysctl({"vm.swappiness": "10"})
    assert res["action"] == "apply_safe_sysctl"
    assert res["success"] is True


def test_escalate():
    res = escalate("Service restart loop detected", "event-123")
    assert res["action"] == "escalate"
    assert res["target"] == "event-123"
    assert res["success"] is True
