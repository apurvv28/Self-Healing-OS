"""Service monitoring module for AegisOS.

Polls systemctl for service unit health, active/sub states, restart counts,
and failed unit enumerations.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from common.events import EvidenceKind

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """Monitors systemd service states and identifies failed units."""

    def __init__(self, monitored_units: list[str] | None = None) -> None:
        self.monitored_units = monitored_units or []
        self._systemctl_path = shutil.which("systemctl")

    @property
    def is_available(self) -> bool:
        return self._systemctl_path is not None

    def get_unit_status(self, unit_name: str) -> dict[str, Any]:
        """Fetch systemd properties for a specific unit."""
        if not self._systemctl_path:
            return {
                "unit": unit_name,
                "active_state": "unknown",
                "sub_state": "unknown",
                "load_state": "unknown",
                "main_pid": 0,
                "restarts": 0,
                "systemctl_available": False,
            }

        cmd = [
            self._systemctl_path,
            "show",
            unit_name,
            "--property=Id,ActiveState,SubState,LoadState,MainPID,NRestarts,ExecMainStatus,ExecMainCode",
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            props: dict[str, str] = {}
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "=" in line:
                        key, val = line.split("=", 1)
                        props[key.strip()] = val.strip()

            active_state = props.get("ActiveState", "unknown")
            sub_state = props.get("SubState", "unknown")
            load_state = props.get("LoadState", "unknown")
            try:
                main_pid = int(props.get("MainPID", "0"))
            except ValueError:
                main_pid = 0
            try:
                restarts = int(props.get("NRestarts", "0"))
            except ValueError:
                restarts = 0

            return {
                "unit": props.get("Id", unit_name),
                "active_state": active_state,
                "sub_state": sub_state,
                "load_state": load_state,
                "main_pid": main_pid,
                "restarts": restarts,
                "exec_status": props.get("ExecMainStatus", "0"),
                "exec_code": props.get("ExecMainCode", "none"),
                "systemctl_available": True,
            }

        except Exception as exc:
            logger.error("Failed to query systemctl for %s: %s", unit_name, exc)
            return {
                "unit": unit_name,
                "active_state": "error",
                "sub_state": "error",
                "load_state": "unknown",
                "main_pid": 0,
                "restarts": 0,
                "systemctl_available": True,
            }

    def list_failed_units(self) -> list[dict[str, Any]]:
        """List all systemd units currently in a failed state."""
        if not self._systemctl_path:
            return []

        # Try json mode first
        cmd_json = [self._systemctl_path, "list-units", "--state=failed", "--output=json"]
        try:
            res = subprocess.run(cmd_json, capture_output=True, text=True, timeout=5, check=False)
            if res.returncode == 0 and res.stdout.strip().startswith("["):
                items = json.loads(res.stdout)
                failed: list[dict[str, Any]] = []
                for item in items:
                    unit_name = item.get("unit") or item.get("id") or "unknown"
                    failed.append(self.get_unit_status(unit_name))
                return failed
        except Exception:
            pass

        # Fallback to standard output parsing
        cmd_plain = [self._systemctl_path, "list-units", "--state=failed", "--plain", "--no-legend"]
        try:
            res = subprocess.run(cmd_plain, capture_output=True, text=True, timeout=5, check=False)
            failed_units: list[dict[str, Any]] = []
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.strip().split()
                    if parts:
                        unit_name = parts[0]
                        failed_units.append(self.get_unit_status(unit_name))
            return failed_units
        except Exception as exc:
            logger.error("Failed to list failed units: %s", exc)
            return []

    def check_all_monitored_units(self) -> list[dict[str, Any]]:
        """Check status for all explicitly configured units."""
        return [self.get_unit_status(u) for u in self.monitored_units]

    def normalize_service_evidence(self, status: dict[str, Any]) -> dict[str, Any]:
        """Convert a unit status record into standard Aegis evidence format."""
        return {
            "kind": EvidenceKind.SERVICE_STATE.value,
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "unit": status.get("unit"),
            "active_state": status.get("active_state"),
            "sub_state": status.get("sub_state"),
            "load_state": status.get("load_state"),
            "main_pid": status.get("main_pid"),
            "restarts": status.get("restarts"),
            "is_failed": status.get("active_state") == "failed",
        }
