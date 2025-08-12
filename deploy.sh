#!/usr/bin/env bash
# Pi Monitor - Complete Deployment Script (venv + systemd + nginx + user setup)

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Complete Deployment${NC}"
echo "========================================="

if [[ ! -f "config.json" ]]; then
  echo -e "${YELLOW}⚠️  config.json not found; proceeding with defaults${NC}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}❌ This script must be run with sudo${NC}"
  exit 1
fi

echo -e "${BLUE}👤 Setting up user and group...${NC}"

# Check if user 'abhinav' exists, create if not
if ! id "abhinav" &>/dev/null; then
    echo -e "${YELLOW}⚠️  User 'abhinav' does not exist. Creating...${NC}"
    
    # Create group 'abhinav' if it doesn't exist
    if ! getent group "abhinav" &>/dev/null; then
        echo "Creating group 'abhinav'..."
        groupadd abhinav
    fi
    
    # Create user 'abhinav' with home directory
    echo "Creating user 'abhinav'..."
    useradd -m -g abhinav -s /bin/bash abhinav
    
    # Set a default password (you can change this later)
    echo "abhinav:raspberry" | chpasswd
    
    echo -e "${GREEN}✅ User 'abhinav' created successfully${NC}"
else
    echo -e "${GREEN}✅ User 'abhinav' already exists${NC}"
fi

# Ensure the pi-mon directory exists and has correct ownership
PI_MON_DIR="/home/abhinav/pi-mon"
if [ ! -d "$PI_MON_DIR" ]; then
    echo "Creating pi-mon directory..."
    mkdir -p "$PI_MON_DIR"
    chown abhinav:abhinav "$PI_MON_DIR"
fi

echo -e "${BLUE}🔧 Running comprehensive setup script...${NC}"
sudo bash "$SCRIPT_DIR/scripts/setup_venv_systemd.sh" "$SCRIPT_DIR"

echo -e "${BLUE}🧪 Verifying services...${NC}"
sleep 3
set +e
curl -fsS http://127.0.0.1/ >/dev/null && echo -e "${GREEN}✅ Frontend reachable at http://<host>/${NC}" || echo -e "${YELLOW}⚠️  Frontend test failed (nginx may be starting)${NC}"
curl -fsS http://127.0.0.1:5001/health >/dev/null && echo -e "${GREEN}✅ Backend healthy on :5001${NC}" || echo -e "${RED}❌ Backend health check failed${NC}"
set -e

echo -e "${GREEN}🎉 Complete deployment finished!${NC}"
echo -e "${BLUE}🌐 Access:${NC} http://<host>/"
echo -e "${BLUE}👤 User:${NC} abhinav (password: raspberry - change this!)"
echo -e "${BLUE}📁 Directory:${NC} /home/abhinav/pi-mon"
echo -e "${BLUE}🔧 Service:${NC} pi-monitor-backend.service"
