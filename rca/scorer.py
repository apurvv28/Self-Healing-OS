"""Multi-signal confidence scoring and policy mapping for AegisOS RCA."""

from __future__ import annotations

import logging
from typing import Any

from common.config_loader import load_config
from common.events import AegisEvent, Severity

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Calculates weighted multi-signal confidence scores and evaluates remediation policies."""

    def __init__(self, config_path: str = "config/aegisos.yaml") -> None:
        self.config = load_config(config_path)
        conf_cfg = self.config.get("confidence", {}).get("confidence", {})

        self.escalate_below = conf_cfg.get("escalate_below", 0.70)
        self.recommend_below = conf_cfg.get("recommend_below", 0.90)
        self.auto_remediate_at = conf_cfg.get("auto_remediate_at", 0.90)
        self.min_evidence_count = conf_cfg.get("min_evidence_count", 2)

    def calculate_confidence(
        self,
        event: AegisEvent,
        ml_info: dict[str, Any],
        evidence_bundle: dict[str, Any],
    ) -> float:
        """Calculate composite confidence score combining ML, signal diversity, and rule specificity."""
        # 1. Base ML / Rule Classifier Score (Weight: 40%)
        ml_conf = float(ml_info.get("confidence", 0.70))

        # 2. Corroborating Signal Diversity (Weight: 35%)
        distinct_kinds = evidence_bundle.get("kind_count", 1)
        if distinct_kinds >= 3:
            diversity_score = 1.00
        elif distinct_kinds == 2:
            diversity_score = 0.80
        else:
            diversity_score = 0.50

        # 3. Rule Specificity & Specific Target Attributes (Weight: 25%)
        has_target = bool(event.affected_unit or event.affected_process)
        if has_target and event.severity == Severity.CRITICAL:
            specificity_score = 1.00
        elif has_target or event.severity == Severity.CRITICAL:
            specificity_score = 0.85
        else:
            specificity_score = 0.60

        # Composite score calculation
        composite = (0.40 * ml_conf) + (0.35 * diversity_score) + (0.25 * specificity_score)
        clamped = max(0.0, min(1.0, composite))
        return round(clamped, 2)

    def evaluate_policy(self, confidence: float) -> str:
        """Map confidence score to policy action."""
        if confidence < self.escalate_below:
            return "LOG_AND_ESCALATE"
        elif confidence < self.recommend_below:
            return "RECOMMEND_REMEDIATION"
        else:
            return "AUTO_REMEDIATION_ELIGIBLE"
