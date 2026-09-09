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


@app.get("/api/logs/stream")
def get_log_stream(limit: int = Query(default=20, ge=1, le=100)) -> list[dict[str, Any]]:
    """Fetch chronologically unified log events for live dashboard terminal streaming."""
    events: list[dict[str, Any]] = []

    # Fetch recent incidents
    incidents = storage.get_recent_incidents(limit=limit)
    for inc in incidents:
        events.append({
            "timestamp": inc.get("timestamp"),
            "level": "WARN" if inc.get("severity") in ("CRITICAL", "WARNING") else "INFO",
            "module": "DETECTOR",
            "message": f"[{inc.get('severity')}] {inc.get('failure_type')} detected on {inc.get('affected_unit') or inc.get('affected_process') or 'system'}",
            "event_id": inc.get("event_id"),
        })

    # Fetch recent remediations
    remediations = audit_logger.get_audit_history(limit=limit)
    for rem in remediations:
        status_symbol = "✅" if rem.get("post_health_status") in ("HEALTHY", "PASSED", True) else "⚙️"
        events.append({
            "timestamp": rem.get("executed_at") or rem.get("timestamp"),
            "level": "SUCCESS" if rem.get("action_status") == "SUCCESS" else "INFO",
            "module": "REMEDIATION",
            "message": f"{status_symbol} Executed action '{rem.get('action_name')}' (Status: {rem.get('action_status')}, MTTR: {rem.get('mttr_seconds', 0.0):.2f}s)",
            "event_id": rem.get("event_id"),
        })

    # Sort chronologically by timestamp
    events.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    return events[:limit]


@app.get("/api/rca/latest")
def get_latest_rca_graph() -> dict[str, Any]:
    """Fetch graph nodes and edges representing the root cause chain of the most recent incident."""
    incidents = storage.get_recent_incidents(limit=1)
    if not incidents:
        return {
            "incident": None,
            "nodes": [
                {"id": "sys", "label": "System Normal", "type": "status", "status": "healthy"}
            ],
            "edges": [],
        }

    latest = incidents[0]
    event_id = latest.get("event_id")
    event_obj = storage.get_incident_by_id(event_id)

    # Perform diagnosis if RCA details exist
    diagnosis = None
    if event_obj:
        try:
            # Reconstruct event for RCA engine
            from common.events import SystemFailureEvent
            system_event = SystemFailureEvent.from_dict(event_obj)
            diagnosis = rca_engine.diagnose(system_event)
        except Exception as exc:
            logger.warning("RCA graph diagnosis generation failed: %s", exc)

    # Fetch remediation if available
    rem_list = audit_logger.get_audit_history(limit=1, event_id=event_id)
    rem_action = rem_list[0] if rem_list else None

    # Construct graph structure for visualization
    nodes = [
        {
            "id": "node-telemetry",
            "label": f"Alert: {latest.get('failure_type')}",
            "sub": f"Severity: {latest.get('severity')}",
            "status": "danger",
        },
        {
            "id": "node-ai",
            "label": "AI Classifier Triage",
            "sub": f"Category: {latest.get('failure_type')}",
            "status": "warning",
        },
        {
            "id": "node-rca",
            "label": diagnosis.get("root_cause", "Root Cause Analysis") if diagnosis else "Root Cause Analysis",
            "sub": f"Target: {latest.get('affected_unit') or latest.get('affected_process') or 'Kernel/OS'}",
            "status": "info",
        },
        {
            "id": "node-remediation",
            "label": f"Action: {rem_action.get('action_name') if rem_action else 'Automated Recovery'}",
            "sub": f"Status: {rem_action.get('action_status') if rem_action else 'Completed'}",
            "status": "success",
        },
        {
            "id": "node-verification",
            "label": "Health Verified",
            "sub": f"MTTR: {rem_action.get('mttr_seconds', 0.0):.2f}s" if rem_action else "Verified Active",
            "status": "healthy",
        },
    ]

    edges = [
        {"from": "node-telemetry", "to": "node-ai", "label": "Ingested"},
        {"from": "node-ai", "to": "node-rca", "label": "Triaged"},
        {"from": "node-rca", "to": "node-remediation", "label": "Resolved"},
        {"from": "node-remediation", "to": "node-verification", "label": "Verified"},
    ]

    return {
        "incident": latest,
        "diagnosis": diagnosis,
        "nodes": nodes,
        "edges": edges,
    }


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

