"""FastAPI REST backend and web dashboard server for AegisOS."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from common.config_loader import load_config
from detector.engine import DetectionEngine
from detector.storage import IncidentStorage
from monitor.daemon import MonitoringDaemon
from rca.engine import RCAEngine
from remediation.audit import RemediationAuditLogger
from remediation.engine import RemediationEngine
from tests.scenarios import (
    generate_mock_cpu_overload_telemetry,
    generate_mock_disk_exhaustion_telemetry,
    generate_mock_kernel_oom_telemetry,
    generate_mock_service_failure_telemetry,
)
from verification.loop import SelfHealingLoop
from verification.metrics import MetricsTracker

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AegisOS REST API",
    description="API endpoints for AegisOS self-healing telemetry, incidents, RCA, remediation, and metrics.",
    version="1.0.0",
)

# Mount static files directory
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Shared module initializations
config = load_config()
daemon = MonitoringDaemon()
storage = IncidentStorage()
detector = DetectionEngine(storage=storage)
rca_engine = RCAEngine()
audit_logger = RemediationAuditLogger()
remediation_engine = RemediationEngine(audit_logger=audit_logger)
metrics_tracker = MetricsTracker()
healing_loop = SelfHealingLoop()


@app.get("/", response_class=HTMLResponse)
def get_dashboard() -> HTMLResponse:
    """Serve single-page HTML Web Dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>AegisOS REST API is running. index.html not found.</h1>")


@app.get("/api/health")
def get_health() -> dict[str, Any]:
    """Get live system health telemetry snapshot."""
    return daemon.collect_telemetry_snapshot()


@app.get("/api/incidents")
def list_incidents(
    limit: int = Query(default=50, ge=1, le=200),
    failure_type: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent recorded incidents from SQLite database."""
    return storage.get_recent_incidents(limit=limit, failure_type=failure_type)


@app.get("/api/incidents/{event_id}")
def get_incident_detail(event_id: str) -> dict[str, Any]:
    """Fetch single incident details and RCA diagnosis."""
    incident = storage.get_incident_by_id(event_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident '{event_id}' not found")
    return incident


@app.get("/api/remediations")
def list_remediations(
    limit: int = Query(default=50, ge=1, le=200),
    event_id: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch remediation audit log history."""
    return audit_logger.get_audit_history(limit=limit, event_id=event_id)


@app.get("/api/metrics")
def get_metrics() -> dict[str, Any]:
    """Get system metrics summary (MTTR, success rates, failure distributions)."""
    return metrics_tracker.get_metrics_summary()


@app.post("/api/trigger-scenario")
def trigger_scenario(scenario_type: str = "service_failure") -> dict[str, Any]:
    """Inject a controlled failure telemetry scenario into the detection engine."""
    if scenario_type == "service_failure":
        telemetry = generate_mock_service_failure_telemetry()
    elif scenario_type == "cpu_overload":
        telemetry = generate_mock_cpu_overload_telemetry()
    elif scenario_type == "memory_exhaustion":
        telemetry = generate_mock_kernel_oom_telemetry()
    elif scenario_type == "disk_exhaustion":
        telemetry = generate_mock_disk_exhaustion_telemetry()
    else:
        telemetry = generate_mock_service_failure_telemetry()

    detected = detector.process_telemetry(telemetry)
    return {
        "scenario_type": scenario_type,
        "detected_count": len(detected),
        "detected_incidents": [e.to_dict() for e in detected],
    }


@app.post("/api/run-cycle")
def run_healing_cycle() -> dict[str, Any]:
    """Trigger a complete end-to-end self-healing cycle."""
    results = healing_loop.run_cycle(operator="auto")
    return {
        "processed_count": len(results),
        "cycle_results": results,
    }
