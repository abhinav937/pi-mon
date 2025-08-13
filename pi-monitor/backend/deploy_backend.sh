#!/bin/bash
# Pi Monitor Backend Deployment Script
# Deploys the FastAPI backend as a systemd service on Raspberry Pi

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="pi-monitor"
SERVICE_USER="pimonitor"
INSTALL_DIR="/opt/pi-monitor"
BACKEND_DIR="$INSTALL_DIR/backend"
VENV_DIR="$INSTALL_DIR/venv"
LOG_DIR="/var/log/pi-monitor"

echo -e "${BLUE}🥧 Pi Monitor Backend Deployment${NC}"
echo "=================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Check if we're on a compatible system
if ! command -v systemctl &> /dev/null; then
    echo -e "${RED}❌ systemctl not found. This script requires systemd.${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 System Information:${NC}"
echo "Architecture: $(uname -m)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)"
echo "Python version: $(python3 --version)"

# Create service user
echo -e "${BLUE}👤 Creating service user...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir $INSTALL_DIR --create-home $SERVICE_USER
    echo -e "${GREEN}✅ User $SERVICE_USER created${NC}"
else
    echo -e "${YELLOW}⚠️  User $SERVICE_USER already exists${NC}"
fi

# Create directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $BACKEND_DIR
mkdir -p $LOG_DIR
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR
chown -R $SERVICE_USER:$SERVICE_USER $LOG_DIR
echo -e "${GREEN}✅ Directories created${NC}"

# Install Python dependencies
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-dev build-essential

# Create virtual environment
echo -e "${BLUE}🏗️  Creating virtual environment...${NC}"
sudo -u $SERVICE_USER python3 -m venv $VENV_DIR
echo -e "${GREEN}✅ Virtual environment created${NC}"

# Copy backend files
echo -e "${BLUE}📄 Copying backend files...${NC}"
cp -r ./* $BACKEND_DIR/
chown -R $SERVICE_USER:$SERVICE_USER $BACKEND_DIR
echo -e "${GREEN}✅ Backend files copied${NC}"

# Install Python dependencies
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
sudo -u $SERVICE_USER $VENV_DIR/bin/pip install --upgrade pip
sudo -u $SERVICE_USER $VENV_DIR/bin/pip install -r $BACKEND_DIR/requirements.txt
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create environment file
echo -e "${BLUE}⚙️  Creating environment configuration...${NC}"
cat > $INSTALL_DIR/.env << EOF
# Pi Monitor Backend Configuration
JWT_SECRET=$(openssl rand -base64 32)
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
MQTT_BROKER=localhost
MQTT_PORT=1883
REDIS_URL=redis://localhost:6379
BACKEND_PORT=5000
PUBLISH_INTERVAL=5.0
DEVICE_NAME=$(hostname)
PYTHONPATH=$BACKEND_DIR
EOF
chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/.env
chmod 600 $INSTALL_DIR/.env
echo -e "${GREEN}✅ Environment file created${NC}"

# Create systemd service file
echo -e "${BLUE}🔧 Creating systemd service...${NC}"
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Pi Monitor Backend Service
Documentation=https://github.com/pi-monitor/pi-monitor
After=network.target redis.service mosquitto.service
Wants=redis.service mosquitto.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONPATH=$BACKEND_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$VENV_DIR/bin/uvicorn main_server:combined_app --host 0.0.0.0 --port 5000 --workers 1 --access-log --log-level info
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $INSTALL_DIR
PrivateDevices=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictRealtime=true
RestrictNamespaces=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Systemd service created${NC}"

# Create agent service (for system monitoring)
echo -e "${BLUE}🔧 Creating Pi Agent systemd service...${NC}"
cat > /etc/systemd/system/pi-monitor-agent.service << EOF
[Unit]
Description=Pi Monitor Agent Service
Documentation=https://github.com/pi-monitor/pi-monitor
After=network.target mosquitto.service $SERVICE_NAME.service
Wants=mosquitto.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONPATH=$BACKEND_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$VENV_DIR/bin/python agent.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-monitor-agent

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Pi Agent service created${NC}"

# Enable and start services
echo -e "${BLUE}🚀 Enabling and starting services...${NC}"
systemctl daemon-reload
systemctl enable $SERVICE_NAME.service
systemctl enable pi-monitor-agent.service

# Start the main service
systemctl start $SERVICE_NAME.service
if systemctl is-active --quiet $SERVICE_NAME.service; then
    echo -e "${GREEN}✅ Pi Monitor backend service started successfully${NC}"
else
    echo -e "${RED}❌ Failed to start Pi Monitor backend service${NC}"
    systemctl status $SERVICE_NAME.service --no-pager
    exit 1
fi

# Start the agent service
systemctl start pi-monitor-agent.service
if systemctl is-active --quiet pi-monitor-agent.service; then
    echo -e "${GREEN}✅ Pi Monitor agent service started successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Pi Monitor agent service failed to start (this is optional)${NC}"
    systemctl status pi-monitor-agent.service --no-pager --lines=5
fi

# Create log rotation
echo -e "${BLUE}📋 Setting up log rotation...${NC}"
cat > /etc/logrotate.d/pi-monitor << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    su $SERVICE_USER $SERVICE_USER
}
EOF
echo -e "${GREEN}✅ Log rotation configured${NC}"

echo ""
echo -e "${GREEN}🎉 Pi Monitor Backend Deployment Complete!${NC}"
echo ""
echo "Service Status:"
echo "Main Service:  $(systemctl is-active $SERVICE_NAME.service)"
echo "Agent Service: $(systemctl is-active pi-monitor-agent.service)"
echo ""
echo "Useful Commands:"
echo "  View logs:     journalctl -u $SERVICE_NAME -f"
echo "  Restart:       sudo systemctl restart $SERVICE_NAME"
echo "  Stop:          sudo systemctl stop $SERVICE_NAME"
echo "  Status:        sudo systemctl status $SERVICE_NAME"
echo ""
echo "Backend API will be available at: http://localhost:5000"
echo "Health check: curl http://localhost:5000/health"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Install and configure MQTT broker (Mosquitto)"
echo "2. Install and configure Redis"
echo "3. Deploy the frontend with deploy_frontend.sh"
echo "4. Access the Pi Monitor dashboard at http://localhost"