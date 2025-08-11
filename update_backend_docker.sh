#!/bin/bash
# Pi Monitor Backend - Simple Docker Update
# Updates the backend container with new code

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Pi Monitor Backend - Docker Update${NC}"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "backend/simple_server.py" ]; then
    echo -e "${RED}❌ Error: Must be run from pi-mon project root directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Please run: cd ~/pi-mon && ./update_backend_docker.sh"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "Please start Docker and try again"
    exit 1
fi

# Pull latest changes from git
echo -e "${BLUE}📥 Pulling latest changes from git...${NC}"
if git pull origin main; then
    echo -e "${GREEN}✅ Git pull successful${NC}"
else
    echo -e "${YELLOW}⚠️  Git pull failed or no changes - continuing with local files${NC}"
fi

# Check if container exists
if docker ps -a -q -f name=pi-monitor-backend | grep -q .; then
    echo -e "${BLUE}🔄 Updating existing container...${NC}"
    
    # Stop and remove existing container
    docker stop pi-monitor-backend
    docker rm pi-monitor-backend
    echo -e "${GREEN}✅ Old container stopped and removed${NC}"
else
    echo -e "${YELLOW}⚠️  No existing container found - will create new one${NC}"
fi

# Build new image
echo -e "${BLUE}🏗️  Building new Docker image...${NC}"
docker build -t pi-monitor-backend ./backend
echo -e "${GREEN}✅ New image built successfully${NC}"

# Run new container
echo -e "${BLUE}🚀 Starting new container...${NC}"
docker run -d \
    --name pi-monitor-backend \
    --restart unless-stopped \
    -p 5001:5001 \
    pi-monitor-backend

echo -e "${GREEN}✅ New container started successfully${NC}"

# Wait a moment for startup
echo -e "${BLUE}⏳ Waiting for container to start...${NC}"
sleep 5

# Check container status
echo -e "${BLUE}📊 Container status:${NC}"
docker ps -f name=pi-monitor-backend

# Test the API
echo -e "${BLUE}🧪 Testing API...${NC}"
if curl -s http://localhost:5001/health > /dev/null; then
    echo -e "${GREEN}✅ API is responding${NC}"
else
    echo -e "${YELLOW}⚠️  API not responding yet - checking logs${NC}"
    echo "Container logs:"
    docker logs pi-monitor-backend --tail 10
fi

echo ""
echo -e "${GREEN}🎉 Backend update complete!${NC}"
echo -e "${BLUE}💡 Useful commands:${NC}"
echo "  • Check status: docker ps -f name=pi-monitor-backend"
echo "  • View logs: docker logs pi-monitor-backend"
echo "  • Test API: curl http://localhost:5001/health"
echo "  • Stop container: docker stop pi-monitor-backend"
echo "  • Start container: docker start pi-monitor-backend"
echo "  • Restart container: docker restart pi-monitor-backend"
