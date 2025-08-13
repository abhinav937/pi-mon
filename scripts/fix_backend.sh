#!/usr/bin/env bash
# Quick fix for backend service issues

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔧 Quick Backend Fix${NC}"
echo "========================"

PI_MON_DIR="/home/abhinav/pi-mon"
VENV_DIR="$PI_MON_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"

# Check if running as root
if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}❌ This script must be run with sudo${NC}"
  exit 1
fi

echo -e "\n${BLUE}1. Checking file permissions...${NC}"
chown -R abhinav:abhinav "$PI_MON_DIR"
chmod +x "$PI_MON_DIR/backend/start_service.py"
chmod +x "$PI_MON_DIR/backend/main.py"

echo -e "\n${BLUE}2. Verifying Python path...${NC}"
if [ -f "$VENV_DIR/bin/python" ]; then
    echo -e "${GREEN}✅ Python found: $VENV_DIR/bin/python${NC}"
    echo "Python version: $("$VENV_DIR/bin/python" --version)"
else
    echo -e "${RED}❌ Python not found in venv${NC}"
    exit 1
fi

echo -e "\n${BLUE}3. Testing start_service.py...${NC}"
if [ -f "$PI_MON_DIR/backend/start_service.py" ]; then
    echo -e "${GREEN}✅ start_service.py exists${NC}"
    
    # Test if it can be imported
    if "$VENV_DIR/bin/python" -c "import sys; sys.path.append('$PI_MON_DIR/backend'); import start_service; print('✅ Import successful')" 2>/dev/null; then
        echo -e "${GREEN}✅ start_service.py can be imported${NC}"
    else
        echo -e "${RED}❌ start_service.py has import issues${NC}"
        echo "Testing with verbose output:"
        "$VENV_DIR/bin/python" -c "import sys; sys.path.append('$PI_MON_DIR/backend'); import start_service" 2>&1 || true
    fi
else
    echo -e "${RED}❌ start_service.py not found${NC}"
    exit 1
fi

echo -e "\n${BLUE}4. Updating service file...${NC}"
# Update the service file with correct paths
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pi Monitor Backend Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=abhinav
Group=abhinav
WorkingDirectory=$PI_MON_DIR/backend
Environment=PYTHONUNBUFFERED=1
Environment=PI_MONITOR_ENV=production
Environment=PI_MONITOR_PRODUCTION_URL=http://65.36.123.68
EnvironmentFile=$PI_MON_DIR/backend/.env
ExecStart=$VENV_DIR/bin/python $PI_MON_DIR/backend/start_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-monitor

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PI_MON_DIR/backend $PI_MON_DIR

# Auto-restart on failure
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Service file updated${NC}"

echo -e "\n${BLUE}5. Reloading systemd...${NC}"
systemctl daemon-reload

echo -e "\n${BLUE}6. Starting service...${NC}"
systemctl enable pi-monitor-backend.service
systemctl start pi-monitor-backend.service

sleep 3

echo -e "\n${BLUE}7. Checking service status...${NC}"
if systemctl is-active --quiet pi-monitor-backend.service; then
    echo -e "${GREEN}✅ Service is running!${NC}"
    systemctl status pi-monitor-backend.service --no-pager -l
else
    echo -e "${RED}❌ Service failed to start${NC}"
    echo "Recent logs:"
    journalctl -u pi-monitor-backend.service --no-pager -n 20
    exit 1
fi

echo -e "\n${BLUE}8. Testing backend...${NC}"
sleep 2
if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
    echo -e "${GREEN}✅ Backend is responding!${NC}"
    curl -s http://127.0.0.1:5001/health
else
    echo -e "${YELLOW}⚠️  Backend not responding yet (may need more time)${NC}"
fi

echo -e "\n${GREEN}🎉 Backend fix complete!${NC}"
echo "The service should now be running properly."
