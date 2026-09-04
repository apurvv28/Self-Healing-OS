"""Unified end-to-end self-healing loop coordinator for AegisOS."""

from __future__ import annotations

import logging
from typing import Any

from common.config_loader import load_config
from detector.engine import DetectionEngine
from monitor.daemon import MonitoringDaemon
from rca.engine import RCAEngine
from remediation.engine import RemediationEngine
from verification.engine import VerificationEngine
from verification.metrics import MetricsTracker

logger = logging.getLogger(__name__)


class SelfHealingLoop:
    """Orchestrates the complete Detect -> Diagnose -> Decide -> Remediate -> Verify -> Escalate cycle."""

    def __init__(self, config_path: str = "config/aegisos.yaml") -> None:
        self.config = load_config(config_path)

        self.daemon = MonitoringDaemon(config_path=config_path)
        self.detector = DetectionEngine(config_path=config_path)
        self.rca_engine = RCAEngine(config_path=config_path)
        self.remediation_engine = RemediationEngine(config_path=config_path)
        self.verification_engine = VerificationEngine(config_path=config_path)
        self.metrics_tracker = MetricsTracker()

    def run_cycle(
        self,
        telemetry: dict[str, Any] | None = None,
        operator: str = "auto",
    ) -> list[dict[str, Any]]:
        """Run a single self-healing cycle through all pipeline stages."""
        # 1. Collect Telemetry Snapshot (Phase 2)
        snapshot = telemetry if telemetry is not None else self.daemon.collect_telemetry_snapshot()

        # 2. Failure Detection & Incident Recording (Phase 3)
        detected_incidents = self.detector.process_telemetry(snapshot)
        logger.info("Self-Healing Cycle: Detected %d new incident(s)", len(detected_incidents))

        cycle_results: list[dict[str, Any]] = []

        for incident in detected_incidents:
            # 3. Root-Cause Analysis & AI Triage (Phases 4 & 5)
            diagnosis = self.rca_engine.diagnose(incident)

            # 4. Remediation Decision & Execution (Phase 6)
            remediation_result = self.remediation_engine.execute_remediation(diagnosis, operator=operator)

            # 5. Post-Remediation Telemetry & Recovery Verification (Phase 7)
            post_telemetry = self.daemon.collect_telemetry_snapshot()
            verification_record = self.verification_engine.verify_recovery(
                diagnosis=diagnosis,
                remediation_result=remediation_result,
                telemetry=post_telemetry,
                initial_timestamp=incident.timestamp,
            )

            cycle_results.append({
                "event_id": incident.event_id,
                "failure_type": incident.failure_type.value if hasattr(incident.failure_type, "value") else str(incident.failure_type),
                "diagnosis": diagnosis.to_dict(),
                "remediation": remediation_result,
                "verification": verification_record,
            })

        return cycle_results
