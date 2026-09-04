"""Verification engine for AegisOS recovery validation and MTTR computation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from common.config_loader import load_config
from common.events import AegisDiagnosis
from rca.correlator import TemporalCorrelator
from verification.checker import HealthChecker

logger = logging.getLogger(__name__)


class VerificationEngine:
    """Evaluates post-remediation recovery and computes Mean Time To Recovery (MTTR)."""

    def __init__(
        self,
        config_path: str = "config/aegisos.yaml",
        health_checker: HealthChecker | None = None,
    ) -> None:
        self.config = load_config(config_path)
        self.thresholds = self.config.get("thresholds", {})
        self.health_checker = health_checker if health_checker is not None else HealthChecker()

    def verify_recovery(
        self,
        diagnosis: AegisDiagnosis,
        remediation_result: dict[str, Any],
        telemetry: dict[str, Any],
        initial_timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Perform health checks and calculate recovery metrics post-remediation."""
        event_id = diagnosis.event_id
        action_success = remediation_result.get("success", False)

        # 1. Target Service Health Check
        target_unit = remediation_result.get("target")
        service_check = (
            self.health_checker.check_service_health(target_unit)
            if target_unit and "service" in target_unit
            else {"healthy": True, "details": "No specific service target"}
        )

        # 2. System Resource Health Check
        resource_metrics = telemetry.get("system_metrics", {})
        resource_check = self.health_checker.check_resource_health(resource_metrics, self.thresholds)

        # 3. Log Health Check
        logs = telemetry.get("journal_logs", []) + telemetry.get("dmesg_logs", [])
        log_check = self.health_checker.check_log_health(logs)

        # Overall Health Determination
        overall_healthy = action_success and service_check["healthy"] and resource_check["healthy"]
        status = "RECOVERED" if overall_healthy else "ESCALATED"

        # 4. Compute MTTR (Mean Time To Recovery in seconds)
        start_ts = initial_timestamp or telemetry.get("timestamp") or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        start_dt = TemporalCorrelator.parse_timestamp(start_ts)
        end_dt = datetime.now(UTC)
        mttr_seconds = max(0.0, round((end_dt - start_dt).total_seconds(), 2))

        verification_record = {
            "event_id": event_id,
            "status": status,
            "recovered": overall_healthy,
            "action_success": action_success,
            "mttr_seconds": mttr_seconds,
            "health_checks": {
                "service": service_check,
                "resource": resource_check,
                "log": log_check,
            },
        }

        logger.info(
            "Verification result for event %s: Status='%s', Recovered=%s, MTTR=%.2fs",
            event_id,
            status,
            overall_healthy,
            mttr_seconds,
        )

        return verification_record
