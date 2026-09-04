"""Tests for SelfHealingLoop module."""

from tests.scenarios import generate_mock_service_failure_telemetry
from verification.loop import SelfHealingLoop


def test_self_healing_loop_end_to_end_cycle():
    loop = SelfHealingLoop(config_path="config/aegisos.yaml")
    telemetry = generate_mock_service_failure_telemetry(unit_name="crashed-app.service")

    results = loop.run_cycle(telemetry=telemetry, operator="auto")

    assert len(results) == 1
    res = results[0]
    assert "event_id" in res
    assert res["failure_type"] == "SERVICE_FAILURE"
    assert "diagnosis" in res
    assert "remediation" in res
    assert "verification" in res
    assert res["verification"]["recovered"] is True
