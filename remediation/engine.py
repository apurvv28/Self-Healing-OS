"""Remediation policy engine for AegisOS.

Evaluates diagnosis confidence, enforces safety gates and permission whitelists,
tracks max retries, dispatches recovery actions, and logs full audit trails.
"""

from __future__ import annotations

import logging
from typing import Any

from common.config_loader import load_config
from common.events import AegisDiagnosis, FailureType, Severity
from remediation.actions import (
    apply_safe_sysctl,
    cleanup_temp_files,
    escalate,
    restart_service,
    restore_configuration,
)
from remediation.audit import RemediationAuditLogger
from remediation.kernel_actions import (
    apply_livepatch,
    blacklist_module,
    reload_driver,
    rollback_kernel_action,
)
from remediation.kernel_db import KernelPatchDatabase

logger = logging.getLogger(__name__)


class RemediationEngine:
    """Orchestrates recovery policy checks, safety controls, and action dispatching."""

    def __init__(
        self,
        config_path: str = "config/aegisos.yaml",
        audit_logger: RemediationAuditLogger | None = None,
        kernel_db: KernelPatchDatabase | None = None,
    ) -> None:
        self.config = load_config(config_path)

        db_path = self.config.get("database", {}).get("path", "data/aegisos.db")
        self.audit_logger = audit_logger if audit_logger is not None else RemediationAuditLogger(db_path=db_path)
        self.kernel_db = kernel_db if kernel_db is not None else KernelPatchDatabase()

        remediation_cfg = self.config.get("remediation", {}).get("policies", {})
        self.policies = remediation_cfg

        conf_cfg = self.config.get("confidence", {}).get("confidence", {})
        self.auto_remediate_threshold = conf_cfg.get("auto_remediate_at", 0.90)

        escalation_cfg = self.config.get("confidence", {}).get("escalation", {})
        self.max_retries = escalation_cfg.get("max_retries", 3)

        # Retry counter tracking: key -> attempt_count
        self._retry_counts: dict[str, int] = {}

    def execute_remediation(
        self,
        diagnosis: AegisDiagnosis,
        operator: str = "auto",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Evaluate policy safety controls and dispatch recovery action for a diagnosis."""
        event_id = diagnosis.event_id
        f_type_str = diagnosis.failure_type.value if hasattr(diagnosis.failure_type, "value") else str(diagnosis.failure_type)
        policy = self.policies.get(f_type_str, self.policies.get("UNKNOWN_FAILURE", {}))

        retry_key = f"{event_id}:{diagnosis.recommended_remediation}"
        current_retries = self._retry_counts.get(retry_key, 0)

        # 1. Max Retry Limit Gate
        if current_retries >= self.max_retries:
            reason = f"Max retry limit ({self.max_retries}) reached for incident {event_id}"
            res = escalate(reason=reason, event_id=event_id)
            self._log_audit(event_id, "escalate", event_id, False, operator, res)
            return res

        # 2. Kernel / Driver Check for Approved Patch DB Mappings
        if f_type_str in (FailureType.KERNEL_ERROR.value, FailureType.DRIVER_FAILURE.value):
            evidence_text = " ".join(diagnosis.evidence)
            kernel_match = self.kernel_db.find_remediation_for_evidence(evidence_text)

            if kernel_match:
                if not kernel_match["admin_approved"] and operator == "auto":
                    reason = f"Kernel remediation '{kernel_match['signature_id']}' requires explicit admin approval."
                    res = escalate(reason=reason, event_id=event_id)
                    self._log_audit(event_id, "escalate", event_id, False, operator, res)
                    return res
                action_name = kernel_match["approved_action"]
                target = kernel_match["target"]
                self._retry_counts[retry_key] = current_retries + 1
                res = self._dispatch_action(action_name, target, policy, dry_run)
                self._log_audit(event_id, action_name, target, res.get("success", False), operator, res)
                return res

        # 3. Operator Auto-Remediate Gate
        if operator == "auto" and not policy.get("auto_remediate", False):
            reason = f"Auto-remediation disabled by policy for {f_type_str}"
            res = escalate(reason=reason, event_id=event_id)
            self._log_audit(event_id, "escalate", event_id, False, operator, res)
            return res

        # 4. Confidence Threshold Gate
        if operator == "auto" and diagnosis.confidence_score < self.auto_remediate_threshold:
            reason = f"Confidence score ({diagnosis.confidence_score:.2f}) below threshold ({self.auto_remediate_threshold:.2f})"
            res = escalate(reason=reason, event_id=event_id)
            self._log_audit(event_id, "escalate", event_id, False, operator, res)
            return res

        # 5. Determine Action Handler
        allowed_actions = policy.get("allowed_actions", ["escalate"])
        action_name = diagnosis.recommended_remediation

        if action_name not in allowed_actions:
            action_name = policy.get("default_action", "escalate")

        # Increment retry counter
        self._retry_counts[retry_key] = current_retries + 1

        # 6. Dispatch Action Execution
        target = self._extract_action_target(diagnosis, action_name, policy)
        result = self._dispatch_action(action_name, target, policy, dry_run)

        # 7. Audit Logging
        self._log_audit(event_id, action_name, target, result.get("success", False), operator, result)

        return result

    def _extract_action_target(self, diagnosis: AegisDiagnosis, action_name: str, policy: dict[str, Any]) -> str:
        """Extract appropriate action target from diagnosis evidence or policy config."""
        for ev in diagnosis.evidence:
            if "Service state '" in ev:
                start = ev.find("Service state '") + len("Service state '")
                end = ev.find("'", start)
                if end != -1:
                    return ev[start:end]

        if action_name == "cleanup_temp_files":
            cleanup_dirs = policy.get("cleanup_dirs", ["/tmp", "/var/tmp"])
            return ", ".join(cleanup_dirs)

        return diagnosis.event_id

    def _dispatch_action(
        self,
        action_name: str,
        target: str,
        policy: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        """Dispatch execution to specific recovery action handler."""
        if action_name == "restart_service":
            return restart_service(unit_name=target)

        if action_name == "cleanup_temp_files":
            cleanup_dirs = policy.get("cleanup_dirs", ["/tmp", "/var/tmp"])
            return cleanup_temp_files(dirs=cleanup_dirs)

        if action_name == "restore_configuration":
            return restore_configuration(target_path=target)

        if action_name == "apply_safe_sysctl":
            params = policy.get("sysctl_params", {"vm.swappiness": "10"})
            return apply_safe_sysctl(params)

        if action_name == "blacklist_module":
            return blacklist_module(module_name=target)

        if action_name == "reload_driver":
            return reload_driver(driver_name=target)

        if action_name == "apply_livepatch":
            return apply_livepatch(patch_name=target)

        return escalate(reason=f"Default escalation for action {action_name}", event_id=target)

    def _log_audit(
        self,
        event_id: str,
        action: str,
        target: str,
        success: bool,
        operator: str,
        details: dict[str, Any],
    ) -> None:
        try:
            self.audit_logger.log_remediation(
                event_id=event_id,
                action_name=action,
                target=target,
                success=success,
                operator=operator,
                details=details,
            )
        except Exception as exc:
            logger.error("Failed to write remediation audit log: %s", exc)
