"""Tests for FastAPI backend REST API endpoints."""

from fastapi.testclient import TestClient

from dashboard.api import app

client = TestClient(app)


def test_get_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "AegisOS" in response.text


def test_get_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "system_metrics" in data
    assert "monitored_services" in data


def test_get_incidents():
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_metrics():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_incidents" in data
    assert "remediation_success_rate_pct" in data


def test_trigger_scenario_endpoint():
    response = client.post("/api/trigger-scenario?scenario_type=service_failure")
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_type"] == "service_failure"
    assert "detected_count" in data


def test_run_cycle_endpoint():
    response = client.post("/api/run-cycle")
    assert response.status_code == 200
    data = response.json()
    assert "processed_count" in data
