#!/usr/bin/env bash
# AegisOS — Live Self-Healing OS Demonstration Script (WSL / Linux)
# Run from WSL: bash scripts/run-demo.sh

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ANSI Colors
BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
YELLOW="\033[33m"
MAGENTA="\033[35m"
RESET="\033[0m"

echo -e "${BOLD}${CYAN}"
echo "=================================================================="
echo "          AegisOS — Autonomous Self-Healing OS Live Demo          "
echo "=================================================================="
echo -e "${RESET}"

# Environment & Python detection
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -f "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python"
else
    echo -e "${YELLOW}--> Setting up Python virtual environment (.venv)...${RESET}"
    python3 -m venv .venv || python -m venv .venv
    PYTHON=".venv/bin/python"
fi

# Verify dependencies and install if missing
if ! "$PYTHON" -c "import uvicorn, fastapi, psutil, sklearn" >/dev/null 2>&1; then
    echo -e "${YELLOW}--> Installing required dependencies from requirements.txt...${RESET}"
    "$PYTHON" -m pip install --upgrade pip -q
    "$PYTHON" -m pip install -r requirements.txt
fi

echo -e "Using Python Runtime: ${MAGENTA}$PYTHON${RESET}"
echo ""

# Step 1: Baseline Health Check
echo -e "${BOLD}${GREEN}[Step 1/5] Checking System Baseline Telemetry & Active Thresholds...${RESET}"
"$PYTHON" agent.py status
echo ""
sleep 2

# Step 2: Triggering Controlled Failure Scenarios
echo -e "${BOLD}${YELLOW}[Step 2/5] Ingesting Synthetic Failure Scenarios & Executing Self-Healing Loop...${RESET}"

scenarios=("service_failure" "cpu_overload" "memory_exhaustion" "disk_exhaustion")
for s in "${scenarios[@]}"; do
    echo -e "${CYAN}--> Triggering Failure Scenario: ${BOLD}${s}${RESET}"
    "$PYTHON" agent.py trigger-scenario --type "$s"
    echo ""
    sleep 2
done

# Step 3: View Incident Audit Logs
echo -e "${BOLD}${GREEN}[Step 3/5] Fetching Recent Incidents from SQLite Audit Log Database...${RESET}"
"$PYTHON" agent.py incidents --limit 10
echo ""
sleep 2

# Step 4: Display Self-Healing Metrics & MTTR
echo -e "${BOLD}${GREEN}[Step 4/5] Computing Self-Healing Success Rate & Mean-Time-To-Recovery (MTTR)...${RESET}"
"$PYTHON" agent.py metrics
echo ""
sleep 2

# Step 5: Web Dashboard Launch Prompt
echo -e "${BOLD}${MAGENTA}[Step 5/5] Launching AegisOS Interactive Web Dashboard & REST API...${RESET}"
echo -e "Dashboard Web Interface: ${BOLD}http://127.0.0.1:8000${RESET}"
echo -e "Press ${BOLD}Ctrl+C${RESET} in terminal to stop the web server when done."
echo ""

"$PYTHON" agent.py serve --host 127.0.0.1 --port 8000
