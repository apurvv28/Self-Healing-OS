"""Log monitoring module for AegisOS.

Collects log records from systemd journald and kernel dmesg,
normalizing them into standard evidence structures.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from typing import Any

from common.events import EvidenceKind

logger = logging.getLogger(__name__)


class LogMonitor:
    """Monitors system logs from journalctl and dmesg."""

    def __init__(self, journal_lookback_minutes: int = 5) -> None:
        self.journal_lookback_minutes = journal_lookback_minutes
        self._journalctl_path = shutil.which("journalctl")
        self._dmesg_path = shutil.which("dmesg")

    def fetch_journal_logs(
        self,
        since_minutes: int | None = None,
        unit: str | None = None,
        priority: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch systemd journal logs formatted as JSON entries."""
        lookback = since_minutes if since_minutes is not None else self.journal_lookback_minutes
        if not self._journalctl_path:
            logger.warning("journalctl binary not found; returning empty log list.")
            return []

        cmd = [self._journalctl_path, "-o", "json", f"--since={lookback} min ago"]
        if unit:
            cmd.extend(["-u", unit])
        if priority is not None:
            cmd.extend(["-p", str(priority)])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if res.returncode != 0:
                logger.warning("journalctl returned code %d: %s", res.returncode, res.stderr.strip())
                return []

            logs: list[dict[str, Any]] = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    logs.append(self.normalize_journal_entry(raw))
                except json.JSONDecodeError:
                    continue
            return logs

        except Exception as exc:
            logger.error("Failed to execute journalctl: %s", exc)
            return []

    def fetch_dmesg_logs(self, max_lines: int = 100) -> list[dict[str, Any]]:
        """Fetch recent kernel ring buffer messages from dmesg."""
        if not self._dmesg_path:
            logger.warning("dmesg binary not found; returning empty log list.")
            return []

        try:
            res = subprocess.run(
                [self._dmesg_path, "-T"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if res.returncode != 0:
                logger.warning("dmesg returned code %d: %s", res.returncode, res.stderr.strip())
                return []

            lines = res.stdout.splitlines()[-max_lines:]
            logs: list[dict[str, Any]] = []
            for line in lines:
                if line.strip():
                    logs.append(self.normalize_dmesg_line(line))
            return logs

        except Exception as exc:
            logger.error("Failed to execute dmesg: %s", exc)
            return []

    def normalize_journal_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Normalize a journalctl JSON record into Aegis evidence format."""
        msg = entry.get("MESSAGE", "")
        if isinstance(msg, list):
            msg = "".join(chr(b) for b in msg)

        # Microsecond timestamp conversion
        raw_ts = entry.get("__REALTIME_TIMESTAMP")
        if raw_ts:
            try:
                dt = datetime.fromtimestamp(int(raw_ts) / 1000000, tz=UTC)
                iso_ts = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            except (ValueError, TypeError, OverflowError):
                iso_ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            iso_ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        unit = entry.get("_SYSTEMD_UNIT") or entry.get("SYSLOG_IDENTIFIER") or "unknown"
        priority = entry.get("PRIORITY", "6")

        return {
            "kind": EvidenceKind.LOG_LINE.value,
            "timestamp": iso_ts,
            "source": "journald",
            "message": str(msg),
            "unit": str(unit),
            "priority": str(priority),
            "pid": str(entry.get("_PID", "")),
            "hostname": str(entry.get("_HOSTNAME", "")),
        }

    def normalize_dmesg_line(self, line: str) -> dict[str, Any]:
        """Normalize a raw dmesg output line into Aegis evidence format."""
        return {
            "kind": EvidenceKind.LOG_LINE.value,
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "dmesg",
            "message": line.strip(),
            "unit": "kernel",
            "priority": "4",
        }
