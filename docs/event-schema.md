# AegisOS — Normalized Event Schema

**Phase 1, Task 4** — Canonical data structure for all detected incidents.

JSON Schema: [schemas/event.schema.json](./schemas/event.schema.json)

---

## Event Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | UUID string | Yes | Unique incident identifier |
| `timestamp` | ISO 8601 UTC | Yes | When the failure was detected |
| `failure_type` | enum | Yes | Failure classification (see below) |
| `source` | string | Yes | Monitor that raised the event |
| `severity` | enum | Yes | `INFO`, `WARNING`, or `CRITICAL` |
| `raw_evidence` | array | Yes | One or more evidence objects |
| `affected_unit` | string | No | systemd unit (e.g. `nginx.service`) |
| `affected_process` | string | No | Process name or PID |
| `tags` | string[] | No | Free-form labels for filtering |

---

## Failure Types

| Value | Typical source | Example trigger |
|-------|----------------|-----------------|
| `SERVICE_FAILURE` | systemctl, journalctl | Unit in `failed` state |
| `MEMORY_EXHAUSTION` | /proc, dmesg, journalctl | OOM killer, memory > threshold |
| `CPU_OVERLOAD` | /proc, psutil | Sustained CPU > threshold |
| `DISK_EXHAUSTION` | df, /proc/mounts | Filesystem usage > threshold |
| `KERNEL_ERROR` | dmesg, journalctl | I/O error, BUG, hung task |
| `DRIVER_FAILURE` | dmesg, /sys/module | Module load failure |
| `CONFIGURATION_ERROR` | journalctl, file check | Invalid config, parse error |
| `UNKNOWN_FAILURE` | any | Unclassified incident |

---

## Severity Levels

| Level | When to use |
|-------|-------------|
| `INFO` | Informational anomaly, no immediate action |
| `WARNING` | Degraded state, monitor closely |
| `CRITICAL` | Active failure requiring remediation or escalation |

---

## Evidence Object

Each item in `raw_evidence`:

```json
{
  "kind": "log_line",
  "data": {
    "message": "nginx.service: Main process exited, code=exited, status=1/FAILURE",
    "unit": "nginx.service",
    "priority": 3
  }
}
```

### Evidence kinds

| Kind | `data` fields (typical) |
|------|-------------------------|
| `log_line` | `message`, `unit`, `priority`, `timestamp` |
| `metric` | `name`, `value`, `unit`, `threshold` |
| `service_state` | `unit`, `active_state`, `result`, `n_restarts` |
| `process` | `pid`, `name`, `cpu_percent`, `memory_percent` |
| `file_excerpt` | `path`, `content`, `line_number` |

---

## Example Event

```json
{
  "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2026-08-29T08:00:00Z",
  "failure_type": "SERVICE_FAILURE",
  "source": "systemctl",
  "severity": "CRITICAL",
  "affected_unit": "nginx.service",
  "raw_evidence": [
    {
      "kind": "service_state",
      "data": {
        "unit": "nginx.service",
        "active_state": "failed",
        "result": "exit-code",
        "n_restarts": 3
      }
    },
    {
      "kind": "log_line",
      "data": {
        "message": "nginx.service: Failed with result 'exit-code'.",
        "unit": "nginx.service",
        "priority": 3
      }
    }
  ],
  "tags": ["systemd", "web-server"]
}
```

---

## Diagnosis Schema (RCA output)

Produced by the Root-Cause Analysis engine (Phase 5).  
JSON Schema: [schemas/diagnosis.schema.json](./schemas/diagnosis.schema.json)

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Links to source event |
| `failure_type` | enum | Confirmed or refined failure class |
| `probable_root_cause` | string | Human-readable diagnosis |
| `evidence` | string[] | Summarized evidence bullets |
| `confidence_score` | float 0–1 | Model + rule combined score |
| `recommended_remediation` | string | Action key from remediation policies |
| `risk_level` | enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |

---

## Python Usage

```python
from common.events import AegisEvent, FailureType, Severity, EvidenceKind

event = AegisEvent.create(
    failure_type=FailureType.SERVICE_FAILURE,
    source="systemctl",
    severity=Severity.CRITICAL,
    raw_evidence=[
        {"kind": "service_state", "data": {"unit": "nginx.service", "active_state": "failed"}}
    ],
    affected_unit="nginx.service",
)
print(event.to_dict())
```

---

## Related

- [config-format.md](./config-format.md) — thresholds and policies
- [system-interfaces.md](./system-interfaces.md) — data source reference
