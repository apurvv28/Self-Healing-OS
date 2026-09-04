"""Tests for FailureClassifier API module."""

from ai.classifier import FailureClassifier
from common.events import FailureType


def test_classifier_inference_with_trained_model():
    classifier = FailureClassifier(model_path="ai/models/failure_classifier.joblib")

    # ML Model Inference Test
    res1 = classifier.classify_evidence("systemd[1]: apache2.service: Main process exited, code=exited, status=1/FAILURE")
    assert res1["failure_type"] == FailureType.SERVICE_FAILURE.value
    assert res1["confidence"] > 0.60
    assert res1["fallback_used"] is False
    assert res1["source"] == "ml_classifier"

    # Rule Fallback Test (when model path missing)
    dummy_classifier = FailureClassifier(model_path="non_existent/model.joblib")

    res2 = dummy_classifier.classify_evidence("kernel: [ 1234.567] Out of memory: Kill process 9999 (mysqld)")
    assert res2["failure_type"] == FailureType.MEMORY_EXHAUSTION.value
    assert res2["fallback_used"] is True
    assert res2["source"] == "rule_fallback"
