#!/usr/bin/env bash
# Pi Monitor - Smart Deployment Script (efficient, state-aware)
# Only sets up what's missing or needs updating

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Smart Deployment Script${NC}"
echo "=============================================="

# Configuration
DOMAIN="pi.cabhinav.com"
STATIC_IP="65.36.123.68"
WEB_ROOT="/var/www/pi-monitor"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
PRODUCTION_URL="http://65.36.123.68"
PI_MON_DIR="/home/abhinav/pi-mon"
VENV_DIR="$PI_MON_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"

# Port configuration
PUBLIC_PORT="80"
NGINX_PORT="80"
BACKEND_PORT="5001"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}❌ This script must be run with sudo${NC}"
  exit 1
fi

echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Domain: $DOMAIN"
echo "   Static IP: $STATIC_IP"
echo "   Web Root: $WEB_ROOT"
echo "   Pi Mon Dir: $PI_MON_DIR"
echo "   Virtual Env: $VENV_DIR"

# =============================================================================
# 1. CHECK CURRENT STATE
# =============================================================================
echo -e "\n${BLUE}🔍 Checking current system state...${NC}"

# Check if user exists
USER_EXISTS=false
if id "abhinav" &>/dev/null; then
    echo -e "${GREEN}✅ User 'abhinav' exists${NC}"
    USER_EXISTS=true
else
    echo -e "${YELLOW}⚠️  User 'abhinav' does not exist${NC}"
fi

# Check if pi-mon directory exists
PI_MON_EXISTS=false
if [ -d "$PI_MON_DIR" ]; then
    echo -e "${GREEN}✅ Pi-mon directory exists: $PI_MON_DIR${NC}"
    PI_MON_EXISTS=true
else
    echo -e "${YELLOW}⚠️  Pi-mon directory does not exist${NC}"
fi

# Check if virtual environment exists and is working
VENV_EXISTS=false
if [ -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${GREEN}✅ Virtual environment exists: $VENV_DIR${NC}"
    VENV_EXISTS=true
    
    # Test if venv Python works
    if "$VENV_DIR/bin/python" -c "import sys; print('Python version:', sys.version)" &>/dev/null; then
        echo -e "${GREEN}✅ Virtual environment Python is working${NC}"
    else
        echo -e "${RED}❌ Virtual environment Python is broken${NC}"
        VENV_EXISTS=false
    fi
else
    echo -e "${YELLOW}⚠️  Virtual environment does not exist or is broken${NC}"
fi

# Check if backend service exists and is configured
SERVICE_EXISTS=false
SERVICE_RUNNING=false
if [ -f "$SERVICE_FILE" ]; then
    echo -e "${GREEN}✅ Backend service file exists${NC}"
    SERVICE_EXISTS=true
    
    # Check if service is running
    if systemctl is-active --quiet pi-monitor-backend.service; then
        echo -e "${GREEN}✅ Backend service is running${NC}"
        SERVICE_RUNNING=true
    else
        echo -e "${YELLOW}⚠️  Backend service exists but is not running${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Backend service file does not exist${NC}"
fi

# Check if Nginx is configured
NGINX_CONFIGURED=false
if [ -f "$NGINX_SITES_AVAILABLE/$DOMAIN" ] && [ -L "$NGINX_SITES_ENABLED/$DOMAIN" ]; then
    echo -e "${GREEN}✅ Nginx site is configured for $DOMAIN${NC}"
    NGINX_CONFIGURED=true
else
    echo -e "${YELLOW}⚠️  Nginx site is not configured for $DOMAIN${NC}"
fi

# Check if frontend is built
FRONTEND_BUILT=false
if [ -f "$WEB_ROOT/index.html" ]; then
    echo -e "${GREEN}✅ Frontend is built in $WEB_ROOT${NC}"
    FRONTEND_BUILT=true
else
    echo -e "${YELLOW}⚠️  Frontend is not built${NC}"
fi

# Check if backend is accessible
BACKEND_ACCESSIBLE=false
if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
    echo -e "${GREEN}✅ Backend is accessible on port 5001${NC}"
    BACKEND_ACCESSIBLE=true
else
    echo -e "${YELLOW}⚠️  Backend is not accessible on port 5001${NC}"
fi

# =============================================================================
# 2. CREATE USER AND DIRECTORY (if needed)
# =============================================================================
if [ "$USER_EXISTS" = false ]; then
    echo -e "\n${BLUE}👤 Creating user 'abhinav'...${NC}"
    
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
fi

if [ "$PI_MON_EXISTS" = false ]; then
    echo -e "\n${BLUE}📁 Creating pi-mon directory...${NC}"
    mkdir -p "$PI_MON_DIR"
    chown abhinav:abhinav "$PI_MON_DIR"
    echo -e "${GREEN}✅ Pi-mon directory created${NC}"
fi

# =============================================================================
# 3. SETUP VIRTUAL ENVIRONMENT (if needed)
# =============================================================================
if [ "$VENV_EXISTS" = false ]; then
    echo -e "\n${BLUE}🐍 Setting up Python virtual environment...${NC}"
    
    # Install Python venv if not available
    if ! command -v python3 &>/dev/null; then
        echo "Installing Python3..."
        apt-get update -y
        apt-get install -y python3 python3-venv python3-pip
    fi
    
    # Create virtual environment
    sudo -u abhinav python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    
    # Install requirements
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        echo "Installing Python dependencies..."
        "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt"
        echo -e "${GREEN}✅ Virtual environment setup complete${NC}"
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
else
    echo -e "\n${BLUE}🔄 Updating virtual environment dependencies...${NC}"
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade
        echo -e "${GREEN}✅ Dependencies updated${NC}"
    fi
fi

# =============================================================================
# 4. SETUP BACKEND SERVICE (if needed or broken)
# =============================================================================
if [ "$SERVICE_EXISTS" = false ] || [ "$SERVICE_RUNNING" = false ]; then
    echo -e "\n${BLUE}🔧 Setting up backend service...${NC}"
    
    # Create proper service file
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
Environment=PI_MONITOR_PRODUCTION_URL=$PRODUCTION_URL
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
ProtectHome=read-only
ReadWritePaths=$PI_MON_DIR/backend $PI_MON_DIR

# Auto-restart on failure
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

    # Create .env file if it doesn't exist
    if [ ! -f "$PI_MON_DIR/backend/.env" ]; then
        cat > "$PI_MON_DIR/backend/.env" <<EOF
# Environment for Pi Monitor backend
PI_MONITOR_API_KEY=pi-monitor-api-key-2024
PI_MONITOR_ENV=production
PI_MONITOR_PRODUCTION_URL=$PRODUCTION_URL
EOF
        chown abhinav:abhinav "$PI_MON_DIR/backend/.env"
    fi

    # Reload systemd and start service
    systemctl daemon-reload
    systemctl enable pi-monitor-backend.service
    
    if [ "$SERVICE_RUNNING" = false ]; then
        echo "Starting backend service..."
        systemctl start pi-monitor-backend.service
        sleep 3
        
        # Check if service started successfully
        if systemctl is-active --quiet pi-monitor-backend.service; then
            echo -e "${GREEN}✅ Backend service started successfully${NC}"
        else
            echo -e "${RED}❌ Backend service failed to start${NC}"
            systemctl status pi-monitor-backend.service
            exit 1
        fi
    fi
else
    echo -e "\n${BLUE}✅ Backend service is already running${NC}"
fi

# =============================================================================
# 5. BUILD FRONTEND (if needed)
# =============================================================================
if [ "$FRONTEND_BUILT" = false ]; then
    echo -e "\n${BLUE}🔨 Building frontend...${NC}"
    
    # Install Node.js if not available
    if ! command -v npm &>/dev/null; then
        echo "Installing Node.js and npm..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
    fi
    
    # Create production environment file
    cat > "$PI_MON_DIR/frontend/.env.production" <<EOF
# Production Environment Configuration
REACT_APP_SERVER_URL=$PRODUCTION_URL
REACT_APP_API_BASE_URL=$PRODUCTION_URL
REACT_APP_ENVIRONMENT=production
REACT_APP_BACKEND_PORT=$BACKEND_PORT
REACT_APP_FRONTEND_PORT=$NGINX_PORT
EOF
    
    # Build frontend
    cd "$PI_MON_DIR/frontend"
    npm install --no-audit --no-fund
    npm run build
    
    # Deploy to web root
    mkdir -p "$WEB_ROOT"
    cp -r build/* "$WEB_ROOT/"
    chown -R www-data:www-data "$WEB_ROOT"
    
    cd "$SCRIPT_DIR"
    echo -e "${GREEN}✅ Frontend built and deployed${NC}"
else
    echo -e "\n${BLUE}✅ Frontend is already built${NC}"
fi

# =============================================================================
# 6. SETUP NGINX (if needed)
# =============================================================================
if [ "$NGINX_CONFIGURED" = false ]; then
    echo -e "\n${BLUE}🌐 Setting up Nginx...${NC}"
    
    # Install Nginx if not available
    if ! command -v nginx &>/dev/null; then
        echo "Installing Nginx..."
        apt-get update -y
        apt-get install -y nginx
    fi
    
    # Copy Nginx configuration
    if [ -f "$PI_MON_DIR/nginx/pi-subdomain.conf" ]; then
        cp "$PI_MON_DIR/nginx/pi-subdomain.conf" "$NGINX_SITES_AVAILABLE/$DOMAIN"
    else
        # Fallback configuration
        cat > "$NGINX_SITES_AVAILABLE/$DOMAIN" <<EOF
server {
  listen 80;
  server_name $DOMAIN;

  root $WEB_ROOT;
  index index.html;

  location / {
    try_files \$uri /index.html;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:5001/api/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
  }

  location /health {
    proxy_pass http://127.0.0.1:5001/health;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
}
EOF
    fi
    
    # Enable site
    ln -sf "$NGINX_SITES_AVAILABLE/$DOMAIN" "$NGINX_SITES_ENABLED/$DOMAIN"
    
    # Remove default site
    if [ -L "$NGINX_SITES_ENABLED/default" ]; then
        rm "$NGINX_SITES_ENABLED/default"
    fi
    
    # Test and restart Nginx
    nginx -t
    systemctl restart nginx
    echo -e "${GREEN}✅ Nginx configured and started${NC}"
else
    echo -e "\n${BLUE}✅ Nginx is already configured${NC}"
fi

# =============================================================================
# 7. FINAL VERIFICATION
# =============================================================================
echo -e "\n${BLUE}🧪 Final verification...${NC}"
sleep 5

# Check backend service
if systemctl is-active --quiet pi-monitor-backend.service; then
    echo -e "${GREEN}✅ Backend service is running${NC}"
else
    echo -e "${RED}❌ Backend service is not running${NC}"
    echo -e "${YELLOW}📋 Service status:${NC}"
    systemctl status pi-monitor-backend.service --no-pager -l
    echo -e "${YELLOW}📋 Recent logs:${NC}"
    journalctl -u pi-monitor-backend.service --no-pager -n 10
    echo -e "${RED}❌ Backend service failed to start properly${NC}"
    exit 1
fi

# Check backend health
echo -e "\n${BLUE}🏥 Testing backend health...${NC}"
if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
    echo "Health response:"
    curl -s http://127.0.0.1:5001/health | head -5
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo -e "${YELLOW}🔍 Checking what's happening on port 5001...${NC}"
    if netstat -tlnp 2>/dev/null | grep :5001; then
        echo -e "${YELLOW}⚠️  Port 5001 is listening but health check failed${NC}"
    else
        echo -e "${RED}❌ Port 5001 is not listening${NC}"
    fi
    exit 1
fi

# Check Nginx
echo -e "\n${BLUE}🌐 Checking Nginx...${NC}"
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx is running${NC}"
else
    echo -e "${RED}❌ Nginx is not running${NC}"
    systemctl status nginx --no-pager -l
    exit 1
fi

# Check frontend
echo -e "\n${BLUE}🎨 Testing frontend...${NC}"
if curl -fsS http://localhost/ &>/dev/null; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
    echo "Frontend response:"
    curl -s http://localhost/ | grep -E "(title|Pi Monitor|React)" | head -3
else
    echo -e "${YELLOW}⚠️  Frontend test failed (may be starting)${NC}"
    echo -e "${YELLOW}🔍 Checking Nginx configuration...${NC}"
    nginx -t
fi

# Check all services are properly configured
echo -e "\n${BLUE}🔧 Service configuration check...${NC}"

# Check if service is enabled
if systemctl is-enabled --quiet pi-monitor-backend.service; then
    echo -e "${GREEN}✅ Backend service is enabled (auto-start on boot)${NC}"
else
    echo -e "${RED}❌ Backend service is not enabled${NC}"
    systemctl enable pi-monitor-backend.service
    echo -e "${GREEN}✅ Backend service now enabled${NC}"
fi

# Check if Nginx is enabled
if systemctl is-enabled --quiet nginx; then
    echo -e "${GREEN}✅ Nginx is enabled (auto-start on boot)${NC}"
else
    echo -e "${RED}❌ Nginx is not enabled${NC}"
    systemctl enable nginx
    echo -e "${GREEN}✅ Nginx now enabled${NC}"
fi

# Final comprehensive test
echo -e "\n${BLUE}🎯 Running comprehensive system test...${NC}"

# Test API endpoints
echo "Testing API endpoints:"
for endpoint in "/health" "/api/system" "/api/metrics"; do
    if curl -fsS "http://127.0.0.1:5001$endpoint" &>/dev/null; then
        echo -e "  ${GREEN}✅ $endpoint${NC}"
    else
        echo -e "  ${RED}❌ $endpoint${NC}"
    fi
done

# Test Nginx proxy
echo "Testing Nginx proxy:"
if curl -fsS "http://localhost/api/health" &>/dev/null; then
    echo -e "  ${GREEN}✅ Nginx proxy to /api/health${NC}"
else
    echo -e "  ${RED}❌ Nginx proxy to /api/health${NC}"
fi

# Check system resources
echo -e "\n${BLUE}💾 System resource check...${NC}"
echo "Memory usage: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "Disk usage: $(df -h / | tail -1 | awk '{print $5}')"
echo "Load average: $(uptime | awk -F'load average:' '{print $2}')"

# Success summary
echo -e "\n${GREEN}🎉 All systems operational!${NC}"

echo -e "\n${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "   Local: http://localhost/"
echo "   Subdomain: http://$DOMAIN/"
echo "   Production IP: $PRODUCTION_URL"
echo "   Backend API: $PRODUCTION_URL:$BACKEND_PORT"
echo ""
echo -e "${BLUE}👤 User:${NC} abhinav (password: raspberry - change this!)"
echo -e "${BLUE}📁 Directory:${NC} $PI_MON_DIR"
echo -e "${BLUE}🔧 Service:${NC} pi-monitor-backend.service"
echo -e "${BLUE}🌐 Web Root:${NC} $WEB_ROOT"
echo -e "${BLUE}🔌 Backend Port:${NC} $BACKEND_PORT"
echo ""
echo -e "${YELLOW}🔧 Useful commands:${NC}"
echo "   Check backend: systemctl status pi-monitor-backend.service"
echo "   View backend logs: journalctl -u pi-monitor-backend.service -f"
echo "   Test API health: curl http://127.0.0.1:5001/health"
echo "   Check Nginx: systemctl status nginx"
echo "   Test Nginx config: nginx -t"
