#!/bin/bash
# Pi Monitor - Pi Deployment Script
# Deploys only the backend for Pi monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Pi Backend Deployment${NC}"
echo "============================================="

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
PROJECT_NAME=$(python -c "import json; print(json.load(open('config.json'))['project']['name'])")
VERSION=$(python -c "import json; print(json.load(open('config.json'))['project']['version'])")

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Project: $PROJECT_NAME v$VERSION"
echo "  Backend Port: $BACKEND_PORT"
echo "  Target: Raspberry Pi Backend Only"

# Stop existing backend container
echo -e "${BLUE}🔄 Stopping existing backend container...${NC}"
docker stop pi-monitor-backend 2>/dev/null || true
docker rm pi-monitor-backend 2>/dev/null || true

# Build backend with correct context
echo -e "${BLUE}🏗️  Building backend...${NC}"
docker build -t pi-monitor-backend -f backend/Dockerfile .

# Start backend
echo -e "${BLUE}🚀 Starting backend...${NC}"
docker run -d \
    --name pi-monitor-backend \
    --restart unless-stopped \
    -p $BACKEND_PORT:$BACKEND_PORT \
    --privileged \
    -v /proc:/host/proc:ro \
    -v /sys:/host/sys:ro \
    -v /var/run:/var/run:ro \
    -e HOST_PROC=/host/proc \
    -e HOST_SYS=/host/sys \
    pi-monitor-backend

# Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for backend to start...${NC}"
sleep 10

# Test backend
echo -e "${BLUE}🧪 Testing backend...${NC}"
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is responding${NC}"
else
    echo -e "${RED}❌ Backend not responding${NC}"
    echo "Backend logs:"
    docker logs pi-monitor-backend --tail 20
    echo ""
    echo "Trying to restart backend..."
    docker restart pi-monitor-backend
    sleep 5
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
        echo -e "${GREEN}✅ Backend is now responding after restart${NC}"
    else
        echo -e "${RED}❌ Backend still not responding${NC}"
        exit 1
    fi
fi

# Test root endpoint
echo -e "${BLUE}🧪 Testing root endpoint...${NC}"
if curl -s http://localhost:$BACKEND_PORT/ > /dev/null; then
    echo -e "${GREEN}✅ Root endpoint working${NC}"
else
    echo -e "${RED}❌ Root endpoint failed${NC}"
fi

# Show container status
echo -e "${BLUE}📊 Container status:${NC}"
docker ps -f name=pi-monitor-backend

echo ""
echo -e "${GREEN}🎉 Pi Backend deployment completed successfully!${NC}"
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "  Backend: http://localhost:$BACKEND_PORT"
echo "  Health: http://localhost:$BACKEND_PORT/health"
echo "  Root: http://localhost:$BACKEND_PORT/"

echo -e "${BLUE}💡 Useful commands:${NC}"
echo "  View logs: docker logs pi-monitor-backend"
echo "  Stop backend: docker stop pi-monitor-backend"
echo "  Start backend: docker start pi-monitor-backend"
echo "  Restart backend: docker restart pi-monitor-backend"
echo "  Shell access: docker exec -it pi-monitor-backend /bin/bash"

echo -e "${BLUE}🔧 Monitoring commands:${NC}"
echo "  System stats: curl -H 'Authorization: Bearer <token>' http://localhost:$BACKEND_PORT/api/system"
echo "  Get token: curl -X POST http://localhost:$BACKEND_PORT/api/auth/token -H 'Content-Type: application/json' -d '{\"username\":\"abhinav\",\"password\":\"kavachi\"}'"
