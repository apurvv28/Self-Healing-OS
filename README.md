# AegisOS — AI-Assisted Self-Healing Linux OS

AegisOS is an AI-assisted, self-healing Linux operating system framework that automatically detects, diagnoses, remediates, and verifies system failures in real time. Designed for high-availability Linux environments, AegisOS combines heuristic rule evaluation, machine learning event classification, automated root-cause analysis (RCA), and policy-driven recovery execution to maintain target operational availability without manual intervention.

---

## Architecture & Self-Healing Pipeline

```text
               +----------------------------------+
               | Real-Time Telemetry & Log Ingest |
               |   (procfs, sysfs, journalctl)    |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |     Failure Detection Engine     |
               | (Rule Engine & Anomaly Detection)|
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |  AI Classifier & Triage Model    |
               | (TF-IDF + Random Forest Engine)  |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |    Root-Cause Analysis (RCA)     |
               |  (Graph-based & Kernel Tracing)  |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |    Remediation Policy Engine     |
               | (Action Execution & Safety Check)|
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |  Verification & Metrics Loop     |
               |  (Post-Check, MTTR, Audit Log)   |
               +----------------------------------+
```

### Core Autonomous Workflow
`Detect` ➔ `Diagnose` ➔ `Decide` ➔ `Remediate` ➔ `Verify` ➔ `Escalate`

---

## Development & Feature Implementation Status

| Phase | Module | Status | Highlights |
|-------|--------|--------|------------|
| **Phase 1** | Foundation & Core Config | ✅ Complete | Structured logging, schema definitions, YAML config loader. |
| **Phase 2** | Real-Time Monitoring Layer | ✅ Complete | Monitors CPU, Memory, Disk, Services (`procfs`, `sysfs`, `journalctl`). |
| **Phase 3** | Failure Detection Engine | ✅ Complete | Threshold alert rules, SQLite incident storage (`data/incidents.db`). |
| **Phase 4** | AI Triage & ML Classifier | ✅ Complete | TF-IDF + Random Forest model trained on Linux syslogs (`ai/model.pkl`). |
| **Phase 5** | Root-Cause Analysis (RCA) | ✅ Complete | Graph-based dependency resolver & log analysis (`rca/engine.py`). |
| **Phase 6** | Remediation Policy Engine | ✅ Complete | Safe automated actions (`systemctl restart`, `kill`, cache flushing). |
| **Phase 7** | Verification & Metrics Loop | ✅ Complete | Health verification, rollback handling, MTTR tracking, audit logging. |
| **Phase 8** | kdump & Kernel Crash Analysis | ✅ Complete | Crash dump parser (`vmcore` / `dmesg`), kernel panic triage. |
| **Phase 9** | Advanced Kernel Remediation | ✅ Complete | Modular kernel remediations (`config/kernel-remediations.yaml`). |
| **Phase 10** | Web Dashboard & Unified CLI | ✅ Complete | Modern Glassmorphism UI, FastAPI REST server, unified `agent.py` CLI. |

---

## Project Structure

```text
Self-Healing-OS/
├── agent.py                 # Unified AegisOS CLI & daemon entry point
├── config/                  # Configuration files
│   ├── aegisos.yaml         # Main framework configuration
│   └── kernel-remediations.yaml # Advanced kernel policy mapping
├── monitor/                 # Telemetry & system monitoring collectors
├── detector/                # Failure detector & SQLite incident storage
├── ai/                      # ML classifier trainer, model, and triage logic
├── rca/                     # Root-cause analysis engine
├── remediation/             # Remediation actions & safety guardrails
├── verification/            # Post-remediation checks & MTTR metrics
├── kdump/                   # Kernel crash dump (kdump) analyzer
├── dashboard/               # FastAPI backend & web UI interface
│   ├── api.py               # REST API endpoints & static file router
│   └── static/              # Dashboard Web UI (HTML, CSS, JS)
├── common/                  # Shared logger, exceptions, and helpers
├── tests/                   # Comprehensive pytest suite (76 tests)
└── docs/                    # Architecture and design documentation
```

---

## Prerequisites

- **Python:** `3.10` or higher
- **OS:** Linux / WSL2 Ubuntu (recommended for live system interactions) or Windows (mock/simulation mode)
- **Dependencies:** Listed in [requirements.txt](./requirements.txt) (`fastapi`, `uvicorn`, `scikit-learn`, `psutil`, `pyyaml`, `pytest`, `joblib`)

---

## Quick Start & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/apurvv28/Self-Healing-OS.git
cd Self-Healing-OS
```

### 2. Set Up Virtual Environment & Install Dependencies
```bash
# On Linux / macOS / WSL2:
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# On Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Usage Guide

### AegisOS Unified CLI (`agent.py`)

AegisOS provides a single entry point for system control, monitoring, testing, and service hosting:

#### 1. Display Current System Status & Health Metrics
```bash
python agent.py status
```
Outputs system CPU/Memory telemetry and any active threshold alerts.

#### 2. View Incident Audit History
```bash
python agent.py incidents --limit 10
```
Displays recent failure incidents stored in the SQLite database.

#### 3. View Self-Healing Metrics & MTTR Summary
```bash
python agent.py metrics
```
Reports total incidents, recovery count, success rate %, and average Mean-Time-To-Recovery (MTTR).

#### 4. Trigger Controlled Test Failure Scenarios
Simulate system failures to verify automated self-healing execution:
```bash
python agent.py trigger-scenario --type service_failure
python agent.py trigger-scenario --type cpu_overload
python agent.py trigger-scenario --type memory_exhaustion
python agent.py trigger-scenario --type disk_exhaustion
```

#### 5. Execute a Single Self-Healing Loop Cycle
```bash
python agent.py run-cycle
```

#### 6. Run Continuous Autonomous Daemon
```bash
python agent.py daemon
```
Runs an continuous background daemon polling telemetry and executing autonomous remediation.

#### 7. Launch Web Server & Control Dashboard
```bash
python agent.py serve --host 127.0.0.1 --port 8000
```
Access the interactive web dashboard at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## REST API & Web Dashboard

When running `python agent.py serve`, AegisOS exposes a FastAPI web application:

- **Web UI:** `http://127.0.0.1:8000/` (Live metrics charts, interactive scenario injection, incident logs, system health gauges)
- **API Endpoints:**
  - `GET /api/status` — Live telemetry snapshot & active alerts
  - `GET /api/incidents` — Recorded incident audit history
  - `GET /api/metrics` — MTTR and recovery success statistics
  - `POST /api/trigger` — Trigger synthetic test scenarios (`{"scenario_type": "service_failure"}`)
  - `POST /api/run-cycle` — Execute manual self-healing loop iteration

---

## Running Test Suite

AegisOS features a suite of 76 unit and integration tests covering all 10 modules:

```bash
# Run all unit tests
pytest -v

# Run with output capture disabled (verbose logging)
pytest -s -v
```

---

## Documentation

| Document | Content |
|----------|---------|
| [overview.md](./overview.md) | Architectural details, pipeline design, and component breakdown |
| [action-plan.md](./action-plan.md) | Original 10-phase project roadmap |
| [docs/coding-conventions.md](./docs/coding-conventions.md) | Coding style, docstring, and error handling standards |
| [docs/environment-setup.md](./docs/environment-setup.md) | WSL2 setup instructions |
| [docs/system-interfaces.md](./docs/system-interfaces.md) | System monitoring targets (`journalctl`, `dmesg`, `/proc`, `/sys`) |
| [docs/event-schema.md](./docs/event-schema.md) | Event and incident JSON/SQLite schemas |
| [docs/config-format.md](./docs/config-format.md) | AegisOS configuration reference |
| [docs/aws-fallback-setup.md](./docs/aws-fallback-setup.md) | AWS EC2 environment guide for kernel/kdump labs |

---

## License

Academic Project — VIT Semester 5, Operating Systems.
