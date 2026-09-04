"""Unified AegisOS Agent CLI tool and daemon entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import Any

import uvicorn

from common.config_loader import load_config
from common.logging_config import setup_logging
from dashboard.api import app
from detector.storage import IncidentStorage
from monitor.daemon import MonitoringDaemon
from tests.scenarios import (
    generate_mock_cpu_overload_telemetry,
    generate_mock_disk_exhaustion_telemetry,
    generate_mock_kernel_oom_telemetry,
    generate_mock_service_failure_telemetry,
)
from verification.loop import SelfHealingLoop
from verification.metrics import MetricsTracker

logger = logging.getLogger("aegis.agent")


def cmd_status(args: argparse.Namespace) -> None:
    """Print current OS health telemetry snapshot and alerts."""
    daemon = MonitoringDaemon(config_path=args.config)
    snapshot = daemon.collect_telemetry_snapshot()

    metrics = snapshot["system_metrics"]
    cpu_pct = metrics["cpu"]["total_percent"]
    mem_pct = metrics["memory"]["used_percent"]
    alerts = snapshot["threshold_alerts"]

    print("=" * 60)
    print(" AegisOS — System Status Summary")
    print("=" * 60)
    print(f" Timestamp:      {snapshot['timestamp']}")
    print(f" CPU Usage:      {cpu_pct:.1f}%")
    print(f" Memory Usage:   {mem_pct:.1f}%")
    print(f" Active Alerts:  {len(alerts)}")
    print("-" * 60)

    if alerts:
        print(" Active Threshold Alerts:")
        for a in alerts:
            print(f"  - [{a['severity']}] {a['type']}: {a['message']}")
    else:
        print(" All systems operating within normal parameters.")
    print("=" * 60)


def cmd_incidents(args: argparse.Namespace) -> None:
    """Print recent recorded incidents."""
    storage = IncidentStorage()
    incidents = storage.get_recent_incidents(limit=args.limit)

    print("=" * 70)
    print(f" AegisOS — Recent Incident Audit Log (Last {len(incidents)})")
    print("=" * 70)
    if not incidents:
        print(" No incidents recorded in database.")
    else:
        print(f"{'TIMESTAMP':<20} | {'FAILURE TYPE':<20} | {'SEVERITY':<10} | {'TARGET'}")
        print("-" * 70)
        for inc in incidents:
            ts = inc["timestamp"]
            f_type = inc["failure_type"]
            sev = inc["severity"]
            target = inc.get("affected_unit") or inc.get("affected_process") or "-"
            print(f"{ts:<20} | {f_type:<20} | {sev:<10} | {target}")
    print("=" * 70)


def cmd_metrics(args: argparse.Namespace) -> None:
    """Print system performance metrics summary."""
    tracker = MetricsTracker()
    summary = tracker.get_metrics_summary()

    print("=" * 60)
    print(" AegisOS — Self-Healing Metrics & MTTR Summary")
    print("=" * 60)
    print(f" Total Incidents Detected:    {summary['total_incidents']}")
    print(f" Total Remediation Attempts:  {summary['total_remediations']}")
    print(f" Successful Recoveries:       {summary['successful_remediations']}")
    print(f" Success Rate:                {summary['remediation_success_rate_pct']:.1f}%")
    print(f" Average MTTR:                {summary['average_mttr_seconds']:.2f}s")
    print("=" * 60)


def cmd_trigger_scenario(args: argparse.Namespace) -> None:
    """Trigger a controlled failure test scenario."""
    loop = SelfHealingLoop(config_path=args.config)

    s_type = args.type
    if s_type == "service_failure":
        telemetry = generate_mock_service_failure_telemetry()
    elif s_type == "cpu_overload":
        telemetry = generate_mock_cpu_overload_telemetry()
    elif s_type == "memory_exhaustion":
        telemetry = generate_mock_kernel_oom_telemetry()
    elif s_type == "disk_exhaustion":
        telemetry = generate_mock_disk_exhaustion_telemetry()
    else:
        telemetry = generate_mock_service_failure_telemetry()

    print(f"Triggering failure scenario '{s_type}'...")
    results = loop.run_cycle(telemetry=telemetry, operator="auto")

    print(f"Scenario complete! Processed {len(results)} incident(s).")
    for r in results:
        print(f" - Incident {r['event_id']}: Failure='{r['failure_type']}', Action='{r['remediation'].get('action')}', Recovered={r['verification']['recovered']}")


def cmd_run_cycle(args: argparse.Namespace) -> None:
    """Run a single self-healing loop cycle."""
    loop = SelfHealingLoop(config_path=args.config)
    print("Executing single self-healing cycle...")
    results = loop.run_cycle(operator="auto")
    print(f"Cycle finished. Handled {len(results)} incident(s).")


def cmd_serve(args: argparse.Namespace) -> None:
    """Start FastAPI Web Backend and Interactive Dashboard Server."""
    print(f"Starting AegisOS Dashboard Web Server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


def cmd_daemon(args: argparse.Namespace) -> None:
    """Run continuous self-healing daemon loop."""
    cfg = load_config(args.config)
    setup_logging(cfg.get("aegisos", {}).get("log_level", "INFO"))
    loop = SelfHealingLoop(config_path=args.config)

    interval = cfg.get("monitoring", {}).get("poll_interval_seconds", 10)
    logger.info("Starting AegisOS Continuous Agent Daemon (poll interval: %ds)...", interval)

    try:
        while True:
            loop.run_cycle(operator="auto")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("AegisOS Agent Daemon stopped by user.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisOS Unified Agent CLI & Daemon")
    parser.add_argument("--config", default="config/aegisos.yaml", help="Path to config file")

    subparsers = parser.add_subparsers(dest="command", help="Available agent commands")

    # Command: status
    subparsers.add_parser("status", help="Display current system health and active alerts")

    # Command: incidents
    p_inc = subparsers.add_parser("incidents", help="Display recent recorded incidents")
    p_inc.add_argument("--limit", type=int, default=20, help="Number of incidents to display")

    # Command: metrics
    subparsers.add_parser("metrics", help="Display self-healing success rate and MTTR metrics")

    # Command: trigger-scenario
    p_scen = subparsers.add_parser("trigger-scenario", help="Trigger a controlled failure test scenario")
    p_scen.add_argument("--type", choices=["service_failure", "cpu_overload", "memory_exhaustion", "disk_exhaustion"], default="service_failure")

    # Command: run-cycle
    subparsers.add_parser("run-cycle", help="Execute single self-healing cycle")

    # Command: serve
    p_serve = subparsers.add_parser("serve", help="Start FastAPI REST server and web dashboard")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host address")
    p_serve.add_argument("--port", type=int, default=8000, help="Port number")

    # Command: daemon
    subparsers.add_parser("daemon", help="Run continuous self-healing daemon loop")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "incidents":
        cmd_incidents(args)
    elif args.command == "metrics":
        cmd_metrics(args)
    elif args.command == "trigger-scenario":
        cmd_trigger_scenario(args)
    elif args.command == "run-cycle":
        cmd_run_cycle(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "daemon":
        cmd_daemon(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
