# AegisOS — System Interfaces & Monitoring Targets

**Phase 1, Task 3** — Reference for all OS data sources AegisOS reads.

Run the access verification script:

```bash
bash scripts/verify-interfaces.sh
```

---

## Overview

| Source | Interface | AegisOS use | Phase |
|--------|-----------|-------------|-------|
| systemd journal | `journalctl` | Service crashes, OOM, app errors | 2–3 |
| systemd units | `systemctl` | Service state, restart loops | 2–3 |
| Kernel ring buffer | `dmesg` | Kernel errors, driver faults, OOM | 2–3 |
| Process & CPU info | `/proc` | Resource usage, process list | 2 |
| Hardware & kernel attrs | `/sys` | Block devices, thermal, modules | 2 |
| Crash dumps | kdump vmcore | Panic analysis | 8 (AWS EC2) |

---

## 1. journalctl (systemd journal)

**Purpose:** Central log stream for services, kernel, and user sessions.

### Key commands

```bash
# Follow live logs (JSON for parsing)
journalctl -f -o json

# Recent errors and above
journalctl -p err..emerg --since "10 min ago" -o json

# Logs for a specific unit
journalctl -u nginx.service --since today -o json

# Boot-scoped logs
journalctl -b -p warning..emerg -o json

# Check journal disk usage
journalctl --disk-usage
```

### Useful fields (JSON output)

| Field | Description |
|-------|-------------|
| `__REALTIME_TIMESTAMP` | Event time (microseconds since epoch) |
| `PRIORITY` | syslog priority (0=emerg … 7=debug) |
| `_SYSTEMD_UNIT` | Source systemd unit |
| `MESSAGE` | Log message text |
| `_PID` | Process ID |
| `_COMM` | Command name |

### Paths & permissions

| Path / command | Access | Notes |
|----------------|--------|-------|
| `journalctl` | User | Read own + system logs |
| `/var/log/journal/` | Root / `systemd-journal` group | Persistent journal storage |
| `/run/log/journal/` | Root / `systemd-journal` group | Runtime journal |

**WSL note:** journald is fully available when systemd is enabled.

---

## 2. systemctl (systemd service manager)

**Purpose:** Detect failed, inactive, or flapping services.

### Key commands

```bash
# List failed units
systemctl --failed --no-pager

# Status of a unit (structured)
systemctl show nginx.service -p ActiveState,SubState,Result,ExecMainStatus,NRestarts

# List all active services
systemctl list-units --type=service --state=running --no-pager

# Show unit file properties
systemctl show -p NRestarts,ExecMainStatus,ActiveEnterTimestamp nginx.service

# Is a unit active?
systemctl is-active nginx.service
```

### States to watch

| State | Meaning |
|-------|---------|
| `failed` | Service entered failed state |
| `inactive` | Not running (may be expected or crashed) |
| `activating` | Starting (stuck here = problem) |
| `deactivating` | Shutting down |

### Paths & permissions

| Path | Access | Notes |
|------|--------|-------|
| `systemctl` | User (read); root (manage) | Remediation needs sudo |
| `/etc/systemd/system/` | Root | Unit file overrides |
| `/run/systemd/system/` | Root | Runtime units |

---

## 3. dmesg (kernel ring buffer)

**Purpose:** Kernel-level errors, OOM killer, driver failures, I/O errors.

### Key commands

```bash
# Human-readable recent kernel messages
dmesg --level=err,warn --ctime

# JSON output (kernel 5.8+)
dmesg -J --level=err,warn

# Follow new messages
dmesg -w --level=err,warn

# Clear ring buffer (root only — avoid in production)
# sudo dmesg -C
```

### Patterns AegisOS watches

| Pattern | Failure class |
|---------|---------------|
| `Out of memory` / `Killed process` | `MEMORY_EXHAUSTION` |
| `I/O error` / `Buffer I/O error` | `KERNEL_ERROR` |
| `segfault` / `BUG:` | `KERNEL_ERROR` |
| `module .* not found` | `DRIVER_FAILURE` |
| `blocked for more than` | `KERNEL_ERROR` |

### Paths & permissions

| Path / command | Access | Notes |
|----------------|--------|-------|
| `dmesg` | User (WSL/modern kernels) | May need `kernel.dmesg_restrict=0` on some systems |
| `/dev/kmsg` | Root | Raw kernel message device |

**WSL note:** Fewer real kernel events than bare metal; sufficient for pattern-matching development.

---

## 4. /proc (process & resource information)

**Purpose:** CPU, memory, disk I/O, and process-level metrics.

### Key files

| File | Content |
|------|---------|
| `/proc/meminfo` | Total/free/available memory, swap, buffers |
| `/proc/loadavg` | 1/5/15 min load averages |
| `/proc/stat` | Per-CPU usage counters |
| `/proc/uptime` | System uptime in seconds |
| `/proc/[pid]/status` | Per-process memory, state, name |
| `/proc/[pid]/cmdline` | Process command line |
| `/proc/diskstats` | Block device I/O statistics |
| `/proc/mounts` | Mounted filesystems |

### Key commands (using /proc via tools)

```bash
# Memory summary
grep -E 'MemTotal|MemAvailable|SwapFree' /proc/meminfo

# Load average
cat /proc/loadavg

# Top memory consumers (uses /proc internally)
ps aux --sort=-%mem | head -10

# Disk usage (filesystem level)
df -h --output=source,size,used,avail,pcent,target
```

### Paths & permissions

| Path | Access |
|------|--------|
| `/proc/meminfo`, `/proc/stat`, `/proc/loadavg` | World-readable |
| `/proc/[pid]/*` | Owner or root for other users' processes |

**Python access:** Use `psutil` (wraps `/proc`) for cross-platform parsing.

---

## 5. /sys (kernel object hierarchy)

**Purpose:** Hardware attributes, block devices, loaded modules, thermal data.

### Key paths

| Path | Content |
|------|---------|
| `/sys/class/block/` | Block devices (sda, sdb, …) |
| `/sys/block/<dev>/stat` | Device I/O counters |
| `/sys/class/thermal/` | Thermal zones and temperatures |
| `/sys/module/` | Loaded kernel modules |
| `/sys/fs/cgroup/` | cgroup v2 hierarchy (resource limits) |

### Key commands

```bash
# List loaded modules
ls /sys/module/

# Block device list
ls /sys/class/block/

# Module info
modinfo <module_name> 2>/dev/null

# Thermal zones
cat /sys/class/thermal/thermal_zone*/type 2>/dev/null
cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null
```

### Paths & permissions

| Path | Access |
|------|--------|
| Most `/sys` attributes | World-readable |
| Writable `/sys` nodes | Root only (not used by AegisOS monitoring) |

---

## 6. psutil (Python wrapper — recommended)

AegisOS uses `psutil` to read `/proc` and `/sys` consistently:

```python
import psutil

psutil.cpu_percent(interval=1)
psutil.virtual_memory()
psutil.disk_usage("/")
psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"])
```

---

## Permission Summary

| Operation | User | sudo required |
|-----------|------|---------------|
| Read journalctl logs | Yes | No |
| Read systemctl status | Yes | No |
| Read dmesg | Yes (WSL) | Sometimes on bare metal |
| Read /proc, /sys | Yes | No |
| Restart services | No | **Yes** |
| Modify sysctl | No | **Yes** |
| kdump / vmcore analysis | No | **Yes** |

Remediation actions (Phase 6) require a sudoers whitelist — configured in `config/remediation-policies.yaml`.

---

## Monitoring Target → Module Mapping

```text
monitor/logs.py       → journalctl
monitor/services.py   → systemctl
monitor/kernel.py     → dmesg
monitor/resources.py  → /proc, /sys, psutil
monitor/processes.py  → /proc, psutil
kdump/analyzer.py     → vmcore (Phase 8, AWS EC2)
```

---

## Related Documents

- [event-schema.md](./event-schema.md) — normalized event structure (Task 4)
- [config-format.md](./config-format.md) — configuration reference (Task 4)
- [environment-setup.md](./environment-setup.md) — WSL setup
