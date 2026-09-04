"""Approved kernel remediation and patch database manager."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from common.config_loader import load_yaml

logger = logging.getLogger(__name__)


class KernelPatchDatabase:
    """Manages pre-approved kernel crash signatures and remediation policies."""

    def __init__(self, config_path: str | Path = "config/kernel-remediations.yaml") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            self.config_path = Path.cwd() / self.config_path

        self.remediations: dict[str, dict[str, Any]] = {}
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path.exists():
            try:
                data = load_yaml(self.config_path)
                self.remediations = data.get("kernel_remediations", {})
                logger.info("Loaded %d kernel remediation rules from %s", len(self.remediations), self.config_path)
            except Exception as exc:
                logger.warning("Failed to load kernel remediations config: %s", exc)

    def find_remediation_for_evidence(self, evidence_text: str) -> dict[str, Any] | None:
        """Search approved database for matching crash pattern."""
        if not isinstance(evidence_text, str):
            evidence_text = str(evidence_text)

        text_lower = evidence_text.lower()
        for sig_id, entry in self.remediations.items():
            pattern = entry.get("crash_pattern", "").lower()
            if pattern and pattern in text_lower:
                return {
                    "signature_id": sig_id,
                    "approved_action": entry.get("approved_action", "escalate"),
                    "target": entry.get("target", "kernel"),
                    "admin_approved": entry.get("admin_approved", False),
                    "rollback_action": entry.get("rollback_action", "escalate"),
                }

        return None
