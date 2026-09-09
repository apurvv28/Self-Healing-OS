#!/usr/bin/env python3
"""AegisOS Stress Scenario Generator for Live Demonstration.

Induces controlled CPU infinite loops, memory pressure, disk consumption,
or service crashes to demonstrate live self-healing on Linux / EC2 instances.

Usage:
    python scripts/stress_scenario.py --mode cpu --duration 30
    python scripts/stress_scenario.py --mode memory --duration 20
    python scripts/stress_scenario.py --mode service --name nginx
"""

from __future__ import annotations

import argparse
import math
import multiprocessing
import os
import sys
import time
from datetime import datetime


def _cpu_infinite_loop(stop_event: multiprocessing.Event) -> None:
    """Infinite loop burning 100% CPU on a single thread."""
    pid = os.getpid()
    print(f"🔥 [CPU Burner Worker PID {pid}] Started infinite calculation loop...")
    x = 0.0001
    while not stop_event.is_set():
        # High CPU intensity math operations
        x = math.sin(x) + math.cos(x) + math.sqrt(abs(x) + 1.0)
        if x > 1000.0:
            x = 0.0001


def run_cpu_stress(duration: int, cores: int | None = None) -> None:
    """Spawn worker processes running infinite loops to max out CPU utilization."""
    num_cores = cores or multiprocessing.cpu_count()
    print(f"\n[⚡ AegisOS Stress] Launching Infinite CPU Loop on {num_cores} core(s) for {duration} seconds...")
    stop_event = multiprocessing.Event()
    processes: list[multiprocessing.Process] = []

    for _ in range(num_cores):
        p = multiprocessing.Process(target=_cpu_infinite_loop, args=(stop_event,), daemon=True)
        p.start()
        processes.append(p)

    pids = [p.pid for p in processes]
    print(f"🚀 [CPU Stress Active] Worker PIDs: {pids}")
    print("👉 AegisOS telemetry & detector should catch high CPU utilization now!\n")

    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user.")
    finally:
        print("🛑 Stopping CPU stress workers...")
        stop_event.set()
        for p in processes:
            p.join(timeout=2.0)
            if p.is_alive():
                p.terminate()
        print("✅ CPU stress workers terminated.\n")


def run_memory_stress(duration: int, size_mb: int = 500) -> None:
    """Allocate blocks of memory to simulate memory leak/pressure."""
    print(f"\n[⚡ AegisOS Stress] Allocating ~{size_mb}MB memory for {duration} seconds...")
    data_blocks = []
    chunk_size = 50 * 1024 * 1024  # 50MB chunks
    chunks_count = max(1, size_mb // 50)

    try:
        for i in range(chunks_count):
            print(f"  └ Allocating chunk {i + 1}/{chunks_count} (50MB)...")
            data_blocks.append(bytearray(chunk_size))
            time.sleep(0.5)

        print(f"🚀 [Memory Stress Active] Allocated total ~{len(data_blocks) * 50}MB.")
        print("👉 AegisOS detector should trigger memory exhaustion alert!\n")
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user.")
    finally:
        print("🛑 Releasing allocated memory...")
        data_blocks.clear()
        print("✅ Memory released.\n")


def run_disk_stress(size_mb: int = 200, target_path: str = "/tmp/aegisos_dummy_file.dat") -> None:
    """Create a temporary large dummy file to simulate high disk usage."""
    print(f"\n[⚡ AegisOS Stress] Writing {size_mb}MB dummy file to {target_path}...")
    try:
        with open(target_path, "wb") as f:
            chunk = b"X" * (1024 * 1024)  # 1MB
            for _ in range(size_mb):
                f.write(chunk)
        print(f"🚀 [Disk Stress Active] File created at {target_path}")
        print("👉 AegisOS detector should flag high disk partition usage!\n")
        time.sleep(10)
    finally:
        if os.path.exists(target_path):
            os.remove(target_path)
            print(f"✅ Cleaned up dummy file {target_path}.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisOS Live Stress Generator for EC2 Demonstrations")
    parser.add_argument(
        "--mode",
        choices=["cpu", "memory", "disk", "all"],
        default="cpu",
        help="Stress mode to execute (default: cpu)",
    )
    parser.add_argument("--duration", type=int, default=20, help="Duration in seconds (default: 20)")
    parser.add_argument("--memory-mb", type=int, default=500, help="Memory size in MB for memory stress")
    parser.add_argument("--disk-mb", type=int, default=200, help="Disk dummy file size in MB for disk stress")

    args = parser.parse_args()

    print("=" * 65)
    print("🛡️  AegisOS Live Demonstration Stress Generator")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    if args.mode == "cpu":
        run_cpu_stress(duration=args.duration)
    elif args.mode == "memory":
        run_memory_stress(duration=args.duration, size_mb=args.memory_mb)
    elif args.mode == "disk":
        run_disk_stress(size_mb=args.disk_mb)
    elif args.mode == "all":
        run_cpu_stress(duration=10)
        run_memory_stress(duration=10, size_mb=300)

    print("🏁 Stress scenario complete.")


if __name__ == "__main__":
    main()
