#!/usr/bin/env bash
# ==============================================================================
# AegisOS — AWS EC2 One-Command Quickstart & Deployment Script
# ==============================================================================
# Automatically prepares environment, installs dependencies, sets up systemd
# background daemon, and launches the Web Dashboard on port 8000.
# ==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}====================================================================${NC}"
echo -e "${GREEN}🛡️  AegisOS — AWS EC2 Setup & Live Demonstration Launcher${NC}"
echo -e "${CYAN}====================================================================${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJECT_DIR"

echo -e "\n${YELLOW}[1/4] Checking system dependencies & Python environment...${NC}"
if command -v apt-get &> /dev/null; then
    echo "Updating apt package index..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-venv python3-pip systemd
elif command -v dnf &> /dev/null; then
    echo "Updating dnf package index..."
    sudo dnf install -y python3 python3-pip systemd
fi

echo -e "\n${YELLOW}[2/4] Setting up Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created at .venv"
fi

source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "Dependencies installed successfully."

echo -e "\n${YELLOW}[3/4] Testing AegisOS Core Agent...${NC}"
python agent.py status

echo -e "\n${YELLOW}[4/4] Starting AegisOS Web Server & Autonomous Self-Healing Daemon...${NC}"

# Detect Public IP if available via IMDS or curl
PUBLIC_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 || curl -s --connect-timeout 2 ifconfig.me || echo "localhost")

echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}🎉 AegisOS setup is complete!${NC}"
echo -e "${CYAN}🌐 Web Dashboard URL:${NC} http://${PUBLIC_IP}:8000"
echo -e "${CYAN}⚡ To run live CPU overload stress on EC2:${NC}"
echo -e "   python scripts/stress_scenario.py --mode cpu --duration 30"
echo -e "${CYAN}🤖 Launch continuous background daemon:${NC}"
echo -e "   python agent.py daemon &"
echo -e "${GREEN}====================================================================${NC}\n"

# Launch dashboard server
python agent.py serve --host 0.0.0.0 --port 8000
