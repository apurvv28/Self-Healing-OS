# AegisOS — Environment Setup Guide

**Phase 1, Task 2** — Choose and configure your Linux target environment.

---

## Recommendation

| Environment | Use for | Status |
|-------------|---------|--------|
| **WSL2 + Ubuntu** (primary) | Phases 1–7, 10 — monitoring, detection, AI, RCA, remediation, dashboard | Recommended |
| **AWS EC2** (fallback) | Phase 8–9 only — kdump, kernel crash analysis, livepatch demo | When needed |

Your machine already has **Ubuntu 26.04 on WSL2** with **systemd running**. That is sufficient for the core self-healing loop. You do **not** need a local VMware/VirtualBox VM.

---

## Why WSL Works for AegisOS

AegisOS monitors user-space and systemd-level failures. WSL2 supports:

| Feature | WSL2 | Notes |
|---------|------|-------|
| systemd / journald | Yes | Required; already enabled on your install |
| `systemctl`, `journalctl` | Yes | Service failure detection works |
| `/proc`, `/sys` | Yes | Resource monitoring works |
| `dmesg` | Partial | Available; fewer real kernel events than bare metal |
| Python + psutil | Yes | Full support |
| Service restart remediation | Yes | systemd units can be managed |
| **kdump / vmcore** | **No** | WSL uses a virtual kernel; no crash dumps |
| **Livepatch / kpatch** | **No** | Requires real Linux kernel |

Phases 1–7 and 10 cover ~90% of the project. Phase 8 (kdump) needs a real Linux instance — use AWS EC2 briefly when you reach that phase.

---

## WSL Setup (Primary Path)

### Prerequisites (Windows host)

- WSL2 enabled
- Ubuntu distro installed (`wsl --list --verbose` should show `Ubuntu` version `2`)

### Project path in WSL

Your repo on `D:` is accessible inside WSL at:

```text
/mnt/d/VIT/Sem 5/Operating System/Self-Healing-OS
```

Work from this path so Windows (Cursor) and WSL share the same files.

### One-command bootstrap

Open **Ubuntu** from the Start menu (interactive terminal — sudo password required):

```bash
cd "/mnt/d/VIT/Sem 5/Operating System/Self-Healing-OS"
bash scripts/setup-wsl.sh
```

> **Note:** Run this in a real Ubuntu terminal, not via automated scripts. It needs your sudo password once.

Verify after setup:

```bash
bash scripts/verify-wsl.sh
```

This script:

1. Installs `python3`, `pip`, `venv`, build tools, systemd utilities
2. Creates `.venv` and installs `requirements.txt`
3. Verifies `journalctl`, `systemctl`, `dmesg`, `/proc`, `/sys`

### Daily workflow

**Terminal 1 — WSL (run AegisOS):**

```bash
cd "/mnt/d/VIT/Sem 5/Operating System/Self-Healing-OS"
source .venv/bin/activate
# run monitors, tests, agents here
```

**Terminal 2 — Windows (Cursor IDE):**

Edit code in Cursor on the Windows side; changes are immediately visible in WSL via `/mnt/d/...`.

### Enable systemd (if ever disabled)

Create or edit `/etc/wsl.conf` inside Ubuntu:

```ini
[boot]
systemd=true
```

Then from PowerShell: `wsl --shutdown`, and reopen Ubuntu.

### WSL resource limits (optional)

Create `%UserProfile%\.wslconfig` on Windows to cap memory if needed:

```ini
[wsl2]
memory=4GB
processors=2
```

Your current WSL instance reports ~7.6 GB RAM and ~954 GB free disk — no changes required.

---

## AWS EC2 Fallback (Phase 8+)

Use only when you reach **kdump / kernel crash analysis**. A `t3.micro` or `t3.small` Ubuntu instance for a few hours is enough.

See [aws-fallback-setup.md](./aws-fallback-setup.md) for step-by-step EC2 provisioning.

**Cost tip:** Start the instance only for Phase 8 labs; stop/terminate when done.

---

## Environment Comparison

| Criteria | Local VMware VM | WSL2 | AWS EC2 |
|----------|-----------------|------|---------|
| Disk on C: drive | High (~20–40 GB) | Minimal | None (remote) |
| systemd / journald | Full | Full (WSL2) | Full |
| kdump support | Yes | No | Yes |
| Setup time | Hours | Minutes | ~10 min |
| Best for | Full kernel labs | Dev + core project | Phase 8 only |

---

## Verification Checklist (Task 2 complete when all pass)

Run inside WSL:

```bash
cd "/mnt/d/VIT/Sem 5/Operating System/Self-Healing-OS"
source .venv/bin/activate

# OS
cat /etc/os-release | grep PRETTY_NAME

# systemd
systemctl is-system-running

# Monitoring tools
journalctl --version
systemctl --version
dmesg --version

# Python
python3 --version
pip show psutil

# Project tests
pytest tests/ -v
```

Expected: all commands succeed; pytest passes.

---

## Snapshot / Baseline

Unlike a VMware snapshot, save a WSL baseline by exporting:

```powershell
wsl --export Ubuntu D:\aegisos-wsl-baseline.tar
```

Restore if needed:

```powershell
wsl --import Ubuntu-backup D:\WSL\Ubuntu-backup D:\aegisos-wsl-baseline.tar
```

---

*Next: [Phase 1, Task 3 — System interfaces reference](./system-interfaces.md)*
