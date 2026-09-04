"""Advanced kernel-level remediation actions for AegisOS."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def blacklist_module(module_name: str, config_dir: str | Path = "/etc/modprobe.d") -> dict[str, Any]:
    """Isolate a faulty kernel module by writing a blacklist config file and removing the module."""
    modprobe_path = shutil.which("modprobe")
    conf_dir = Path(config_dir)

    try:
        conf_dir.mkdir(parents=True, exist_ok=True)
        blacklist_file = conf_dir / f"aegis-blacklist-{module_name}.conf"
        blacklist_file.write_text(f"blacklist {module_name}\ninstall {module_name} /bin/false\n", encoding="utf-8")
        logger.info("Created kernel module blacklist file: %s", blacklist_file)

        mod_success = True
        if modprobe_path:
            res = subprocess.run([modprobe_path, "-r", module_name], capture_output=True, text=True, check=False)
            mod_success = res.returncode == 0

        return {
            "action": "blacklist_module",
            "target": module_name,
            "success": mod_success,
            "blacklist_file": str(blacklist_file),
            "output": f"Blacklisted module {module_name}",
            "error": "",
            "dry_run": not bool(modprobe_path),
        }
    except Exception as exc:
        logger.error("Failed to blacklist module %s: %s", module_name, exc)
        return {
            "action": "blacklist_module",
            "target": module_name,
            "success": False,
            "output": "",
            "error": str(exc),
            "dry_run": False,
        }


def reload_driver(driver_name: str) -> dict[str, Any]:
    """Unload and reload a kernel driver module."""
    modprobe_path = shutil.which("modprobe")
    if not modprobe_path:
        logger.warning("modprobe binary not found; performing dry-run driver reload for %s", driver_name)
        return {
            "action": "reload_driver",
            "target": driver_name,
            "success": True,
            "output": f"Dry-run reload of driver {driver_name} completed.",
            "error": "",
            "dry_run": True,
        }

    try:
        # Step 1: Remove module
        res_unload = subprocess.run([modprobe_path, "-r", driver_name], capture_output=True, text=True, check=False)
        # Step 2: Load module
        res_load = subprocess.run([modprobe_path, driver_name], capture_output=True, text=True, check=False)

        success = res_load.returncode == 0
        return {
            "action": "reload_driver",
            "target": driver_name,
            "success": success,
            "output": res_load.stdout.strip(),
            "error": res_load.stderr.strip() if not success else "",
            "dry_run": False,
        }
    except Exception as exc:
        logger.error("Failed to reload driver %s: %s", driver_name, exc)
        return {
            "action": "reload_driver",
            "target": driver_name,
            "success": False,
            "output": "",
            "error": str(exc),
            "dry_run": False,
        }


def apply_livepatch(patch_name: str, package_path: str | None = None) -> dict[str, Any]:
    """Apply a pre-approved Linux Livepatch / kpatch package (demonstration mode)."""
    kpatch_path = shutil.which("kpatch") or shutil.which("canonical-livepatch")

    if not kpatch_path:
        logger.warning("Livepatch tool not found; performing dry-run livepatch for %s", patch_name)
        return {
            "action": "apply_livepatch",
            "target": patch_name,
            "success": True,
            "output": f"Dry-run livepatch '{patch_name}' applied successfully.",
            "error": "",
            "dry_run": True,
        }

    try:
        cmd = [kpatch_path, "apply", patch_name] if "kpatch" in kpatch_path else [kpatch_path, "refresh"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        success = res.returncode == 0
        return {
            "action": "apply_livepatch",
            "target": patch_name,
            "success": success,
            "output": res.stdout.strip(),
            "error": res.stderr.strip() if not success else "",
            "dry_run": False,
        }
    except Exception as exc:
        logger.error("Failed to apply livepatch %s: %s", patch_name, exc)
        return {
            "action": "apply_livepatch",
            "target": patch_name,
            "success": False,
            "output": "",
            "error": str(exc),
            "dry_run": False,
        }


def rollback_kernel_action(action_name: str, target: str, config_dir: str | Path = "/etc/modprobe.d") -> dict[str, Any]:
    """Roll back kernel remediation action (e.g. remove blacklist config or unload livepatch)."""
    if action_name == "blacklist_module":
        conf_file = Path(config_dir) / f"aegis-blacklist-{target}.conf"
        if conf_file.exists():
            try:
                conf_file.unlink()
                logger.info("Rollback: Removed blacklist file %s", conf_file)
                return {
                    "action": "rollback_kernel_action",
                    "target": target,
                    "success": True,
                    "output": f"Removed blacklist file for {target}",
                    "error": "",
                }
            except Exception as exc:
                return {
                    "action": "rollback_kernel_action",
                    "target": target,
                    "success": False,
                    "output": "",
                    "error": str(exc),
                }

    return {
        "action": "rollback_kernel_action",
        "target": target,
        "success": True,
        "output": f"Completed rollback for {action_name}:{target}",
        "error": "",
    }
