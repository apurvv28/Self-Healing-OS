"""AI Failure Classifier API for AegisOS triage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import joblib

from common.events import FailureType

logger = logging.getLogger(__name__)


class FailureClassifier:
    """Classifies system failures using trained ML models with rule-based fallback."""

    def __init__(
        self,
        model_path: str | Path = "ai/models/failure_classifier.joblib",
        confidence_threshold: float = 0.60,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_absolute():
            self.model_path = Path.cwd() / self.model_path

        self.confidence_threshold = confidence_threshold
        self.pipeline: Any = None
        self.is_trained = False

        self._load_model()

    def _load_model(self) -> None:
        """Load trained scikit-learn pipeline artifact if available."""
        if self.model_path.exists():
            try:
                self.pipeline = joblib.load(self.model_path)
                self.is_trained = True
                logger.info("Successfully loaded ML model from %s", self.model_path)
            except Exception as exc:
                logger.warning("Failed to load ML model from %s: %s", self.model_path, exc)
                self.is_trained = False
        else:
            logger.info("Model file %s not found. Classifier running in rule-fallback mode.", self.model_path)

    def extract_text_from_evidence(self, evidence: list[dict[str, Any]] | str) -> str:
        """Extract plain log text from evidence bundle or raw input string."""
        if isinstance(evidence, str):
            return evidence

        lines: list[str] = []
        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, dict):
                    if "message" in item:
                        lines.append(str(item["message"]))
                    elif "log_entry" in item:
                        entry = item["log_entry"]
                        if isinstance(entry, dict) and "message" in entry:
                            lines.append(str(entry["message"]))
                        else:
                            lines.append(str(entry))
                    elif "unit" in item:
                        lines.append(f"service {item.get('unit')} state {item.get('active_state')}")

        return " ".join(lines) if lines else "unknown system event log"

    def classify_evidence(self, evidence: list[dict[str, Any]] | str) -> dict[str, Any]:
        """Classify log evidence returning predicted FailureType and confidence score."""
        log_text = self.extract_text_from_evidence(evidence)

        if self.is_trained and self.pipeline is not None:
            try:
                probs = self.pipeline.predict_proba([log_text])[0]
                classes = self.pipeline.classes_

                max_idx = int(probs.argmax())
                predicted_class = str(classes[max_idx])
                confidence = float(probs[max_idx])

                if confidence >= self.confidence_threshold:
                    return {
                        "failure_type": predicted_class,
                        "confidence": confidence,
                        "fallback_used": False,
                        "source": "ml_classifier",
                        "log_text": log_text,
                    }

                logger.info(
                    "Model confidence (%.2f) below threshold (%.2f). Triggering rule fallback.",
                    confidence,
                    self.confidence_threshold,
                )
            except Exception as exc:
                logger.error("Inference error in ML classifier: %s", exc)

        # Rule-based fallback
        fallback_class, fallback_conf = self._rule_fallback(log_text)
        return {
            "failure_type": fallback_class,
            "confidence": fallback_conf,
            "fallback_used": True,
            "source": "rule_fallback",
            "log_text": log_text,
        }

    def _rule_fallback(self, log_text: str) -> tuple[str, float]:
        """Simple rule fallback when model confidence is low or model is missing."""
        text_lower = log_text.lower()
        if "out of memory" in text_lower or "oom-killer" in text_lower or "heap space" in text_lower:
            return FailureType.MEMORY_EXHAUSTION.value, 0.85
        if "cpu" in text_lower or "lockup" in text_lower or "load average" in text_lower:
            return FailureType.CPU_OVERLOAD.value, 0.80
        if "no space left" in text_lower or "disk" in text_lower or "i/o error" in text_lower:
            return FailureType.DISK_EXHAUSTION.value, 0.85
        if "segfault" in text_lower or "kernel panic" in text_lower or "null pointer" in text_lower:
            return FailureType.KERNEL_ERROR.value, 0.90
        if "driver" in text_lower or "gpu" in text_lower or "firmware" in text_lower:
            return FailureType.DRIVER_FAILURE.value, 0.80
        if "configuration" in text_lower or "syntax error" in text_lower or "config" in text_lower:
            return FailureType.CONFIGURATION_ERROR.value, 0.80
        if "failed" in text_lower or "exit-code" in text_lower or "service" in text_lower:
            return FailureType.SERVICE_FAILURE.value, 0.75

        return FailureType.UNKNOWN_FAILURE.value, 0.50

    def get_model_info(self) -> dict[str, Any]:
        """Fetch model metadata summary."""
        metadata_path = self.model_path.parent / "model_metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return {
            "is_trained": self.is_trained,
            "model_path": str(self.model_path),
            "confidence_threshold": self.confidence_threshold,
        }
