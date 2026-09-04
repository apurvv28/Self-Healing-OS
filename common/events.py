"""Normalized event and diagnosis data structures for AegisOS."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class FailureType(StrEnum):
    SERVICE_FAILURE = "SERVICE_FAILURE"
    MEMORY_EXHAUSTION = "MEMORY_EXHAUSTION"
    CPU_OVERLOAD = "CPU_OVERLOAD"
    DISK_EXHAUSTION = "DISK_EXHAUSTION"
    KERNEL_ERROR = "KERNEL_ERROR"
    DRIVER_FAILURE = "DRIVER_FAILURE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceKind(StrEnum):
    LOG_LINE = "log_line"
    METRIC = "metric"
    SERVICE_STATE = "service_state"
    PROCESS = "process"
    FILE_EXCERPT = "file_excerpt"


@dataclass
class AegisEvent:
    """Normalized incident event emitted by the detection engine."""

    event_id: str
    timestamp: str
    failure_type: FailureType
    source: str
    severity: Severity
    raw_evidence: list[dict[str, Any]]
    affected_unit: str | None = None
    affected_process: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        failure_type: FailureType,
        source: str,
        severity: Severity,
        raw_evidence: list[dict[str, Any]],
        *,
        affected_unit: str | None = None,
        affected_process: str | None = None,
        tags: list[str] | None = None,
    ) -> AegisEvent:
        if not raw_evidence:
            raise ValueError("raw_evidence must contain at least one item")
        return cls(
            event_id=str(uuid4()),
            timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            failure_type=failure_type,
            source=source,
            severity=severity,
            raw_evidence=raw_evidence,
            affected_unit=affected_unit,
            affected_process=affected_process,
            tags=tags or [],
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failure_type"] = self.failure_type.value
        data["severity"] = self.severity.value
        return data


@dataclass
class AegisDiagnosis:
    """RCA output linking an event to a root cause and recommended action."""

    event_id: str
    failure_type: FailureType
    probable_root_cause: str
    evidence: list[str]
    confidence_score: float
    recommended_remediation: str
    risk_level: RiskLevel
    correlated_event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failure_type"] = self.failure_type.value
        data["risk_level"] = self.risk_level.value
        return data
