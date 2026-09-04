"""Root-Cause Analysis (RCA) engine for AegisOS.

Correlates temporal incident events, applies ML triage classification,
computes multi-signal confidence scores, and synthesizes structured AegisDiagnosis objects.
"""

from __future__ import annotations

import logging
from typing import Any

from ai.classifier import FailureClassifier
from common.config_loader import load_config
from common.events import AegisDiagnosis, AegisEvent, FailureType, RiskLevel
from rca.correlator import TemporalCorrelator
from rca.scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


# Standard remediation recommendations per failure type
REMEDIATION_MAP: dict[str, str] = {
    FailureType.SERVICE_FAILURE.value: "restart_service",
    FailureType.MEMORY_EXHAUSTION.value: "cleanup_temp_files",
    FailureType.CPU_OVERLOAD.value: "apply_safe_sysctl",
    FailureType.DISK_EXHAUSTION.value: "cleanup_temp_files",
    FailureType.KERNEL_ERROR.value: "investigate_kernel",
    FailureType.DRIVER_FAILURE.value: "reload_driver",
    FailureType.CONFIGURATION_ERROR.value: "restore_configuration",
    FailureType.UNKNOWN_FAILURE.value: "escalate_to_admin",
}

# Risk level mapping per failure type
RISK_MAP: dict[str, RiskLevel] = {
    FailureType.SERVICE_FAILURE.value: RiskLevel.LOW,
    FailureType.DISK_EXHAUSTION.value: RiskLevel.LOW,
    FailureType.CPU_OVERLOAD.value: RiskLevel.MEDIUM,
    FailureType.MEMORY_EXHAUSTION.value: RiskLevel.MEDIUM,
    FailureType.CONFIGURATION_ERROR.value: RiskLevel.HIGH,
    FailureType.DRIVER_FAILURE.value: RiskLevel.HIGH,
    FailureType.KERNEL_ERROR.value: RiskLevel.CRITICAL,
    FailureType.UNKNOWN_FAILURE.value: RiskLevel.MEDIUM,
}


class RCAEngine:
    """Orchestrates temporal correlation, ML triage, confidence scoring, and root cause diagnosis."""

    def __init__(
        self,
        config_path: str = "config/aegisos.yaml",
        classifier: FailureClassifier | None = None,
        correlator: TemporalCorrelator | None = None,
        scorer: ConfidenceScorer | None = None,
    ) -> None:
        self.config = load_config(config_path)
        self.classifier = classifier if classifier is not None else FailureClassifier()
        self.correlator = correlator if correlator is not None else TemporalCorrelator()
        self.scorer = scorer if scorer is not None else ConfidenceScorer(config_path=config_path)

    def diagnose(
        self,
        target_event: AegisEvent,
        context_events: list[AegisEvent] | None = None,
    ) -> AegisDiagnosis:
        """Perform Root-Cause Analysis on a target event using surrounding context events."""
        candidates = context_events or []

        # 1. Temporal event correlation
        correlated = self.correlator.correlate_events(target_event, candidates)

        # 2. Evidence bundling
        evidence_bundle = self.correlator.bundle_evidence(target_event, correlated)

        # 3. AI Triage classification
        ml_info = self.classifier.classify_evidence(evidence_bundle["raw_records"])

        # Determine failure type (prefer ML if confident, fallback to target event type)
        f_type_str = ml_info.get("failure_type") or target_event.failure_type.value
        try:
            failure_type = FailureType(f_type_str)
        except ValueError:
            failure_type = target_event.failure_type

        # 4. Confidence scoring
        confidence_score = self.scorer.calculate_confidence(target_event, ml_info, evidence_bundle)

        # 5. Root cause synthesis
        probable_root_cause = self._synthesize_root_cause(target_event, failure_type, evidence_bundle)

        # 6. Recommendation and Risk Level mapping
        recommended_remediation = REMEDIATION_MAP.get(failure_type.value, "escalate_to_admin")
        risk_level = RISK_MAP.get(failure_type.value, RiskLevel.MEDIUM)

        correlated_ids = [e.event_id for e in correlated]

        diagnosis = AegisDiagnosis(
            event_id=target_event.event_id,
            failure_type=failure_type,
            probable_root_cause=probable_root_cause,
            evidence=evidence_bundle["bullets"],
            confidence_score=confidence_score,
            recommended_remediation=recommended_remediation,
            risk_level=risk_level,
            correlated_event_ids=correlated_ids,
        )

        logger.info(
            "RCA Diagnosis generated for event %s: Cause='%s', Confidence=%.2f, Policy=%s",
            target_event.event_id,
            probable_root_cause,
            confidence_score,
            self.scorer.evaluate_policy(confidence_score),
        )

        return diagnosis

    def _synthesize_root_cause(
        self,
        event: AegisEvent,
        failure_type: FailureType,
        evidence_bundle: dict[str, Any],
    ) -> str:
        """Synthesize human-readable probable root cause text."""
        unit = event.affected_unit
        proc = event.affected_process

        if failure_type == FailureType.SERVICE_FAILURE:
            target = f"'{unit}'" if unit else "systemd unit"
            return f"Systemd service {target} failed to start or exited unexpectedly with non-zero code."

        if failure_type == FailureType.MEMORY_EXHAUSTION:
            target = f"'{proc}'" if proc else "system process"
            return f"High memory pressure triggered kernel OOM killer or allocation failure affecting {target}."

        if failure_type == FailureType.CPU_OVERLOAD:
            target = f"'{proc}'" if proc else "workload"
            return f"Sustained high CPU utilization saturation caused by {target}."

        if failure_type == FailureType.DISK_EXHAUSTION:
            target = f"'{unit}'" if unit else "mount"
            return f"Storage space depletion on partition {target} reached critical threshold."

        if failure_type == FailureType.KERNEL_ERROR:
            return "Kernel panic, null pointer dereference, or segmentation fault encountered in system logs."

        if failure_type == FailureType.DRIVER_FAILURE:
            return "Hardware driver crash, GPU lockup, or module load failure detected."

        if failure_type == FailureType.CONFIGURATION_ERROR:
            return "Invalid configuration file syntax, missing keys, or improper file permissions."

        return f"Unspecified system anomaly associated with source '{event.source}'."
