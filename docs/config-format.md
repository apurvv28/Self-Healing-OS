# AegisOS — Configuration Format Reference

**Phase 1, Task 4** — How configuration files are organized and loaded.

All config files live in `config/` and use YAML. Paths are relative to the project root unless absolute.

---

## File Layout

| File | Purpose |
|------|---------|
| `config/aegisos.yaml` | Main settings: logging, DB, poll intervals |
| `config/thresholds.yaml` | Resource alert thresholds |
| `config/confidence-policies.yaml` | Auto-remediate vs escalate rules |
| `config/remediation-policies.yaml` | Allowed actions per failure type |

Load order: `aegisos.yaml` references the other files by path.

---

## aegisos.yaml

Top-level runtime configuration.

```yaml
aegisos:
  environment: wsl          # wsl | ec2 | bare-metal
  log_level: INFO
  log_file: logs/aegisos.log

monitoring:
  poll_interval_seconds: 10
  journal_lookback_minutes: 5
  config_files:
    thresholds: config/thresholds.yaml
    confidence: config/confidence-policies.yaml
    remediation: config/remediation-policies.yaml

database:
  path: data/aegisos.db     # SQLite incident store

agent:
  max_concurrent_incidents: 5
  dedup_window_seconds: 60
```

---

## thresholds.yaml

Resource monitoring alert thresholds. Values are percentages unless noted.

```yaml
thresholds:
  cpu:
    warning_percent: 80
    critical_percent: 90
    sustained_seconds: 30     # must exceed for N seconds

  memory:
    warning_percent: 85
    critical_percent: 95

  disk:
    warning_percent: 85
    critical_percent: 95
    paths:
      - /
      - /tmp

  service:
    max_restarts: 3           # restarts within window → SERVICE_FAILURE
    restart_window_seconds: 300
```

---

## confidence-policies.yaml

Controls whether AegisOS logs, recommends, or auto-executes remediation.

```yaml
confidence:
  escalate_below: 0.70        # < 70%  → log + escalate
  recommend_below: 0.90       # 70–90% → recommend only
  auto_remediate_at: 0.90     # >= 90% → auto-remediate (if policy allows)

  min_evidence_count: 2     # minimum corroborating signals for auto-remediate

escalation:
  max_retries: 3
  retry_backoff_seconds: 30
  notify:
    log: true
    file: logs/escalations.log
```

---

## remediation-policies.yaml

Maps failure types to allowed actions and risk levels.

### Action keys

| Action key | Description | sudo |
|------------|-------------|------|
| `restart_service` | `systemctl restart <unit>` | Yes |
| `restore_configuration` | Copy from known-good backup | Yes |
| `cleanup_temp_files` | Remove files in approved dirs | Yes |
| `apply_safe_sysctl` | Apply pre-approved sysctl values | Yes |
| `blacklist_module` | Add module to modprobe blacklist | Yes |
| `escalate` | Log and stop; no automated action | No |

### Policy structure

```yaml
policies:
  SERVICE_FAILURE:
    risk_level: LOW
    allowed_actions:
      - restart_service
      - restore_configuration
    default_action: restart_service
    auto_remediate: true

  MEMORY_EXHAUSTION:
    risk_level: MEDIUM
    allowed_actions:
      - restart_service
      - escalate
    default_action: restart_service
    auto_remediate: true
    target_units: []          # empty = infer from evidence

  DISK_EXHAUSTION:
    risk_level: LOW
    allowed_actions:
      - cleanup_temp_files
      - escalate
    default_action: cleanup_temp_files
    auto_remediate: true
    cleanup_dirs:
      - /tmp
      - /var/tmp

  KERNEL_ERROR:
    risk_level: HIGH
    allowed_actions:
      - escalate
    default_action: escalate
    auto_remediate: false

  DRIVER_FAILURE:
    risk_level: HIGH
    allowed_actions:
      - blacklist_module
      - escalate
    default_action: escalate
    auto_remediate: false     # Phase 9 only, with explicit enable

global:
  remediation_timeout_seconds: 120
  require_sudo_whitelist: true
  sudo_whitelist:
    - /bin/systemctl restart *
    - /bin/systemctl start *
    - /bin/systemctl stop *
```

---

## Loading Config in Python

```python
from common.config_loader import load_config

cfg = load_config("config/aegisos.yaml")
poll_interval = cfg["monitoring"]["poll_interval_seconds"]
cpu_critical = cfg["thresholds"]["cpu"]["critical_percent"]
```

---

## Environment Overrides

For AWS EC2 (Phase 8), override environment in a local file not committed to git:

```yaml
# config/local.yaml (gitignored)
aegisos:
  environment: ec2
```

Merge order: `aegisos.yaml` → `local.yaml` (if present).

---

## Related

- [event-schema.md](./event-schema.md) — event and diagnosis structures
- [system-interfaces.md](./system-interfaces.md) — monitoring targets
