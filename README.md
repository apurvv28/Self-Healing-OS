# AegisOS — AI-Assisted Self-Healing Linux OS

AegisOS is an AI-assisted self-healing Linux operating system prototype that automatically detects, diagnoses, and recovers from common system failures.

**Core workflow:** Detect → Diagnose → Decide → Remediate → Verify → Escalate

## Documentation

| Document | Description |
|----------|-------------|
| [overview.md](./overview.md) | Full project overview, architecture, and features |
| [action-plan.md](./action-plan.md) | 10-phase implementation plan |
| [docs/coding-conventions.md](./docs/coding-conventions.md) | Python style and logging standards |
| [docs/environment-setup.md](./docs/environment-setup.md) | WSL2 setup (primary) and environment comparison |
| [docs/system-interfaces.md](./docs/system-interfaces.md) | Monitoring targets: journalctl, systemctl, dmesg, /proc, /sys |
| [docs/event-schema.md](./docs/event-schema.md) | Normalized event and diagnosis schema |
| [docs/config-format.md](./docs/config-format.md) | YAML configuration reference |
| [docs/aws-fallback-setup.md](./docs/aws-fallback-setup.md) | AWS EC2 for kdump labs (Phase 8+) |

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

- **Host:** Windows with WSL2 (recommended) or Linux
- **Target environment:** WSL2 Ubuntu for Phases 1–7 and 10; AWS EC2 for Phase 8 kdump labs only
- **Python:** 3.10 or newer inside WSL

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

### 5. Set up WSL2 Ubuntu (primary environment)

From WSL:

```bash
cd "/mnt/d/VIT/Sem 5/Operating System/Self-Healing-OS"
bash scripts/setup-wsl.sh
```

See [docs/environment-setup.md](./docs/environment-setup.md) for full details. For kdump/kernel labs (Phase 8), use [docs/aws-fallback-setup.md](./docs/aws-fallback-setup.md).

## Development Status

| Phase | Status |
|-------|--------|
| 1 — Project Foundation | Complete |
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
