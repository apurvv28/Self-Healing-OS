# AegisOS — Coding Conventions & Logging Standards

This document defines shared conventions for all Python modules in the AegisOS project.

---

## Project Layout

```text
Self-Healing-OS/
├── monitor/        # Real-time OS monitoring (Phase 2)
├── detector/       # Failure detection engine (Phase 3)
├── ai/             # ML classifier & triage (Phase 4)
├── rca/            # Root-cause analysis (Phase 5)
├── remediation/    # Recovery policy engine (Phase 6)
├── verification/   # Post-remediation health checks (Phase 7)
├── kdump/          # Kernel crash analysis (Phase 8)
├── dashboard/      # Web UI & API (Phase 10)
├── common/         # Shared utilities (logging, helpers)
├── config/         # YAML/JSON configuration files
├── tests/          # Unit and integration tests
└── docs/           # Project documentation
```

Each Python package directory must contain an `__init__.py`.

---

## Python Style

| Rule | Convention |
|------|------------|
| Python version | 3.10+ |
| Formatter | Follow PEP 8; 88–100 char line length |
| Naming — modules | `snake_case.py` |
| Naming — classes | `PascalCase` |
| Naming — functions/vars | `snake_case` |
| Naming — constants | `UPPER_SNAKE_CASE` |
| Type hints | Required on all public functions and methods |
| Docstrings | Required on public modules, classes, and functions |
| Imports | Standard library → third-party → local; one blank line between groups |

### Module Header Pattern

Every module should start with a one-line docstring describing its purpose:

```python
"""Collects systemd service state from journald and systemctl."""
```

### Error Handling

- Catch specific exceptions; avoid bare `except:`.
- Log errors with context before re-raising or returning a failure result.
- Never silently swallow failures in monitoring or remediation paths.

---

## Logging Standards

All modules must use the shared logging utility in `common/logging_config.py`.

### Setup (once at entry point)

```python
from pathlib import Path
from common.logging_config import setup_logging

setup_logging(level="INFO", log_file=Path("logs/aegisos.log"))
```

### Per-module logger

```python
from common.logging_config import get_logger

logger = get_logger(__name__)
```

### Log Levels

| Level | When to use |
|-------|-------------|
| `DEBUG` | Polling intervals, raw data samples, internal state |
| `INFO` | Normal operations: startup, detection, remediation success |
| `WARNING` | Recoverable issues: retries, low confidence, threshold breaches |
| `ERROR` | Failed actions, permission errors, unexpected exceptions |
| `CRITICAL` | System-wide failures requiring immediate escalation |

### Log Message Format

Use structured, actionable messages:

```python
# Good
logger.info("Service restart succeeded: unit=%s attempt=%d", unit, attempt)
logger.warning("Confidence below threshold: score=%.2f threshold=%.2f", score, threshold)

# Avoid
logger.info("done")
logger.error("something went wrong")
```

### Required Log Context for Key Events

| Event | Required fields |
|-------|-----------------|
| Failure detected | `event_id`, `failure_type`, `source`, `severity` |
| Diagnosis produced | `event_id`, `root_cause`, `confidence` |
| Remediation executed | `event_id`, `action`, `target`, `result` |
| Verification result | `event_id`, `recovered`, `mttr_seconds` |
| Escalation | `event_id`, `reason`, `retry_count` |

---

## Configuration

- Store runtime config in `config/` as YAML files.
- Do not hardcode thresholds, paths, or policy values in module code.
- Load config at startup; pass config objects into components rather than reading files repeatedly.

---

## Testing

- Place tests in `tests/` mirroring the source package structure.
- Name test files `test_<module>.py`.
- Use pytest; mark integration tests that require the Ubuntu VM with `@pytest.mark.integration`.

---

## Security & Safety

- Remediation modules must log every action before execution.
- Never execute shell commands with unsanitized user input.
- Kernel-level operations require explicit config enablement (disabled by default).
