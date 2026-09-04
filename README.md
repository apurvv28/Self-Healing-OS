# AegisOS — AI-Assisted Self-Healing Linux OS

AegisOS is an AI-assisted self-healing Linux operating system prototype that automatically detects, diagnoses, and recovers from common system failures.

**Core workflow:** Detect → Diagnose → Decide → Remediate → Verify → Escalate

## Documentation

| Document | Description |
|----------|-------------|
| [overview.md](./overview.md) | Full project overview, architecture, and features |
| [action-plan.md](./action-plan.md) | 10-phase implementation plan |
| [docs/coding-conventions.md](./docs/coding-conventions.md) | Python style and logging standards |

## Project Structure

```text
monitor/        Real-time OS monitoring
detector/       Failure detection engine
ai/             ML classifier & triage
rca/            Root-cause analysis
remediation/    Recovery policy engine
verification/   Post-remediation health checks
kdump/          Kernel crash analysis
dashboard/      Web UI & API
common/         Shared utilities
config/         Configuration files
tests/          Test suite
docs/           Documentation
```

## Prerequisites

- **Host:** Windows or Linux with VirtualBox or VMware
- **Target VM:** Ubuntu LTS 22.04 or 24.04 (≥ 4 GB RAM, ≥ 40 GB disk)
- **Python:** 3.10 or newer (on host for development; on VM for runtime)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd Self-Healing-OS
```

### 2. Create a virtual environment

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure logging (optional)

```python
from pathlib import Path
from common.logging_config import setup_logging

setup_logging(level="INFO", log_file=Path("logs/aegisos.log"))
```

### 5. Prepare the Ubuntu VM

See [action-plan.md — Phase 1, Task 2](./action-plan.md) for VM provisioning steps. AegisOS monitoring and remediation run on the Ubuntu target VM.

## Development Status

| Phase | Status |
|-------|--------|
| 1 — Project Foundation | In progress |
| 2 — Monitoring Layer | Not started |
| 3 — Failure Detection | Not started |
| 4 — AI Classifier | Not started |
| 5 — Root-Cause Analysis | Not started |
| 6 — Remediation Engine | Not started |
| 7 — Recovery Verification | Not started |
| 8 — kdump Analysis | Not started |
| 9 — Advanced Kernel (optional) | Not started |
| 10 — Dashboard & Demo | Not started |

## Running Tests

```bash
pytest tests/
```

Integration tests that require the Ubuntu VM:

```bash
pytest tests/ -m integration
```

## License

Academic project — VIT Semester 5, Operating Systems.
