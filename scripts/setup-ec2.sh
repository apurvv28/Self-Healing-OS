#!/usr/bin/env bash
# ==============================================================================
# AegisOS — AWS EC2 One-Command Quickstart & Deployment Script
# ==============================================================================
# Prepares environment, configures firewall, auto-cleans port 8000, and launches
# the Web Dashboard server on 0.0.0.0:8000.
# ==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}====================================================================${NC}"
echo -e "${GREEN}🛡️  AegisOS — AWS EC2 Server Launcher${NC}"
echo -e "${CYAN}====================================================================${NC}"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJECT_DIR"

# 1. Environment Setup (skips if already setup)
if [ ! -d ".venv" ]; then
    echo -e "\n${YELLOW}[1/4] Installing system dependencies & Python environment...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-venv python3-pip systemd ufw
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip systemd
    fi
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
else
    echo -e "\n${YELLOW}[1/4] Activating Python virtual environment...${NC}"
    source .venv/bin/activate
fi

# 2. Configure Linux Firewall (UFW)
echo -e "\n${YELLOW}[2/4] Ensuring Linux firewall permits port 8000...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw allow 8000/tcp > /dev/null 2>&1 || true
    echo "Port 8000 allowed in ufw firewall."
fi

# 3. Clean up any stale process occupying port 8000
echo -e "\n${YELLOW}[3/4] Checking port 8000 availability...${NC}"
if command -v fuser &> /dev/null; then
    sudo fuser -k 8000/tcp > /dev/null 2>&1 || true
fi

# 4. Detect EC2 Public IP
PUBLIC_IP=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 || curl -s --connect-timeout 2 ifconfig.me || echo "15.252.139.132")

echo -e "\n${YELLOW}[4/4] Starting AegisOS Web Server on 0.0.0.0:8000...${NC}"
echo -e "${GREEN}====================================================================${NC}"
echo -e "${GREEN}🎉 AegisOS Web Server is launching!${NC}"
echo -e "${CYAN}🌐 Access Web Dashboard at:${NC} http://${PUBLIC_IP}:8000"
echo -e "${YELLOW}⚠️  IMPORTANT:${NC} Ensure AWS EC2 Security Group allows Inbound TCP on Port 8000!"
echo -e "${CYAN}⚡ To run live CPU stress in a 2nd terminal:${NC}"
echo -e "   python scripts/stress_scenario.py --mode cpu --duration 30"
echo -e "${GREEN}====================================================================${NC}\n"

# Launch server bound to 0.0.0.0:8000
python agent.py serve --host 0.0.0.0 --port 8000
