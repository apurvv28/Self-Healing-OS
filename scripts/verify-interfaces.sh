#!/usr/bin/env bash
# AegisOS — Verify read access to all monitoring targets (Phase 1, Task 3)
# Run from WSL: bash scripts/verify-interfaces.sh

set -uo pipefail

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }

echo "==> AegisOS monitoring interface verification"
echo ""

# --- journalctl ---
echo "-- journalctl --"
if journalctl --version >/dev/null 2>&1; then
    pass "journalctl binary available"
else
    fail "journalctl binary available"
fi

if journalctl -n 1 -o json >/dev/null 2>&1; then
    pass "journalctl JSON read (last 1 entry)"
else
    fail "journalctl JSON read (last 1 entry)"
fi

if journalctl -p err -n 1 --no-pager >/dev/null 2>&1; then
    pass "journalctl error-priority filter"
else
    fail "journalctl error-priority filter"
fi

# --- systemctl ---
echo ""
echo "-- systemctl --"
if systemctl --version >/dev/null 2>&1; then
    pass "systemctl binary available"
else
    fail "systemctl binary available"
fi

if systemctl is-system-running >/dev/null 2>&1; then
    pass "systemd is running"
else
    fail "systemd is running"
fi

if systemctl --failed --no-pager >/dev/null 2>&1; then
    pass "systemctl --failed readable"
else
    fail "systemctl --failed readable"
fi

if systemctl show ssh.service -p ActiveState >/dev/null 2>&1 || \
   systemctl show -.mount -p ActiveState >/dev/null 2>&1; then
    pass "systemctl show unit properties"
else
    warn "systemctl show unit properties (no test unit found)"
fi

# --- dmesg ---
echo ""
echo "-- dmesg --"
if dmesg --version >/dev/null 2>&1; then
    pass "dmesg binary available"
else
    fail "dmesg binary available"
fi

if dmesg -l err,warn -T 2>/dev/null | head -1 >/dev/null; then
    pass "dmesg error/warn level read"
else
    if dmesg 2>/dev/null | head -1 >/dev/null; then
        warn "dmesg readable but level filter unsupported"
    else
        fail "dmesg read"
    fi
fi

# --- /proc ---
echo ""
echo "-- /proc --"
for f in /proc/meminfo /proc/loadavg /proc/stat /proc/uptime /proc/mounts; do
    if test -r "$f"; then
        pass "readable: $f"
    else
        fail "readable: $f"
    fi
done

if test -r /proc/self/status; then
    pass "readable: /proc/self/status (process info)"
else
    fail "readable: /proc/self/status"
fi

# --- /sys ---
echo ""
echo "-- /sys --"
for p in /sys/class/block /sys/module /sys/fs/cgroup; do
    if test -d "$p"; then
        pass "accessible: $p"
    else
        warn "not found: $p (may differ on WSL)"
    fi
done

if ls /sys/class/block/ >/dev/null 2>&1; then
    pass "block devices listed in /sys/class/block"
else
    warn "block devices listed in /sys/class/block"
fi

# --- psutil (Python) ---
echo ""
echo "-- psutil (Python) --"
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import psutil; psutil.cpu_percent(); psutil.virtual_memory(); psutil.disk_usage('/')" 2>/dev/null; then
        pass "psutil import and basic reads"
    elif test -d ".venv" && .venv/bin/python -c "import psutil" 2>/dev/null; then
        pass "psutil available in project .venv"
    else
        warn "psutil not installed — run scripts/setup-wsl.sh"
    fi
else
    fail "python3 not available"
fi

# --- Summary ---
echo ""
echo "-- Summary --"
echo "  Passed:   $PASS"
echo "  Warnings: $WARN"
echo "  Failed:   $FAIL"

if [ "$FAIL" -gt 0 ]; then
    echo ""
    echo "Some monitoring targets are unavailable. See docs/system-interfaces.md"
    exit 1
fi

echo ""
echo "All required monitoring interfaces are accessible."
