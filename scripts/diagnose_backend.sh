#!/usr/bin/env bash
# Pi Monitor - Backend Diagnostic Script
# Helps troubleshoot backend issues

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔍 Pi Monitor Backend Diagnostics${NC}"
echo "====================================="

PI_MON_DIR="/home/abhinav/pi-mon"
VENV_DIR="$PI_MON_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"

# Check if running as root
if [[ "$EUID" -ne 0 ]]; then
  echo -e "${YELLOW}⚠️  Some checks may require sudo access${NC}"
fi

echo -e "\n${BLUE}1. System Information${NC}"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Architecture: $(uname -m)"
echo "Python3: $(command -v python3 2>/dev/null || echo 'Not found')"
echo "Python3 version: $(python3 --version 2>/dev/null || echo 'Not available')"

echo -e "\n${BLUE}2. Directory Structure${NC}"
if [ -d "$PI_MON_DIR" ]; then
    echo -e "${GREEN}✅ Pi-mon directory exists: $PI_MON_DIR${NC}"
    ls -la "$PI_MON_DIR"
else
    echo -e "${RED}❌ Pi-mon directory missing: $PI_MON_DIR${NC}"
fi

echo -e "\n${BLUE}3. Virtual Environment${NC}"
if [ -d "$VENV_DIR" ]; then
    echo -e "${GREEN}✅ Virtual environment exists: $VENV_DIR${NC}"
    ls -la "$VENV_DIR/bin/"
    
    if [ -f "$VENV_DIR/bin/python" ]; then
        echo "Python version in venv: $("$VENV_DIR/bin/python" --version 2>/dev/null || echo 'Error')"
        
        # Test imports
        echo "Testing key imports..."
        if "$VENV_DIR/bin/python" -c "import psutil; print('✅ psutil imported')" 2>/dev/null; then
            echo -e "${GREEN}✅ psutil available${NC}"
        else
            echo -e "${RED}❌ psutil not available${NC}"
        fi
    else
        echo -e "${RED}❌ Python not found in venv${NC}"
    fi
else
    echo -e "${RED}❌ Virtual environment missing: $VENV_DIR${NC}"
fi

echo -e "\n${BLUE}4. Backend Files${NC}"
BACKEND_DIR="$PI_MON_DIR/backend"
if [ -d "$BACKEND_DIR" ]; then
    echo -e "${GREEN}✅ Backend directory exists${NC}"
    ls -la "$BACKEND_DIR/"
    
    # Check requirements
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        echo -e "${GREEN}✅ requirements.txt found${NC}"
        cat "$BACKEND_DIR/requirements.txt"
    else
        echo -e "${RED}❌ requirements.txt missing${NC}"
    fi
    
    # Check main files
    for file in "main.py" "server.py" "start_service.py" "config.py"; do
        if [ -f "$BACKEND_DIR/$file" ]; then
            echo -e "${GREEN}✅ $file exists${NC}"
        else
            echo -e "${RED}❌ $file missing${NC}"
        fi
    done
else
    echo -e "${RED}❌ Backend directory missing: $BACKEND_DIR${NC}"
fi

echo -e "\n${BLUE}5. Systemd Service${NC}"
if [ -f "$SERVICE_FILE" ]; then
    echo -e "${GREEN}✅ Service file exists${NC}"
    echo "Service file contents:"
    cat "$SERVICE_FILE"
    
    # Check service status
    if systemctl is-active --quiet pi-monitor-backend.service; then
        echo -e "\n${GREEN}✅ Service is running${NC}"
    else
        echo -e "\n${RED}❌ Service is not running${NC}"
    fi
    
    if systemctl is-enabled --quiet pi-monitor-backend.service; then
        echo -e "${GREEN}✅ Service is enabled${NC}"
    else
        echo -e "${RED}❌ Service is not enabled${NC}"
    fi
    
    # Show recent logs
    echo -e "\nRecent service logs:"
    journalctl -u pi-monitor-backend.service --no-pager -n 20
else
    echo -e "${RED}❌ Service file missing: $SERVICE_FILE${NC}"
fi

echo -e "\n${BLUE}6. Network Status${NC}"
echo "Port 5001 status:"
if netstat -tlnp 2>/dev/null | grep :5001; then
    echo -e "${GREEN}✅ Port 5001 is listening${NC}"
else
    echo -e "${RED}❌ Port 5001 is not listening${NC}"
fi

echo -e "\n${BLUE}7. Process Check${NC}"
echo "Python processes:"
if pgrep -f "pi-monitor\|start_service.py" >/dev/null; then
    echo -e "${GREEN}✅ Pi-monitor processes found${NC}"
    ps aux | grep -E "(pi-monitor|start_service.py)" | grep -v grep
else
    echo -e "${RED}❌ No pi-monitor processes found${NC}"
fi

echo -e "\n${BLUE}8. Manual Test${NC}"
echo "Testing backend manually..."
cd "$PI_MON_DIR/backend" 2>/dev/null || echo "Cannot cd to backend directory"

if [ -f "$VENV_DIR/bin/python" ] && [ -f "$BACKEND_DIR/start_service.py" ]; then
    echo "Attempting to start backend manually (will timeout after 10s)..."
    timeout 10s "$VENV_DIR/bin/python" start_service.py || echo "Manual start test completed"
else
    echo -e "${RED}❌ Cannot test manually - missing files${NC}"
fi

echo -e "\n${BLUE}9. Recommendations${NC}"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}🔧 Create virtual environment: python3 -m venv $VENV_DIR${NC}"
fi

if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}🔧 Create systemd service file${NC}"
fi

if ! systemctl is-active --quiet pi-monitor-backend.service; then
    echo -e "${YELLOW}🔧 Start the service: sudo systemctl start pi-monitor-backend.service${NC}"
fi

if ! netstat -tlnp 2>/dev/null | grep :5001; then
    echo -e "${YELLOW}🔧 Backend is not listening on port 5001${NC}"
fi

echo -e "\n${GREEN}🎯 Diagnostic complete!${NC}"
echo "Run the deploy script to fix issues: sudo ./deploy.sh"
