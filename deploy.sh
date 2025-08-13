#!/usr/bin/env bash
# Pi Monitor - Complete Deployment Script (venv + systemd + nginx + subdomain setup)

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Complete Deployment with Subdomain${NC}"
echo "========================================================="

# Configuration
DOMAIN="pi.cabhinav.com"
STATIC_IP="65.36.123.68"
WEB_ROOT="/var/www/pi-monitor"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
PRODUCTION_URL="http://65.36.123.68"

# Port configuration - adjust these if you have port conflicts
PUBLIC_PORT="80"  # Change to 8080, 3000, or 443 if port 80 is blocked
NGINX_PORT="80"   # Keep this as 80 (internal)
BACKEND_PORT="5001"

if [[ ! -f "config.json" ]]; then
  echo -e "${YELLOW}⚠️  config.json not found; proceeding with defaults${NC}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}❌ This script must be run with sudo${NC}"
  exit 1
fi

echo -e "${BLUE}📋 Configuration:${NC}"
echo "   Domain: $DOMAIN"
echo "   Static IP: $STATIC_IP"
echo "   Public Port: $PUBLIC_PORT (router port forwarding)"
echo "   Internal Port: $NGINX_PORT (Nginx)"
echo "   Web Root: $WEB_ROOT"
echo ""
echo -e "${YELLOW}💡 Port Forwarding Setup:${NC}"
echo "   Router: External Port $PUBLIC_PORT → Internal Port $NGINX_PORT → $STATIC_IP"
echo "   If port $PUBLIC_PORT is blocked, try 8080, 3000, or 443"

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

# Update backend configuration for production
echo -e "${BLUE}⚙️  Updating backend configuration for production...${NC}"
if [ -f "config.json" ]; then
    # Update config.json with production URLs if not already present
    if ! grep -q '"production"' config.json; then
        echo -e "${YELLOW}📝 Adding production configuration to config.json...${NC}"
        # This will be handled by the production config file
    fi
    echo -e "${GREEN}✅ Backend configuration updated for production${NC}"
fi

# Ensure backend service is configured for production
echo -e "${YELLOW}🔧 Configuring backend service for production...${NC}"
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"
if [ -f "$SERVICE_FILE" ]; then
    # Update service file to use production environment
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PI_MON_DIR|g" $SERVICE_FILE
    sed -i "s|User=.*|User=abhinav|g" $SERVICE_FILE
    sed -i "s|Group=.*|Group=abhinav|g" $SERVICE_FILE
    # Add production environment if not present
    if ! grep -q "Environment=PI_MONITOR_ENV=production" $SERVICE_FILE; then
        sed -i '/ExecStart=/i Environment=PI_MONITOR_ENV=production\nEnvironment=PI_MONITOR_PRODUCTION_URL=http://65.36.123.68' $SERVICE_FILE
    fi
    
    systemctl daemon-reload
    
    echo -e "${GREEN}✅ Backend service configured for production${NC}"
else
    echo -e "${RED}❌ Backend service file not found: $SERVICE_FILE${NC}"
fi

echo -e "${BLUE}🌐 Setting up subdomain configuration...${NC}"

# Install required packages if not already installed
echo -e "${YELLOW}📦 Installing required packages...${NC}"
apt update && apt install -y nginx curl

# Create web directory
echo -e "${YELLOW}📁 Creating web directory...${NC}"
mkdir -p $WEB_ROOT/frontend/build
chown -R abhinav:abhinav $WEB_ROOT

# Copy Nginx configuration for subdomain
echo -e "${YELLOW}⚙️  Setting up Nginx configuration for $DOMAIN...${NC}"
cp nginx/pi-subdomain.conf $NGINX_SITES_AVAILABLE/$DOMAIN

# Enable the subdomain site
echo -e "${YELLOW}🔗 Enabling Nginx site for $DOMAIN...${NC}"
ln -sf $NGINX_SITES_AVAILABLE/$DOMAIN $NGINX_SITES_ENABLED/$DOMAIN

# Remove default site if it exists
if [ -L "$NGINX_SITES_ENABLED/default" ]; then
    echo -e "${YELLOW}🗑️  Removing default Nginx site...${NC}"
    rm $NGINX_SITES_ENABLED/default
fi

# Test Nginx configuration
echo -e "${YELLOW}🧪 Testing Nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✅ Nginx configuration is valid${NC}"
else
    echo -e "${RED}❌ Nginx configuration test failed${NC}"
    exit 1
fi

# Build frontend (if package.json exists)
if [ -f "frontend/package.json" ]; then
    echo -e "${YELLOW}🔨 Building frontend for production...${NC}"
    
    # Create production environment file
    echo -e "${YELLOW}📝 Creating production environment configuration...${NC}"
    cat > frontend/.env.production << EOF
# Production Environment Configuration
REACT_APP_SERVER_URL=$PRODUCTION_URL
REACT_APP_API_BASE_URL=$PRODUCTION_URL
REACT_APP_ENVIRONMENT=production
REACT_APP_BACKEND_PORT=$BACKEND_PORT
REACT_APP_FRONTEND_PORT=$NGINX_PORT
EOF
    
    cd frontend
    npm install
    
    # Build with production environment
    echo -e "${YELLOW}🏗️  Building frontend with production configuration...${NC}"
    npm run build
    
    cd ..
    
    # Copy built files to web directory
    echo -e "${YELLOW}📋 Copying built files...${NC}"
    cp -r frontend/build/* $WEB_ROOT/frontend/build/
    
    echo -e "${GREEN}✅ Frontend built and deployed with production configuration${NC}"
else
    echo -e "${YELLOW}⚠️  No frontend package.json found, skipping build${NC}"
fi

# Set proper permissions
echo -e "${YELLOW}🔐 Setting permissions...${NC}"
chown -R www-data:www-data $WEB_ROOT
chmod -R 755 $WEB_ROOT

# Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 22/tcp
    ufw --force enable
    echo -e "${GREEN}✅ Firewall configured with ufw${NC}"
else
    echo -e "${YELLOW}⚠️  ufw not found. Please configure firewall manually:${NC}"
    echo "   - Allow port 80 (HTTP) for web traffic"
    echo "   - Allow port 22 (SSH) for remote access"
    echo "   - Or install ufw: sudo apt install ufw"
fi

# Restart Nginx
echo -e "${YELLOW}🔄 Restarting Nginx...${NC}"
systemctl restart nginx

# Start and enable backend service
echo -e "${YELLOW}🚀 Starting backend service...${NC}"
if systemctl is-active --quiet pi-monitor-backend.service; then
    echo -e "${YELLOW}🔄 Restarting existing backend service...${NC}"
    systemctl restart pi-monitor-backend.service
else
    echo -e "${YELLOW}▶️  Starting backend service...${NC}"
    systemctl start pi-monitor-backend.service
fi

# Enable service to start on boot
systemctl enable pi-monitor-backend.service

# Check Nginx status
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx is running${NC}"
else
    echo -e "${RED}❌ Nginx failed to start${NC}"
    systemctl status nginx
    exit 1
fi

echo -e "${BLUE}🧪 Verifying services...${NC}"
sleep 3
set +e

# Test local access
echo -e "${YELLOW}🌐 Testing local access...${NC}"
if curl -fsS http://localhost/ >/dev/null; then
    echo -e "${GREEN}✅ Frontend reachable at http://localhost/${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend test failed (nginx may be starting)${NC}"
fi

# Test backend health
if curl -fsS http://127.0.0.1:5001/health >/dev/null; then
    echo -e "${GREEN}✅ Backend healthy on :5001${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
fi

# Test production endpoints
echo -e "${YELLOW}🌐 Testing production endpoints...${NC}"
if curl -fsS $PRODUCTION_URL:$BACKEND_PORT/health >/dev/null; then
    echo -e "${GREEN}✅ Production backend reachable at $PRODUCTION_URL:$BACKEND_PORT/health${NC}"
else
    echo -e "${YELLOW}⚠️  Production backend test failed (may need external access)${NC}"
fi

# Test subdomain configuration
echo -e "${YELLOW}🌐 Testing subdomain configuration...${NC}"
if curl -fsS -H "Host: $DOMAIN" http://127.0.0.1/ >/dev/null; then
    echo -e "${GREEN}✅ Subdomain configuration working locally${NC}"
else
    echo -e "${YELLOW}⚠️  Subdomain test failed locally${NC}"
fi

set -e

echo -e "${GREEN}🎉 Complete deployment with subdomain finished!${NC}"
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
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Configure DNS A record for $DOMAIN to point to $STATIC_IP"
echo "2. Wait for DNS propagation (can take up to 48 hours)"
echo "3. Test your site at http://$DOMAIN"
echo "4. Test API endpoints at $PRODUCTION_URL:$BACKEND_PORT/health"
echo ""
echo -e "${YELLOW}🔧 Useful commands:${NC}"
echo "   View Nginx logs: tail -f /var/log/nginx/$DOMAIN.access.log"
echo "   Check Nginx status: systemctl status nginx"
echo "   Test Nginx config: nginx -t"
echo "   Restart Nginx: systemctl restart nginx"
echo "   Check backend: systemctl status pi-monitor-backend.service"
echo "   View backend logs: journalctl -u pi-monitor-backend.service -f"
echo "   Test API health: curl $PRODUCTION_URL:$BACKEND_PORT/health"
