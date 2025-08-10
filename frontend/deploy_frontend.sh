#!/bin/bash
# Pi Monitor Frontend Deployment Script
# Builds and deploys the React frontend in Docker with Nginx

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="pi-monitor-frontend"
CONTAINER_NAME="pi-monitor-frontend"
PORT="80"
BACKEND_URL="${BACKEND_URL:-http://localhost:5000}"

echo -e "${BLUE}🥧 Pi Monitor Frontend Deployment${NC}"
echo "==================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    echo "Please install Docker first:"
    echo "curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    echo "Please start Docker daemon: sudo systemctl start docker"
    exit 1
fi

echo -e "${YELLOW}📋 System Information:${NC}"
echo "Docker version: $(docker --version)"
echo "Architecture: $(uname -m)"
echo "Backend URL: $BACKEND_URL"

# Stop and remove existing container if it exists
echo -e "${BLUE}🧹 Cleaning up existing deployment...${NC}"
if docker ps -a --format 'table {{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "Stopping existing container..."
    docker stop $CONTAINER_NAME || true
    echo "Removing existing container..."
    docker rm $CONTAINER_NAME || true
    echo -e "${GREEN}✅ Existing container cleaned up${NC}"
fi

# Remove existing image if it exists
if docker images --format 'table {{.Repository}}:{{.Tag}}' | grep -q "^$IMAGE_NAME:latest$"; then
    echo "Removing existing image..."
    docker rmi $IMAGE_NAME:latest || true
    echo -e "${GREEN}✅ Existing image removed${NC}"
fi

# Check if we have the required files
echo -e "${BLUE}📄 Checking required files...${NC}"
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ package.json not found. Please run this script from the frontend directory.${NC}"
    exit 1
fi

if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}❌ Dockerfile not found in the frontend directory.${NC}"
    exit 1
fi

if [ ! -f "nginx.conf" ]; then
    echo -e "${RED}❌ nginx.conf not found in the frontend directory.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All required files found${NC}"

# Create .env file for build if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}⚙️  Creating .env file...${NC}"
    cat > .env << EOF
REACT_APP_SERVER_URL=$BACKEND_URL
GENERATE_SOURCEMAP=false
EOF
    echo -e "${GREEN}✅ .env file created${NC}"
fi

# Build the Docker image
echo -e "${BLUE}🏗️  Building Docker image...${NC}"
echo "This may take several minutes on first build..."

# Build with platform specification for ARM64 compatibility
if docker build --platform linux/arm64 -t $IMAGE_NAME:latest . ; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${YELLOW}⚠️  ARM64 build failed, trying without platform specification...${NC}"
    if docker build -t $IMAGE_NAME:latest . ; then
        echo -e "${GREEN}✅ Docker image built successfully${NC}"
    else
        echo -e "${RED}❌ Docker image build failed${NC}"
        exit 1
    fi
fi

# Run the container
echo -e "${BLUE}🚀 Starting container...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p $PORT:80 \
    --env-file .env \
    $IMAGE_NAME:latest

# Wait a moment for container to start
sleep 3

# Check if container is running
if docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -q "^$CONTAINER_NAME"; then
    echo -e "${GREEN}✅ Container started successfully${NC}"
else
    echo -e "${RED}❌ Container failed to start${NC}"
    echo "Container logs:"
    docker logs $CONTAINER_NAME
    exit 1
fi

# Test the deployment
echo -e "${BLUE}🧪 Testing deployment...${NC}"
sleep 2

if curl -f -s http://localhost:$PORT/ > /dev/null; then
    echo -e "${GREEN}✅ Frontend is responding on port $PORT${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend might not be ready yet, checking container status...${NC}"
    docker ps --filter "name=$CONTAINER_NAME"
fi

# Show container status and logs
echo -e "${BLUE}📊 Container Status:${NC}"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo -e "${GREEN}🎉 Pi Monitor Frontend Deployment Complete!${NC}"
echo ""
echo "Deployment Information:"
echo "  Image:      $IMAGE_NAME:latest"
echo "  Container:  $CONTAINER_NAME"
echo "  Port:       $PORT"
echo "  URL:        http://localhost:$PORT"
echo "  Backend:    $BACKEND_URL"
echo ""
echo "Useful Commands:"
echo "  View logs:     docker logs $CONTAINER_NAME -f"
echo "  Restart:       docker restart $CONTAINER_NAME"
echo "  Stop:          docker stop $CONTAINER_NAME"
echo "  Remove:        docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME"
echo "  Shell access:  docker exec -it $CONTAINER_NAME sh"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Ensure the backend is running on $BACKEND_URL"
echo "2. Open http://localhost:$PORT in your browser"
echo "3. Check the system status and connection indicators"
echo ""
echo "Note: If you need to change the backend URL, update the BACKEND_URL environment"
echo "variable and redeploy: BACKEND_URL=http://new-backend-url ./deploy_frontend.sh"
