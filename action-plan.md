# AegisOS — Step-by-Step Action Plan

**Project:** AI-Assisted Self-Healing Linux Operating System  
**Core Workflow:** Detect → Diagnose → Decide → Remediate → Verify → Escalate  
**Target Environment:** Ubuntu Linux VM (VirtualBox/VMware) on Windows/Linux host  
**Reference Document:** [overview.md](./overview.md)

---

## Plan Summary

| Phase | Name | Primary Goal |
|-------|------|--------------|
| 1 | Project Foundation & Environment Setup | Establish repo, VM, and tooling |
| 2 | Real-Time Monitoring Layer | Continuously collect OS health data |
| 3 | Failure Detection Engine | Detect and normalize system incidents |
| 4 | Failure Dataset & AI Classifier | Train ML model for failure classification |
| 5 | Root-Cause Analysis Engine | Correlate evidence and produce diagnoses |
| 6 | Remediation Policy Engine | Execute controlled recovery actions |
| 7 | Recovery Verification & Safety Layer | Verify healing and enforce confidence policies |
| 8 | kdump & Kernel Crash Analysis | Analyze kernel panics and crash dumps |
| 9 | Advanced Kernel Remediation (Optional) | Controlled livepatch/module isolation demo |
| 10 | Dashboard, Integration & Final Demo | End-to-end prototype and evaluation |

---

## Phase 1 — Project Foundation & Environment Setup

**Goal:** Prepare the development environment, repository structure, and baseline knowledge required for all subsequent phases.

**Duration Estimate:** 1–2 weeks

### Tasks

1. **Initialize project repository and directory structure**
   - Create Git repo with folders: `monitor/`, `detector/`, `ai/`, `rca/`, `remediation/`, `verification/`, `kdump/`, `dashboard/`, `config/`, `tests/`, `docs/`
   - Add `requirements.txt`, `.gitignore`, and a root `README.md` with setup instructions
   - Define coding conventions and logging standards for all Python modules

2. **Provision and configure Linux target environment**
   - **Primary (recommended):** Use existing WSL2 Ubuntu — run `bash scripts/setup-wsl.sh` from the project root
   - **Fallback (Phase 8+ only):** AWS EC2 Ubuntu for kdump/kernel crash labs — see `docs/aws-fallback-setup.md`
   - Verify systemd is enabled (`systemctl is-system-running`), project path accessible at `/mnt/d/...`
   - Install base packages: `python3`, `pip`, `venv`, build tools; create `.venv` and install `requirements.txt`
   - Export WSL baseline snapshot: `wsl --export Ubuntu <path>.tar` (optional)

3. **Document system interfaces and monitoring targets**
   - Map data sources: `journalctl`, `systemctl`, `dmesg`, `/proc`, `/sys`
   - Create a reference sheet of commands and file paths used by AegisOS
   - Verify read access and permissions for each monitoring target

4. **Define normalized event schema and configuration format**
   - Design the canonical event structure: Event ID, Timestamp, Failure Type, Source, Severity, Raw Evidence
   - Create YAML/JSON config templates for thresholds, allowed actions, and confidence policies
   - Store schema and config specs in `docs/` for use across all modules

**Deliverable:** A configured WSL2 Ubuntu environment (or AWS EC2 for kernel labs), initialized repo, and documented schemas ready for monitoring implementation. See `docs/environment-setup.md`.

---

## Phase 2 — Real-Time Monitoring Layer

**Goal:** Build a Python-based monitoring daemon that continuously collects OS health information from all primary sources.

**Duration Estimate:** 2 weeks

### Tasks

1. **Implement log and service monitors**
   - Build modules to tail/filter `journalctl` output and poll `systemctl` for service states
   - Capture `dmesg` kernel messages on interval or via inotify-style polling
   - Normalize raw log lines into structured records with timestamps and source tags

2. **Implement resource and process monitors**
   - Read CPU, memory, disk, and load averages from `/proc` and `/sys` (or via `psutil`)
   - Track running processes: PID, name, CPU%, memory%, state
   - Define configurable thresholds for resource alerts (e.g., CPU > 90%, memory > 95%)

3. **Build the monitoring daemon (`aegis-monitor`)**
   - Create a long-running Python daemon with configurable poll intervals
   - Aggregate outputs from all sub-monitors into a unified event stream or message queue
   - Add structured logging, graceful shutdown, and error handling for missing permissions

4. **Validate monitoring output against manual checks**
   - Compare daemon output with manual `journalctl`, `top`, and `systemctl` results
   - Run the daemon for 24+ hours and confirm stable, continuous data collection
   - Document sample output and any permission/sudo requirements

**Deliverable:** A working `aegis-monitor` daemon that continuously streams structured OS health data.

---

## Phase 3 — Failure Detection Engine

**Goal:** Detect predefined failure classes and emit normalized incident events without AI assistance.

**Duration Estimate:** 2 weeks

### Tasks

1. **Implement rule-based failure detectors**
   - Service failure: detect `failed`/`inactive` systemd units and repeated restart loops
   - Resource exhaustion: detect high CPU, memory pressure (OOM hints), and disk full conditions
   - Kernel errors: flag critical `dmesg`/`journald` patterns (I/O errors, segfaults, module failures)

2. **Define failure taxonomy and severity mapping**
   - Map detections to classes: `SERVICE_FAILURE`, `MEMORY_EXHAUSTION`, `CPU_OVERLOAD`, `DISK_EXHAUSTION`, `KERNEL_ERROR`, `DRIVER_FAILURE`, `CONFIGURATION_ERROR`, `UNKNOWN_FAILURE`
   - Assign severity levels (INFO, WARNING, CRITICAL) and deduplication rules to avoid alert storms

3. **Build the detection engine and event pipeline**
   - Consume monitor output and apply detection rules in real time
   - Emit normalized events with Event ID, Timestamp, Failure Type, Source, Severity, Raw Evidence
   - Persist detected incidents to SQLite for downstream AI and RCA modules

4. **Create controlled failure test scenarios**
   - Script reproducible failures: crash a test service, fill disk in `/tmp`, trigger memory pressure, inject config errors
   - Verify each scenario is detected with correct failure type and evidence attached
   - Document test scripts in `tests/scenarios/`

**Deliverable:** AegisOS detects and records basic system incidents with correct classification and evidence.

---

## Phase 4 — Failure Dataset & AI Classifier

**Goal:** Train a lightweight ML model to classify system failures from log features.

**Duration Estimate:** 2–3 weeks

### Tasks

1. **Collect and label failure log dataset**
   - Run controlled failure scenarios (Phase 3 scripts) and capture associated logs
   - Label samples by failure class; aim for balanced coverage across all primary types
   - Store raw logs and labels in `data/raw/` with a manifest file describing each sample

2. **Build log preprocessing and feature extraction pipeline**
   - Clean logs: strip timestamps, normalize paths, tokenize messages
   - Extract features using TF-IDF on log text; optionally add metadata features (source, severity, resource metrics)
   - Split data into train/validation/test sets (e.g., 70/15/15)

3. **Train and evaluate classifier models**
   - Train Logistic Regression and Random Forest baselines using scikit-learn
   - Evaluate with precision, recall, F1-score, and confusion matrix per failure class
   - Select best model based on F1 and interpretability; save model artifact to `ai/models/`

4. **Integrate classifier into the AI triage module**
   - Build `ai/classifier.py` API: input = log evidence bundle, output = failure class + probability
   - Wire classifier output into the detection pipeline as a secondary classification layer
   - Add fallback to rule-based detection when model confidence is low

**Deliverable:** A trained, evaluated classifier integrated into AegisOS with documented accuracy metrics.

---

## Phase 5 — Root-Cause Analysis Engine

**Goal:** Move beyond single-log classification to multi-source diagnosis with confidence scoring.

**Duration Estimate:** 2–3 weeks

### Tasks

1. **Implement temporal event correlation**
   - Align events from logs, service states, and resource metrics by timestamp windows (e.g., ±30 s)
   - Group correlated events into incident bundles for unified analysis
   - Handle overlapping incidents and prevent double-counting

2. **Build evidence aggregation and diagnosis generator**
   - Combine classifier output with correlated evidence (OOM messages + high memory + process kill)
   - Produce diagnosis objects: Failure Type, Probable Root Cause, Evidence, Confidence Score, Recommended Remediation, Risk Level

3. **Implement confidence scoring logic**
   - Score based on: number of corroborating signals, classifier probability, rule match strength
   - Apply policy thresholds: `< 70%` → log + escalate; `70–90%` → recommend; `> 90%` → auto-remediate eligible
   - Document scoring formula and tunable weights in config

4. **Validate RCA against known failure scenarios**
   - Run full scenario suite and verify diagnoses match expected root causes
   - Measure diagnosis accuracy and false-positive rate
   - Refine correlation windows and scoring weights based on results

**Deliverable:** An RCA engine that outputs structured diagnoses with evidence and confidence scores.

---

## Phase 6 — Remediation Policy Engine

**Goal:** Execute controlled, logged recovery actions for supported failure classes.

**Duration Estimate:** 2–3 weeks

### Tasks

1. **Implement core remediation actions**
   - `restart_service(unit)`: restart failed systemd services with timeout
   - `restore_configuration(path)`: restore from known-good backup snapshots
   - `cleanup_temp_files(dirs)`: remove approved temporary files to free disk space
   - `apply_safe_sysctl(params)`: apply pre-approved, reversible sysctl changes

2. **Build policy engine and action dispatcher**
   - Map failure types + confidence levels to allowed remediation policies via YAML config
   - Dispatch actions through a single `RemediationEngine` with permission checks (sudo whitelist)
   - Enforce action logging: timestamp, action type, target, result, operator (auto/manual)

3. **Add safety controls: retries, timeouts, and rollback**
   - Set maximum retry limits per incident (e.g., 3 attempts with exponential backoff)
   - Implement rollback for config/sysctl changes on verification failure
   - Block high-risk actions (kernel mods, driver blacklisting) unless explicitly enabled

4. **Test remediation on controlled failure scenarios**
   - Verify service restart recovers crashed Apache/nginx test service
   - Verify disk cleanup resolves simulated disk-full condition
   - Confirm blocked actions escalate instead of executing when confidence is low

**Deliverable:** AegisOS automatically recovers from selected low-risk failures with full audit logging.

---

## Phase 7 — Recovery Verification & Safety Layer

**Goal:** Confirm remediation success, measure recovery metrics, and enforce escalation policies.

**Duration Estimate:** 2 weeks

### Tasks

1. **Implement post-remediation health checks**
   - Service health: `systemctl is-active`, process alive, port responding (if applicable)
   - Resource health: CPU/memory/disk within thresholds for N seconds post-action
   - Log health: no repeated failure signatures in logs within observation window

2. **Build verification loop with retry and escalation**
   - Flow: Remediation → Wait → Health Check → Recovered? → Success or Retry/Escalate
   - Stop retrying after max attempts; mark incident as `ESCALATED` with full history
   - Notify via log entry, file alert, or dashboard flag on escalation

3. **Implement incident history and metrics tracking**
   - Record: detected failures, timestamps, diagnoses, actions, results, recovery time (MTTR)
   - Compute metrics: recovery success rate, false remediation rate, detection/diagnosis accuracy
   - Expose metrics via SQLite queries or a simple metrics API endpoint

4. **Run end-to-end self-healing loop tests**
   - Execute full Detect → Diagnose → Decide → Remediate → Verify → Escalate loop on all scenario types
   - Compare MTTR with manual recovery baseline
   - Document success/failure cases and edge cases (e.g., flapping services)

**Deliverable:** Quantifiable evidence that AegisOS improves recovery with verified success/failure tracking.

---

## Phase 8 — kdump & Kernel Crash Analysis

**Goal:** Integrate kernel-level crash capture and analysis for panic/post-mortem diagnosis.

**Duration Estimate:** 2–3 weeks

### Tasks

1. **Configure kdump in the Ubuntu VM**
   - Install and configure `kdump-tools`; set crash kernel memory reservation
   - Test crash dump generation with controlled kernel panic (e.g., `echo c > /proc/sysrq-trigger` in test VM snapshot)
   - Verify vmcore files are written to configured dump path

2. **Build crash dump analysis module**
   - Parse vmcore or use `crash` utility to extract panic message, stack trace, and suspect modules
   - Map extracted signatures to known failure patterns in a local crash signature database
   - Output structured crash report: panic type, suspected module/function, call path summary

3. **Integrate crash monitor into AegisOS pipeline**
   - Detect new vmcore files and trigger analysis automatically
   - Feed crash analysis results into RCA engine as high-severity evidence
   - Restrict output to diagnosis only — no automatic kernel modification after panic

4. **Validate with controlled crash scenarios**
   - Document 2–3 reproducible panic scenarios (e.g., faulty test module, sysrq trigger)
   - Verify crash analysis correctly identifies panic cause and suspect components
   - Add crash incidents to incident history with separate `KERNEL_CRASH` category

**Deliverable:** A kernel crash analysis component that diagnoses controlled crash scenarios from kdump data.

---

## Phase 9 — Advanced Kernel Remediation (Optional Extension)

**Goal:** Demonstrate controlled, pre-approved kernel-level recovery without AI-generated patches.

**Duration Estimate:** 2 weeks

### Tasks

1. **Build known-issue and approved-patch database**
   - Create a YAML/JSON database mapping crash signatures and kernel errors to approved remediations
   - Include entries for: module blacklisting, driver reload, pre-approved livepatch packages
   - Require explicit admin approval flag for each entry before auto-execution

2. **Implement module isolation and driver management**
   - Safe actions: `modprobe -r` for test modules, blacklist entry in `/etc/modprobe.d/` (test VM only)
   - Log all module operations; rollback blacklist on verification failure
   - Never auto-modify production or unknown drivers

3. **Integrate Linux Livepatch/kpatch (demonstration only)**
   - Set up livepatch on Ubuntu test kernel with a pre-approved patch package
   - Flow: AI diagnosis → match known issue → approved patch available → apply → verify health
   - Document manual approval step and rollback procedure

4. **Validate advanced remediation in isolated test VM**
   - Demonstrate one module isolation and one livepatch scenario end-to-end
   - Confirm escalation when no approved remediation exists for an unknown kernel issue
   - Snapshot VM before each test; never run on host system

**Deliverable:** A controlled demonstration of kernel-level remediation with strict safety gates.

---

## Phase 10 — Dashboard, Integration & Final Demo

**Goal:** Integrate all components into a complete, demonstrable AegisOS prototype.

**Duration Estimate:** 2–3 weeks

### Tasks

1. **Build FastAPI backend and incident API**
   - Expose REST endpoints: system health, active incidents, diagnosis details, remediation history, metrics
   - Connect API to SQLite incident database and live monitor status
   - Add WebSocket or polling endpoint for real-time incident updates

2. **Develop optional web dashboard**
   - Display: system health status, active/recovered incidents, failure timeline, AI diagnosis, confidence scores
   - Show remediation actions, recovery status, MTTR, and kernel crash incidents
   - Use React/Next.js or a lightweight HTML/JS frontend per team preference

3. **Integrate full pipeline into unified AegisOS agent**
   - Wire all modules: Monitoring → Detection → AI Triage → RCA → Remediation → Verification → History
   - Single entry point: `aegis-agent` daemon or systemd service with config-driven startup
   - Add CLI commands: `status`, `incidents`, `metrics`, `trigger-test-scenario`

4. **Prepare final demonstration and project report**
   - Run 5+ controlled failure scenarios comparing manual vs AegisOS-assisted recovery
   - Record MTTR, success rate, and sample incident reports for documentation
   - Write final report covering architecture, results, limitations, and future work

**Deliverable:** Complete AegisOS prototype with dashboard, full integration, and documented evaluation results.

---

## Dependency Flow

```text
Phase 1 (Setup)
    ↓
Phase 2 (Monitoring)
    ↓
Phase 3 (Detection)
    ↓
Phase 4 (AI Classifier) ──→ Phase 5 (RCA)
                                ↓
                          Phase 6 (Remediation)
                                ↓
                          Phase 7 (Verification)
                                ↓
              Phase 8 (kdump) ──┴── Phase 9 (Advanced Kernel) [optional]
                                ↓
                          Phase 10 (Dashboard & Demo)
```

---

## Technology Stack Reference

| Layer | Technology |
|-------|------------|
| OS / VM | Ubuntu LTS, VirtualBox/VMware |
| Monitoring | systemd, journald, dmesg, `/proc`, `/sys`, psutil |
| Backend | Python 3, Bash |
| ML | scikit-learn, pandas, TF-IDF |
| Database | SQLite |
| API | FastAPI |
| Dashboard | React / Next.js (optional) |
| Kernel | kdump, crash, Livepatch/kpatch (optional) |
| VCS | Git + GitHub |

---

## Success Criteria (Final Checklist)

- [ ] Failure introduced in test VM is detected within configured time window
- [ ] Evidence is collected from multiple sources (logs + metrics + service state)
- [ ] Root cause is identified with confidence score and recommended action
- [ ] Safe remediation executes automatically when confidence > 90%
- [ ] System health is verified post-remediation; failure escalates on repeated failure
- [ ] Incident is recorded with full audit trail and recovery time
- [ ] Dashboard (or CLI) displays current health and incident history
- [ ] Final demo compares manual recovery time vs AegisOS MTTR across 5+ scenarios

---

## Recommended Timeline (Approximate)

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 1 — Foundation | 1–2 weeks | Week 2 |
| 2 — Monitoring | 2 weeks | Week 4 |
| 3 — Detection | 2 weeks | Week 6 |
| 4 — AI Classifier | 2–3 weeks | Week 9 |
| 5 — RCA | 2–3 weeks | Week 12 |
| 6 — Remediation | 2–3 weeks | Week 15 |
| 7 — Verification | 2 weeks | Week 17 |
| 8 — kdump | 2–3 weeks | Week 20 |
| 9 — Advanced Kernel (optional) | 2 weeks | Week 22 |
| 10 — Dashboard & Demo | 2–3 weeks | Week 25 |

**Total estimated duration:** ~5–6 months (adjust based on team size and academic schedule)

---

*This action plan is derived from [overview.md](./overview.md) and should be updated as implementation progresses.*
