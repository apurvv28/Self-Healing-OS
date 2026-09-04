#!/usr/bin/env bash
# AegisOS — WSL environment bootstrap (Phase 1, Task 2)
# Run from an INTERACTIVE Ubuntu WSL terminal (sudo password required):
#   cd "/mnt/d/VIT/Sem 5/Operating System/Self-Healing-OS"
#   bash scripts/setup-wsl.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if ! sudo -n true 2>/dev/null; then
    echo "This script requires sudo. You will be prompted for your Ubuntu password."
    sudo -v || { echo "ERROR: sudo authentication failed."; exit 1; }
fi

echo "==> AegisOS WSL setup"
echo "    Project: $PROJECT_ROOT"

echo "==> Updating package index..."
sudo apt-get update -qq

echo "==> Installing base packages..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    systemd \
    systemd-sysv \
    git \
    curl \
    procps \
    kmod

echo "==> Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Verifying monitoring targets..."
checks=(
    "journalctl --version"
    "systemctl --version"
    "dmesg --version"
    "test -r /proc/meminfo"
    "test -d /sys/class"
    "systemctl is-system-running"
)

for cmd in "${checks[@]}"; do
    if eval "$cmd" >/dev/null 2>&1; then
        echo "  OK  $cmd"
    else
        echo "  FAIL $cmd"
        exit 1
    fi
done

echo ""
echo "==> WSL environment ready."
echo "    Activate venv:  source .venv/bin/activate"
echo "    Run tests:      pytest tests/"
echo ""
echo "Note: kdump/kernel crash analysis (Phase 8) requires a full Linux VM"
echo "      (e.g. AWS EC2). See docs/aws-fallback-setup.md"
echo ""
echo "Verify setup: bash scripts/verify-wsl.sh"
