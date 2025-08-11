#!/bin/bash
# Pi Monitor - Simple Deployment Script
# Uses configuration from config.json

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Simple Deployment${NC}"
echo "====================================="

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo -e "${RED}❌ config.json not found!${NC}"
    echo "Please create a config.json file first."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Load configuration values
BACKEND_PORT=$(python -c "import json; print(json.load(open('config.json'))['ports']['backend'])")
FRONTEND_PORT=$(python -c "import json; print(json.load(open('config.json'))['ports']['frontend'])")
PROJECT_NAME=$(python -c "import json; print(json.load(open('config.json'))['project']['name'])")
VERSION=$(python -c "import json; print(json.load(open('config.json'))['project']['version'])")

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Project: $PROJECT_NAME v$VERSION"
echo "  Backend Port: $BACKEND_PORT"
echo "  Frontend Port: $FRONTEND_PORT"

# Build and deploy backend
echo -e "${BLUE}🏗️  Building backend...${NC}"
docker build -t pi-monitor-backend -f backend/Dockerfile backend

# Stop existing containers
echo -e "${BLUE}🔄 Stopping existing containers...${NC}"
docker stop pi-monitor-backend pi-monitor-frontend 2>/dev/null || true
docker rm pi-monitor-backend pi-monitor-frontend 2>/dev/null || true

# Start backend
echo -e "${BLUE}🚀 Starting backend...${NC}"
docker run -d \
    --name pi-monitor-backend \
    --restart unless-stopped \
    -p $BACKEND_PORT:$BACKEND_PORT \
    pi-monitor-backend

# Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for backend to start...${NC}"
sleep 5

# Test backend
echo -e "${BLUE}🧪 Testing backend...${NC}"
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is responding${NC}"
else
    echo -e "${RED}❌ Backend not responding${NC}"
    echo "Backend logs:"
    docker logs pi-monitor-backend --tail 10
    exit 1
fi

# Build and deploy frontend natively
echo -e "${BLUE}🏗️  Building frontend natively...${NC}"
# Install Apache and required modules if not present
if ! command -v apache2 &> /dev/null; then
    echo -e "${YELLOW}📦 Installing Apache...${NC}"
    sudo apt update
    sudo apt install -y apache2
fi
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite headers deflate
# Build React app
cd frontend
npm install
npm run build
cd ..
# Copy build to Apache root
sudo cp -r frontend/build/* /var/www/html/
sudo chown -R www-data:www-data /var/www/html/
# Copy Apache config
sudo cp frontend/apache.conf /etc/apache2/sites-available/000-default.conf
# Restart Apache
sudo systemctl restart apache2

# Wait for frontend to be ready
echo -e "${BLUE}⏳ Waiting for frontend to start...${NC}"
sleep 5

# Test frontend
echo -e "${BLUE}🧪 Testing frontend...${NC}"
if curl -s http://localhost:$FRONTEND_PORT > /dev/null; then
    echo -e "${GREEN}✅ Frontend is responding${NC}"
else
    echo -e "${RED}❌ Frontend not responding${NC}"
    echo "Apache logs:"
    sudo tail -n 10 /var/log/apache2/error.log
    exit 1
fi

# Show status (only backend container now)
echo -e "${BLUE}📊 Container status:${NC}"
docker ps -f name=pi-monitor-backend

echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "  Backend: http://localhost:$BACKEND_PORT"
echo "  Frontend: http://localhost:$FRONTEND_PORT (native via Apache)"
echo "  Health: http://localhost:$BACKEND_PORT/health"

echo -e "${BLUE}💡 Useful commands:${NC}"
echo "  View logs: docker logs pi-monitor-backend"
echo "  Apache logs: sudo tail -f /var/log/apache2/error.log"
echo "  Stop backend: docker stop pi-monitor-backend"
echo "  Restart Apache: sudo systemctl restart apache2"
