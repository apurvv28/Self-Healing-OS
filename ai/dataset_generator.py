"""Failure log dataset generator for AegisOS AI training."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

from common.events import FailureType

# Failure log templates per failure class
DATASET_TEMPLATES: dict[str, list[str]] = {
    FailureType.SERVICE_FAILURE.value: [
        "systemd[1]: Unit {unit}.service entered failed state.",
        "systemd[1]: {unit}.service: Main process exited, code=exited, status=1/FAILURE",
        "systemd[1]: {unit}.service: Failed with result 'exit-code'.",
        "systemd[1]: {unit}.service: Scheduled restart job, restart counter is at {num}.",
        "systemd[1]: {unit}.service: Start request repeated too quickly.",
        "systemd[1]: Failed to start {unit} daemon.",
        "{unit}[{pid}]: [CRITICAL] Service failed to bind to port {port}: address already in use.",
        "{unit}[{pid}]: Fatal error: configuration process crashed unexpectedly with signal 9.",
        "systemd[1]: {unit}.service: Control process exited, code=killed, status=15/TERM",
        "systemd[1]: {unit}.service: Service has no holdoff time, scheduling restart.",
    ],
    FailureType.MEMORY_EXHAUSTION.value: [
        "kernel: [{time}] Out of memory: Kill process {pid} ({proc}) score {num} or sacrifice child",
        "kernel: [{time}] oom-killer: gfp_mask=0x100cca(GFP_HIGHUSER_MOVABLE), order=0, oom_score_adj=0",
        "kernel: [{time}] Memory cgroup out of memory: Killed process {pid} ({proc})",
        "kernel: [{time}] {proc} invoked oom-killer: gfp_mask=0x6200ca, order=0",
        "kernel: [{time}] Memory allocation failed for process {proc} (PID {pid}): page allocation error.",
        "{proc}[{pid}]: [ERROR] java.lang.OutOfMemoryError: Java heap space",
        "{proc}[{pid}]: [ERROR] Memory limit exceeded: failed to allocate {num}MB memory buffer",
        "kernel: [{time}] System memory usage critical: free memory 12MB / total 16000MB (used {num}%)",
        "{proc}[{pid}]: Memory allocation error: cannot allocate memory for worker thread pool",
        "kernel: [{time}] SLUB: Unable to allocate memory for slab cache",
    ],
    FailureType.CPU_OVERLOAD.value: [
        "kernel: [{time}] watchdog: BUG: soft lockup - CPU#{num} stuck for 22s! [{proc}:{pid}]",
        "kernel: [{time}] rcu: INFO: rcu_sched self-detected stall on CPU #{num}",
        "kernel: [{time}] CPU throttling invoked: sustained high load average {num}.50",
        "{proc}[{pid}]: [WARNING] CPU utilization exceeded threshold: usage at 98.4%",
        "{proc}[{pid}]: Worker thread stall detected: processing queue blocked due to CPU saturation",
        "systemd[1]: System load average critical: 1m load {num}.82 exceeds CPU capacity",
        "{proc}[{pid}]: Task scheduler warning: thread {pid} exceeded slice time (CPU overload)",
        "kernel: [{time}] perf: interrupt took too long, lowering kernel.perf_event_max_sample_rate to {num}",
        "{proc}[{pid}]: High CPU consumption alert: process consuming 99.8% CPU for {num}0 seconds",
        "kernel: [{time}] sched: RT throttling activated for CPU #{num}",
    ],
    FailureType.DISK_EXHAUSTION.value: [
        "kernel: [{time}] EXT4-fs (sda1): error count since last fsck: {num}",
        "{proc}[{pid}]: [ERROR] IOError: [Errno 28] No space left on device: '/var/log/{unit}.log'",
        "{proc}[{pid}]: Failed to write trace data: disk partition /tmp is 100% full",
        "systemd-journald[{pid}]: Suppressed {num} messages due to disk quota exceeded on /var/log/journal",
        "kernel: [{time}] blk_update_request: I/O error, dev sda, sector {num}00",
        "{proc}[{pid}]: Cannot create database checkpoint file: No space left on device",
        "kernel: [{time}] EXT4-fs error (device sda1): ext4_lookup: deleted inode referenced: {num}",
        "systemd[1]: Failed to save runtime state to /run: No space left on device",
        "{proc}[{pid}]: Database storage write error: disk space fully depleted on mount /data",
        "kernel: [{time}] Buffer I/O error on dev sda1, logical block {num}, async page read",
    ],
    FailureType.KERNEL_ERROR.value: [
        "kernel: [{time}] BUG: unable to handle kernel NULL pointer dereference at 000000000000000{num}",
        "kernel: [{time}] Kernel panic - not syncing: Fatal exception in interrupt",
        "kernel: [{time}] CPU: {num} PID: {pid} Comm: {proc} Tainted: G        W          5.15.0",
        "kernel: [{time}] Hardware error: Machine Check Exception (MCE) detected on CPU #{num}",
        "kernel: [{time}] general protection fault: 0000 [#1] SMP NOPAGE",
        "{proc}[{pid}]: segfault at 0 ip 00007f9a{num} sp 00007fff error 4 in lib{proc}.so",
        "kernel: [{time}] Call Trace: [<ffffffff8100{num}>] dump_stack+0x1b/0x1d",
        "kernel: [{time}] invalid opcode: 0000 [#1] PREEMPT SMP",
        "kernel: [{time}] Stack dump: 0000000000000000 0000000000000286 ffff8801{num}",
        "kernel: [{time}] Kernel bug detected at net/core/dev.c:{num}!",
    ],
    FailureType.DRIVER_FAILURE.value: [
        "kernel: [{time}] drm:i915_hangcheck_elapsed [i915] *ERROR* Resetting chip after gpu lockup",
        "kernel: [{time}] iwlwifi 0000:02:00.0: Failed to load firmware chunk!",
        "kernel: [{time}] nvidia-modeset: ERROR: GPU:0: Display engine watchdog alive check failed",
        "kernel: [{time}] modprobe: FATAL: Module {unit}_drv not found in directory /lib/modules",
        "kernel: [{time}] r8169 0000:03:00.0 eth0: link down / driver reset triggered",
        "kernel: [{time}] sound wire driver failure: pcm_read error -5",
        "kernel: [{time}] usb 1-1: device descriptor read/64, error -110 (driver timeout)",
        "kernel: [{time}] ath10k_pci 0000:04:00.0: failed to receive control response from driver: timeout",
        "kernel: [{time}] pcieport 0000:00:1c.0: PCIe Bus Error: severity=Uncorrected, type=Transaction Layer",
        "kernel: [{time}] i2c i2c-0: controller timed out, resetting driver bus",
    ],
    FailureType.CONFIGURATION_ERROR.value: [
        "{proc}[{pid}]: [FATAL] Configuration parsing error in /etc/{unit}/config.yaml line {num}: invalid syntax",
        "{proc}[{pid}]: Failed to start: required configuration option '{unit}_path' is missing",
        "{proc}[{pid}]: Syntax error in configuration file /etc/{unit}/{unit}.conf at line {num}: unexpected token",
        "systemd[1]: /etc/systemd/system/{unit}.service:{num}: Unknown key 'ExecStartInvalid' in section 'Service'",
        "{proc}[{pid}]: Invalid permission settings on certificate file /etc/ssl/certs/{unit}.crt: permissions too open",
        "{proc}[{pid}]: Configuration validation error: port {port} out of range [1-65535]",
        "{proc}[{pid}]: Environment variable {unit}_SECRET is required but not set",
        "systemd[1]: [/etc/systemd/system/{unit}.service:{num}] Failed to parse service restart policy",
        "{proc}[{pid}]: Config error: failed to resolve upstream hostname 'bad-db-host.invalid'",
        "{proc}[{pid}]: Invalid JSON in policy file /etc/{unit}/policy.json: expecting property name enclosed in double quotes",
    ],
}


def generate_sample(failure_type: str) -> str:
    """Generate a single realistic failure log string from template."""
    templates = DATASET_TEMPLATES.get(failure_type, DATASET_TEMPLATES[FailureType.SERVICE_FAILURE.value])
    template = random.choice(templates)

    unit = random.choice(["nginx", "apache2", "mysql", "redis", "sshd", "aegis-agent", "docker", "postgres"])
    proc = random.choice(["python3", "mysqld", "node", "java", "nginx", "dockerd", "redis-server"])
    pid = random.randint(100, 32000)
    port = random.choice([80, 443, 3306, 6379, 22, 8080, 5432])
    num = random.randint(1, 99)
    time_str = f"123{num}.{random.randint(100, 999)}"

    return template.format(
        unit=unit,
        proc=proc,
        pid=pid,
        port=port,
        num=num,
        time=time_str,
    )


def generate_dataset(
    output_csv: str | Path = "data/raw/failure_logs.csv",
    manifest_json: str | Path = "data/raw/manifest.json",
    samples_per_class: int = 60,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Generate balanced failure dataset and save CSV and manifest JSON."""
    random.seed(random_seed)

    csv_path = Path(output_csv)
    manifest_path = Path(manifest_json)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, str]] = []

    for failure_type in DATASET_TEMPLATES.keys():
        for _ in range(samples_per_class):
            log_text = generate_sample(failure_type)
            records.append({
                "log_message": log_text,
                "label": failure_type,
            })

    df = pd.DataFrame(records)
    # Shuffle dataset
    df = df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)

    # Save to CSV
    df.to_csv(csv_path, index=False, encoding="utf-8")

    # Generate manifest
    class_counts = df["label"].value_counts().to_dict()
    manifest = {
        "total_samples": len(df),
        "samples_per_class": samples_per_class,
        "class_distribution": class_counts,
        "features": ["log_message"],
        "target": "label",
        "csv_path": str(csv_path),
    }

    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    return df


if __name__ == "__main__":
    df_out = generate_dataset()
    print(f"Generated dataset with {len(df_out)} samples across {df_out['label'].nunique()} classes.")
