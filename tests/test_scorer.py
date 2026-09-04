"""Tests for ConfidenceScorer module."""

from common.events import AegisEvent, EvidenceKind, FailureType, Severity
from rca.scorer import ConfidenceScorer


def test_confidence_scoring_and_policy():
    scorer = ConfidenceScorer(config_path="config/aegisos.yaml")

    event = AegisEvent.create(
        failure_type=FailureType.SERVICE_FAILURE,
        source="systemd",
        severity=Severity.CRITICAL,
        raw_evidence=[{"kind": EvidenceKind.SERVICE_STATE.value, "unit": "apache2"}],
        affected_unit="apache2",
    )

    ml_info = {"confidence": 0.95}
    evidence_bundle = {"kind_count": 3}

    score = scorer.calculate_confidence(event, ml_info, evidence_bundle)
    assert 0.85 <= score <= 1.00

    policy = scorer.evaluate_policy(score)
    assert policy == "AUTO_REMEDIATION_ELIGIBLE"


def test_evaluate_policy_escalate():
    scorer = ConfidenceScorer(config_path="config/aegisos.yaml")

    assert scorer.evaluate_policy(0.50) == "LOG_AND_ESCALATE"
    assert scorer.evaluate_policy(0.80) == "RECOMMEND_REMEDIATION"
    assert scorer.evaluate_policy(0.95) == "AUTO_REMEDIATION_ELIGIBLE"
