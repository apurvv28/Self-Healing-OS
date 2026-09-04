"""Detection engine for AegisOS.

Processes telemetry snapshots, applies rule-based failure detectors,
performs time-window event deduplication, and persists detected incidents.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from common.config_loader import load_config
from common.events import AegisEvent
from detector.rules import BaseDetector, KernelDetector, ResourceDetector, ServiceDetector
from detector.storage import IncidentStorage

logger = logging.getLogger(__name__)


class DetectionEngine:
    """Orchestrates rule-based failure detection, deduplication, and incident recording."""

    def __init__(
        self,
        config_path: str = "config/aegisos.yaml",
        storage: IncidentStorage | None = None,
        detectors: list[BaseDetector] | None = None,
    ) -> None:
        self.config = load_config(config_path)

        db_path = self.config.get("database", {}).get("path", "data/aegisos.db")
        self.storage = storage if storage is not None else IncidentStorage(db_path=db_path)

        self.thresholds = self.config.get("thresholds", {}).get("thresholds", {})
        self.dedup_window = self.config.get("agent", {}).get("dedup_window_seconds", 60)

        self.detectors = detectors or [
            ServiceDetector(),
            ResourceDetector(),
            KernelDetector(),
        ]

        # Signature history for sliding window deduplication: (timestamp, failure_type, affected_unit, affected_process)
        self._recent_signatures: list[tuple[float, str, str | None, str | None]] = []

    def process_telemetry(self, telemetry: dict[str, Any]) -> list[AegisEvent]:
        """Process a telemetry snapshot and return newly detected, deduplicated incidents."""
        raw_events: list[AegisEvent] = []

        for detector in self.detectors:
            try:
                detected = detector.detect(telemetry, thresholds=self.thresholds)
                raw_events.extend(detected)
            except Exception as exc:
                logger.error("Error in detector %s: %s", detector.__class__.__name__, exc, exc_info=True)

        new_incidents: list[AegisEvent] = []
        for event in raw_events:
            if not self._is_duplicate(event):
                self._record_signature(event)
                if self.storage:
                    self.storage.save_incident(event)
                new_incidents.append(event)
            else:
                logger.debug(
                    "Deduplicated event %s (%s, unit=%s, proc=%s)",
                    event.event_id,
                    event.failure_type,
                    event.affected_unit,
                    event.affected_process,
                )

        return new_incidents

    def _is_duplicate(self, event: AegisEvent) -> bool:
        """Check if a matching event signature exists within the deduplication time window."""
        now = time.time()
        cutoff = now - self.dedup_window

        # Prune expired signatures
        self._recent_signatures = [sig for sig in self._recent_signatures if sig[0] >= cutoff]

        f_type = event.failure_type.value if hasattr(event.failure_type, "value") else str(event.failure_type)
        unit = event.affected_unit
        proc = event.affected_process

        for _, s_type, s_unit, s_proc in self._recent_signatures:
            if s_type == f_type and s_unit == unit and s_proc == proc:
                return True

        return False

    def _record_signature(self, event: AegisEvent) -> None:
        f_type = event.failure_type.value if hasattr(event.failure_type, "value") else str(event.failure_type)
        self._recent_signatures.append((
            time.time(),
            f_type,
            event.affected_unit,
            event.affected_process,
        ))
