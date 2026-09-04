"""Core remediation recovery action handlers for AegisOS."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def restart_service(unit_name: str, timeout: int = 30) -> dict[str, Any]:
    """Restart a systemd service unit with timeout."""
    systemctl_path = shutil.which("systemctl")
    if not systemctl_path:
        logger.warning("systemctl not available; performing dry-run restart for %s", unit_name)
        return {
            "action": "restart_service",
            "target": unit_name,
            "success": True,
            "output": f"Dry-run restart of service {unit_name} completed.",
            "error": "",
            "dry_run": True,
        }

    cmd = [systemctl_path, "restart", unit_name]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        success = res.returncode == 0
        return {
            "action": "restart_service",
            "target": unit_name,
            "success": success,
            "output": res.stdout.strip(),
            "error": res.stderr.strip() if not success else "",
            "dry_run": False,
        }
    except Exception as exc:
        logger.error("Error restarting service %s: %s", unit_name, exc)
        return {
            "action": "restart_service",
            "target": unit_name,
            "success": False,
            "output": "",
            "error": str(exc),
            "dry_run": False,
        }


def restore_configuration(target_path: str, backup_path: str | None = None) -> dict[str, Any]:
    """Restore a configuration file from a known-good backup snapshot."""
    target = Path(target_path)
    backup = Path(backup_path) if backup_path else Path(f"{target_path}.bak")

    if not backup.exists():
        logger.warning("Backup file %s does not exist for target %s", backup, target)
        return {
            "action": "restore_configuration",
            "target": str(target),
            "success": False,
            "output": "",
            "error": f"Backup file {backup} not found.",
            "dry_run": False,
        }

    try:
        shutil.copy2(backup, target)
        logger.info("Restored config %s from %s", target, backup)
        return {
            "action": "restore_configuration",
            "target": str(target),
            "success": True,
            "output": f"Restored {target} from {backup}.",
            "error": "",
            "dry_run": False,
        }
    except Exception as exc:
        logger.error("Failed to restore config %s: %s", target, exc)
        return {
            "action": "restore_configuration",
            "target": str(target),
            "success": False,
            "output": "",
            "error": str(exc),
            "dry_run": False,
        }


def cleanup_temp_files(dirs: list[str] | None = None, max_age_hours: int = 24) -> dict[str, Any]:
    """Clean temporary files in pre-approved temporary directories."""
    target_dirs = dirs or ["/tmp", "/var/tmp"]
    files_removed = 0
    bytes_freed = 0
    cutoff_time = time.time() - (max_age_hours * 3600)

    for d in target_dirs:
        dir_path = Path(d)
        if not dir_path.exists() or not dir_path.is_dir():
            continue

        for item in dir_path.glob("*"):
            try:
                if item.is_file() and item.stat().st_mtime < cutoff_time:
                    size = item.stat().st_size
                    item.unlink()
                    files_removed += 1
                    bytes_freed += size
            except Exception as exc:
                logger.debug("Could not remove temp file %s: %s", item, exc)

    return {
        "action": "cleanup_temp_files",
        "target": ", ".join(target_dirs),
        "success": True,
        "files_removed": files_removed,
        "bytes_freed": bytes_freed,
        "output": f"Removed {files_removed} temp files ({bytes_freed} bytes freed).",
        "error": "",
        "dry_run": False,
    }


def apply_safe_sysctl(params: dict[str, str]) -> dict[str, Any]:
    """Apply pre-approved, reversible sysctl configuration parameter changes."""
    sysctl_path = shutil.which("sysctl")
    previous_values: dict[str, str] = {}

    if not sysctl_path:
        logger.warning("sysctl binary not found; performing dry-run sysctl application")
        return {
            "action": "apply_safe_sysctl",
            "target": str(params),
            "success": True,
            "previous_values": {},
            "output": f"Dry-run sysctl application for {params}",
            "error": "",
            "dry_run": True,
        }

    applied: list[str] = []
    for key, value in params.items():
        try:
            # Read current value for rollback
            res_read = subprocess.run([sysctl_path, "-n", key], capture_output=True, text=True, check=False)
            if res_read.returncode == 0:
                previous_values[key] = res_read.stdout.strip()

            # Set new value
            res_write = subprocess.run([sysctl_path, f"{key}={value}"], capture_output=True, text=True, check=False)
            if res_write.returncode == 0:
                applied.append(f"{key}={value}")
        except Exception as exc:
            logger.error("Failed to apply sysctl parameter %s=%s: %s", key, value, exc)

    success = len(applied) == len(params)
    return {
        "action": "apply_safe_sysctl",
        "target": ", ".join(applied),
        "success": success,
        "previous_values": previous_values,
        "output": f"Applied sysctl settings: {', '.join(applied)}",
        "error": "" if success else "Some sysctl parameters failed to apply",
        "dry_run": False,
    }


def escalate(reason: str, event_id: str) -> dict[str, Any]:
    """Escalate incident to human administrator / log alert."""
    logger.warning("ESCALATION ALERT for incident %s: %s", event_id, reason)
    return {
        "action": "escalate",
        "target": event_id,
        "success": True,
        "reason": reason,
        "output": f"Incident {event_id} escalated: {reason}",
        "error": "",
        "dry_run": False,
    }
