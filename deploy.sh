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
echo "   Web Root: $WEB_ROOT"

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
    echo -e "${YELLOW}🔨 Building frontend...${NC}"
    cd frontend
    npm install
    npm run build
    cd ..
    
    # Copy built files to web directory
    echo -e "${YELLOW}📋 Copying built files...${NC}"
    cp -r frontend/build/* $WEB_ROOT/frontend/build/
else
    echo -e "${YELLOW}⚠️  No frontend package.json found, skipping build${NC}"
fi

# Set proper permissions
echo -e "${YELLOW}🔐 Setting permissions...${NC}"
chown -R www-data:www-data $WEB_ROOT
chmod -R 755 $WEB_ROOT

# Configure firewall
echo -e "${YELLOW}🔥 Configuring firewall...${NC}"
ufw allow 80/tcp
ufw allow 22/tcp
ufw --force enable

# Restart Nginx
echo -e "${YELLOW}🔄 Restarting Nginx...${NC}"
systemctl restart nginx

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
echo ""
echo -e "${BLUE}👤 User:${NC} abhinav (password: raspberry - change this!)"
echo -e "${BLUE}📁 Directory:${NC} $PI_MON_DIR"
echo -e "${BLUE}🔧 Service:${NC} pi-monitor-backend.service"
echo -e "${BLUE}🌐 Web Root:${NC} $WEB_ROOT"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Configure DNS A record for $DOMAIN to point to $STATIC_IP"
echo "2. Wait for DNS propagation (can take up to 48 hours)"
echo "3. Test your site at http://$DOMAIN"
echo ""
echo -e "${YELLOW}🔧 Useful commands:${NC}"
echo "   View Nginx logs: tail -f /var/log/nginx/$DOMAIN.access.log"
echo "   Check Nginx status: systemctl status nginx"
echo "   Test Nginx config: nginx -t"
echo "   Restart Nginx: systemctl restart nginx"
echo "   Check backend: systemctl status pi-monitor-backend.service"
