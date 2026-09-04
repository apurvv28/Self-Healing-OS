"""Temporal event correlation for AegisOS Root-Cause Analysis."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from common.events import AegisEvent

logger = logging.getLogger(__name__)


class TemporalCorrelator:
    """Correlates incidents and signals occurring within a sliding time window."""

    def __init__(self, default_window_seconds: int = 30) -> None:
        self.default_window_seconds = default_window_seconds

    @staticmethod
    def parse_timestamp(ts: str) -> datetime:
        """Parse ISO timestamp string into UTC datetime."""
        try:
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts).astimezone(UTC)
        except Exception:
            return datetime.now(UTC)

    def correlate_events(
        self,
        target_event: AegisEvent,
        candidates: list[AegisEvent],
        window_seconds: int | None = None,
    ) -> list[AegisEvent]:
        """Filter candidate events within ±window_seconds of target event timestamp."""
        window = window_seconds if window_seconds is not None else self.default_window_seconds
        target_dt = self.parse_timestamp(target_event.timestamp)

        correlated: list[tuple[float, AegisEvent]] = []
        for candidate in candidates:
            if candidate.event_id == target_event.event_id:
                continue

            cand_dt = self.parse_timestamp(candidate.timestamp)
            diff_seconds = abs((target_dt - cand_dt).total_seconds())

            if diff_seconds <= window:
                correlated.append((diff_seconds, candidate))

        # Sort candidates by temporal proximity
        correlated.sort(key=lambda item: item[0])
        return [item[1] for item in correlated]

    def bundle_evidence(
        self,
        target_event: AegisEvent,
        correlated_events: list[AegisEvent],
    ) -> dict[str, Any]:
        """Aggregate evidence records and unique evidence bullet strings across events."""
        all_events = [target_event] + correlated_events
        raw_evidence_records: list[dict[str, Any]] = []
        evidence_bullets: list[str] = []
        evidence_kinds: set[str] = set()

        for ev in all_events:
            for item in ev.raw_evidence:
                raw_evidence_records.append(item)
                kind = item.get("kind", "unknown")
                evidence_kinds.add(kind)

                # Format human-readable bullet
                if kind == "log_line":
                    msg = item.get("message") or item.get("log_entry", {}).get("message") or str(item)
                    evidence_bullets.append(f"Log [{item.get('source', 'log')}]: {msg}")
                elif kind == "metric":
                    m_name = item.get("metric_name", "metric")
                    val = item.get("value", "N/A")
                    evidence_bullets.append(f"Metric '{m_name}': {val}% (Threshold breached)")
                elif kind == "service_state":
                    unit = item.get("unit", "service")
                    state = item.get("active_state", "unknown")
                    restarts = item.get("restarts", 0)
                    evidence_bullets.append(f"Service state '{unit}': {state} (restarts: {restarts})")
                elif kind == "process":
                    procs = item.get("top_processes", [])
                    if procs:
                        top = procs[0]
                        evidence_bullets.append(f"Top process: {top.get('name')} (PID {top.get('pid')}) CPU {top.get('cpu_percent')}%")
                else:
                    evidence_bullets.append(f"Evidence [{kind}]: {str(item)}")

        # Deduplicate bullet strings preserving order
        unique_bullets = list(dict.fromkeys(evidence_bullets))

        return {
            "raw_records": raw_evidence_records,
            "bullets": unique_bullets,
            "distinct_kinds": list(evidence_kinds),
            "kind_count": len(evidence_kinds),
        }
