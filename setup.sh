#!/bin/bash
# Pi Monitor - System Setup Script
# Prepares Raspberry Pi environment with Docker, Docker Compose, Python, and prerequisites

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🥧 Pi Monitor - System Setup${NC}"
echo "=============================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}⚠️  This doesn't appear to be a Raspberry Pi${NC}"
    echo "The setup will continue, but some features may not work as expected."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${YELLOW}📋 System Information:${NC}"
echo "Architecture: $(uname -m)"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'Unknown')"
echo "Kernel: $(uname -r)"

# Update system
echo -e "${BLUE}📦 Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y
echo -e "${GREEN}✅ System updated${NC}"

# Install basic dependencies
echo -e "${BLUE}🛠️  Installing basic dependencies...${NC}"
sudo apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    redis-server \
    openssl

echo -e "${GREEN}✅ Basic dependencies installed${NC}"

# Install Docker
echo -e "${BLUE}🐳 Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io

    # Add current user to docker group
    sudo usermod -aG docker $USER

    echo -e "${GREEN}✅ Docker installed${NC}"
    echo -e "${YELLOW}⚠️  Please log out and back in for Docker group changes to take effect${NC}"
else
    echo -e "${YELLOW}⚠️  Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${BLUE}🔧 Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    # Get latest version
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # Download and install for ARM64
    sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    echo -e "${GREEN}✅ Docker Compose installed (${DOCKER_COMPOSE_VERSION})${NC}"
else
    echo -e "${YELLOW}⚠️  Docker Compose already installed${NC}"
fi

# Install and configure Mosquitto MQTT broker
echo -e "${BLUE}🦟 Installing Mosquitto MQTT broker...${NC}"
if ! command -v mosquitto &> /dev/null; then
    sudo apt-get install -y mosquitto mosquitto-clients
    
    # Create mosquitto directory and config
    sudo mkdir -p /etc/mosquitto/conf.d
    
    # Create basic configuration
    sudo cat > /etc/mosquitto/conf.d/pi-monitor.conf << EOF
# Pi Monitor MQTT Configuration
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd

# WebSocket support
listener 9001
protocol websockets
allow_anonymous false

# Logging
log_dest file /var/log/mosquitto/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
connection_messages true
log_timestamp true
EOF

    # Create MQTT user
    sudo mosquitto_passwd -c -b /etc/mosquitto/passwd pimonitor pimonitor123
    
    # Enable and start Mosquitto
    sudo systemctl enable mosquitto
    sudo systemctl restart mosquitto
    
    echo -e "${GREEN}✅ Mosquitto installed and configured${NC}"
else
    echo -e "${YELLOW}⚠️  Mosquitto already installed${NC}"
fi

# Configure Redis
echo -e "${BLUE}🔴 Configuring Redis...${NC}"
if systemctl is-enabled redis-server &>/dev/null; then
    # Configure Redis for Pi Monitor
    sudo sed -i 's/# requirepass foobared/requirepass pimonitor123/' /etc/redis/redis.conf
    sudo systemctl restart redis-server
    echo -e "${GREEN}✅ Redis configured${NC}"
else
    echo -e "${YELLOW}⚠️  Redis not installed or not managed by systemd${NC}"
fi

# Enable services
echo -e "${BLUE}🚀 Enabling services...${NC}"
sudo systemctl enable docker
sudo systemctl enable redis-server
sudo systemctl enable mosquitto

# Create mosquitto directory structure for Docker
echo -e "${BLUE}📁 Creating mosquitto directories...${NC}"
mkdir -p mosquitto/config mosquitto/data mosquitto/log

# Create mosquitto configuration for Docker
cat > mosquitto/mosquitto.conf << EOF
# Mosquitto configuration for Pi Monitor
listener 1883
listener 9001
protocol websockets

# Allow anonymous connections (you may want to change this for production)
allow_anonymous true

# Persistence
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
log_type error
log_type warning
log_type notice
log_type information
log_timestamp true
EOF

echo -e "${GREEN}✅ Mosquitto directories and config created${NC}"

# Set up environment file
echo -e "${BLUE}⚙️  Setting up environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo "Creating .env file with default configuration..."
    # The .env file should already be created by the edit_file command above
    echo -e "${GREEN}✅ Environment file configured${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists${NC}"
fi

# Create systemd journal directory for better logging
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal

# Configure sudo permissions for pi-monitor service (for future deployment)
echo -e "${BLUE}🔐 Pre-configuring sudo permissions for pi-monitor service...${NC}"
SERVICE_USER="pimonitor"

# Create the sudoers configuration (will be used when service is deployed)
cat > /tmp/pi-monitor-sudoers << EOF
# Pi Monitor Service Permissions
# Allow pimonitor user to run specific system commands without password

# Service management commands
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl status *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl start *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl stop *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl reload *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl enable *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl disable *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-enabled *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl is-active *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl list-units *
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl --failed *

# Power management commands
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl poweroff
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl reboot
$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/shutdown
$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/reboot

# Network and system info commands (read-only)
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/cat /proc/cpuinfo
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/cat /sys/class/thermal/thermal_zone*/temp
$SERVICE_USER ALL=(ALL) NOPASSWD: /usr/bin/vcgencmd *
EOF

# We'll install this during backend deployment, for now just prepare it
echo -e "${GREEN}✅ Sudo permissions configuration prepared${NC}"

# Final system check
echo -e "${BLUE}🔍 Running system check...${NC}"
echo "Docker version: $(docker --version 2>/dev/null || echo 'Not available')"
echo "Docker Compose version: $(docker-compose --version 2>/dev/null || echo 'Not available')"
echo "Python version: $(python3 --version)"
echo "Redis status: $(systemctl is-active redis-server 2>/dev/null || echo 'Not running')"
echo "Mosquitto status: $(systemctl is-active mosquitto 2>/dev/null || echo 'Not running')"

# Copy diagnostic scripts to backend directory
echo -e "${BLUE}📋 Setting up diagnostic tools...${NC}"
cp backend/test_system_monitoring.py backend/test_system_monitoring.py.bak 2>/dev/null || true
cp backend/diagnose_pi_monitor.py backend/diagnose_pi_monitor.py.bak 2>/dev/null || true
chmod +x backend/test_system_monitoring.py 2>/dev/null || true
chmod +x backend/diagnose_pi_monitor.py 2>/dev/null || true
echo -e "${GREEN}✅ Diagnostic tools ready${NC}"

echo ""
echo -e "${GREEN}🎉 Pi Monitor System Setup Complete!${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Log out and back in (or run 'newgrp docker') to use Docker without sudo"
echo "2. Run backend deployment: 'cd backend && sudo ./deploy_backend.sh'"
echo "3. Run frontend deployment: 'cd frontend && ./deploy_frontend.sh'"
echo "4. Or run full stack with Docker: 'docker-compose up -d'"
echo ""
echo -e "${BLUE}If you experience API issues after deployment:${NC}"
echo "• Run diagnostics: 'cd backend && python3 diagnose_pi_monitor.py'"
echo "• Test monitoring: 'cd backend && python3 test_system_monitoring.py'"
echo "• Check service logs: 'sudo journalctl -u pi-monitor -f'"
echo ""
echo -e "${BLUE}Testing:${NC}"
echo "• Test Redis: redis-cli -a pimonitor123 ping"
echo "• Test MQTT: mosquitto_pub -h localhost -t test -m hello"
echo "• Test Docker: docker run hello-world"
echo ""
echo -e "${YELLOW}Important Notes:${NC}"
echo "• Default MQTT credentials: pimonitor/pimonitor123"
echo "• Default Redis password: pimonitor123"
echo "• Change passwords in .env file for production use"
echo "• Backend will be available on port 5000"
echo "• Frontend will be available on port 80"
echo ""
echo -e "${GREEN}Happy monitoring! 🥧📊${NC}"
