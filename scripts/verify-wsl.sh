#!/usr/bin/env bash
# AegisOS — WSL environment verification (no sudo required)
# Run from WSL: bash scripts/verify-wsl.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PASS=0
FAIL=0

check() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  [PASS] $label"
        PASS=$((PASS + 1))
    else
        echo "  [FAIL] $label"
        FAIL=$((FAIL + 1))
    fi
}

echo "==> AegisOS WSL verification"
echo ""

echo "-- OS --"
check "Ubuntu detected" test -f /etc/os-release
grep PRETTY_NAME /etc/os-release 2>/dev/null || true

echo ""
echo "-- systemd --"
check "systemd running" systemctl is-system-running

echo ""
echo "-- Monitoring tools --"
check "journalctl available" journalctl --version
check "systemctl available" systemctl --version
check "dmesg available" dmesg --version
check "/proc/meminfo readable" test -r /proc/meminfo
check "/sys/class accessible" test -d /sys/class

echo ""
echo "-- Python --"
check "python3 available" python3 --version
check "pip available" pip3 --version
check "venv module available" python3 -m venv --help
check "project venv exists" test -d .venv
if test -d .venv; then
    check "psutil installed in venv" .venv/bin/pip show psutil
fi

echo ""
echo "-- Summary --"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Run 'bash scripts/setup-wsl.sh' in an interactive Ubuntu terminal (sudo required)."
    exit 1
fi

echo ""
echo "WSL environment is ready for AegisOS development."
