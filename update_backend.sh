#!/bin/bash
# Pi Monitor Backend Update Script
# Updates and restarts the systemd backend service only

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="pi-monitor"
SERVICE_USER="pimonitor"
INSTALL_DIR="/opt/pi-monitor"
BACKEND_DIR="$INSTALL_DIR/backend"

echo -e "${BLUE}🔄 Pi Monitor Backend Update${NC}"
echo "==============================="

# Check if we're in the right directory
if [ ! -f "backend/main_server.py" ]; then
    echo -e "${RED}❌ Error: Must be run from pi-mon project root directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Please run: cd ~/pi-mon && ./update_backend.sh"
    exit 1
fi

# Check if systemd service exists
if ! systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    echo -e "${RED}❌ Error: $SERVICE_NAME systemd service not found${NC}"
    echo "Please run the deployment script first: cd backend && sudo ./deploy_backend.sh"
    exit 1
fi

# Pull latest changes from git
echo -e "${BLUE}📥 Pulling latest changes from git...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✅ Git pull successful${NC}"
else
    echo -e "${YELLOW}⚠️  Git pull failed or no changes - continuing with local files${NC}"
fi

# Stop the service before updating
echo -e "${BLUE}⏹️  Stopping backend service...${NC}"
if systemctl is-active --quiet $SERVICE_NAME.service; then
    sudo systemctl stop $SERVICE_NAME.service
    echo -e "${GREEN}✅ Service stopped${NC}"
else
    echo -e "${YELLOW}⚠️  Service was not running${NC}"
fi

# Copy updated backend files
echo -e "${BLUE}📄 Updating backend files...${NC}"
sudo cp backend/*.py $BACKEND_DIR/
sudo cp backend/requirements.txt $BACKEND_DIR/
sudo chown -R $SERVICE_USER:$SERVICE_USER $BACKEND_DIR
echo -e "${GREEN}✅ Backend files updated${NC}"

# Update Python dependencies if requirements.txt changed
echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
if ! sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install -r $BACKEND_DIR/requirements.txt --quiet; then
    echo -e "${YELLOW}⚠️  Dependency update failed - continuing anyway${NC}"
else
    echo -e "${GREEN}✅ Dependencies up to date${NC}"
fi

# Start the service
echo -e "${BLUE}🚀 Starting backend service...${NC}"
sudo systemctl start $SERVICE_NAME.service

# Wait a moment for startup
sleep 2

# Check service status
if systemctl is-active --quiet $SERVICE_NAME.service; then
    echo -e "${GREEN}✅ Backend service started successfully${NC}"
    
    # Test the API
    echo -e "${BLUE}🧪 Testing API...${NC}"
    if curl -s http://localhost:5000/health > /dev/null; then
        echo -e "${GREEN}✅ API is responding${NC}"
        
        # Show service status
        echo -e "${BLUE}📊 Service Status:${NC}"
        sudo systemctl status $SERVICE_NAME.service --no-pager --lines=5
    else
        echo -e "${YELLOW}⚠️  API not responding yet - check logs if needed${NC}"
    fi
else
    echo -e "${RED}❌ Backend service failed to start${NC}"
    echo -e "${BLUE}📋 Service logs:${NC}"
    sudo journalctl -u $SERVICE_NAME.service --no-pager --lines=10
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Backend update complete!${NC}"
echo -e "${BLUE}💡 Useful commands:${NC}"
echo "  • Check status: sudo systemctl status $SERVICE_NAME.service"
echo "  • View logs: sudo journalctl -u $SERVICE_NAME.service -f"
echo "  • Test API: curl http://localhost:5000/health"
echo "  • Stop service: sudo systemctl stop $SERVICE_NAME.service"
echo "  • Start service: sudo systemctl start $SERVICE_NAME.service"
