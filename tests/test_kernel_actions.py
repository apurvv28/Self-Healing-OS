"""Tests for kernel_actions module."""

import tempfile
from pathlib import Path

from remediation.kernel_actions import (
    apply_livepatch,
    blacklist_module,
    reload_driver,
    rollback_kernel_action,
)


def test_blacklist_module_and_rollback():
    with tempfile.TemporaryDirectory() as tmpdir:
        res = blacklist_module("my_test_driver", config_dir=tmpdir)
        assert res["action"] == "blacklist_module"
        assert res["target"] == "my_test_driver"
        assert res["success"] is True

        blacklist_file = Path(tmpdir) / "aegis-blacklist-my_test_driver.conf"
        assert blacklist_file.exists()

        # Rollback
        res_rb = rollback_kernel_action("blacklist_module", "my_test_driver", config_dir=tmpdir)
        assert res_rb["success"] is True
        assert not blacklist_file.exists()


def test_reload_driver():
    res = reload_driver("i915")
    assert res["action"] == "reload_driver"
    assert res["target"] == "i915"
    assert res["success"] is True


def test_apply_livepatch():
    res = apply_livepatch("aegis-patch-001")
    assert res["action"] == "apply_livepatch"
    assert res["target"] == "aegis-patch-001"
    assert res["success"] is True
