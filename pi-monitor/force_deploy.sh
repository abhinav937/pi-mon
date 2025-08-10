#!/bin/bash
# Pi Monitor - Force Deployment Script
# Handles port conflicts, removes previous versions, and deploys latest with full cleanup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="pi-monitor"
COMPOSE_FILE="docker-compose.yml"
CONFLICTING_SERVICES=("redis" "redis-server" "mosquitto")
CONFLICTING_PORTS=(6379 1883 5000 80 9001)

echo -e "${BLUE}🥧 Pi Monitor - Force Deployment${NC}"
echo "=================================="
echo -e "${YELLOW}⚠️  This will completely remove all existing pi-monitor containers, images, and volumes!${NC}"
echo ""

# Ask for confirmation unless --yes flag is provided
if [[ "$1" != "--yes" ]] && [[ "$1" != "-y" ]]; then
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

echo ""
echo -e "${PURPLE}🔍 System Information:${NC}"
echo "Architecture: $(uname -m)"
echo "OS: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'"' -f2 || echo 'Unknown')"
echo "Docker version: $(docker --version 2>/dev/null || echo 'Not installed')"
echo "Docker Compose version: $(docker-compose --version 2>/dev/null || echo 'Not installed')"
echo ""

# Function to check if a port is in use
check_port() {
    local port=$1
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find what's using a port
find_port_user() {
    local port=$1
    echo "Port $port usage:"
    netstat -tulpn 2>/dev/null | grep ":$port " || ss -tulpn 2>/dev/null | grep ":$port " || echo "  No specific process found"
}

# Function to stop system services safely
stop_system_service() {
    local service=$1
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo -e "${YELLOW}  🛑 Stopping system service: $service${NC}"
        sudo systemctl stop "$service" || echo -e "${RED}    ❌ Failed to stop $service${NC}"
        
        # Also disable it to prevent auto-restart
        if systemctl is-enabled --quiet "$service" 2>/dev/null; then
            echo -e "${YELLOW}  🚫 Disabling auto-start for: $service${NC}"
            sudo systemctl disable "$service" || echo -e "${RED}    ❌ Failed to disable $service${NC}"
        fi
    fi
}

# Step 1: Check for Docker and Docker Compose
echo -e "${BLUE}📦 Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo "Please install Docker first: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running!${NC}"
    echo "Please start Docker: sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are ready${NC}"

# Step 2: Check for docker-compose.yml
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo -e "${RED}❌ $COMPOSE_FILE not found!${NC}"
    echo "Please run this script from the pi-monitor directory."
    exit 1
fi

# Step 3: Stop conflicting system services
echo ""
echo -e "${BLUE}🔍 Checking for conflicting system services...${NC}"
for service in "${CONFLICTING_SERVICES[@]}"; do
    stop_system_service "$service"
done

# Step 4: Check for port conflicts
echo ""
echo -e "${BLUE}🔌 Checking for port conflicts...${NC}"
conflicts_found=false
for port in "${CONFLICTING_PORTS[@]}"; do
    if check_port "$port"; then
        echo -e "${YELLOW}⚠️  Port $port is in use:${NC}"
        find_port_user "$port"
        conflicts_found=true
    fi
done

if [[ "$conflicts_found" == true ]]; then
    echo ""
    echo -e "${YELLOW}⚠️  Some ports are still in use. Attempting to resolve...${NC}"
    
    # Try to kill processes using our ports (be careful here)
    for port in "${CONFLICTING_PORTS[@]}"; do
        if check_port "$port"; then
            echo -e "${YELLOW}  🔧 Attempting to free port $port...${NC}"
            # Find and kill processes using these specific ports (only if they're likely ours)
            pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | grep -E '^[0-9]+$' || true)
            if [[ -n "$pids" ]]; then
                for pid in $pids; do
                    if ps -p "$pid" -o comm= 2>/dev/null | grep -E "(redis|mosquitto)" &>/dev/null; then
                        echo -e "${YELLOW}    🔪 Killing process $pid using port $port${NC}"
                        sudo kill -TERM "$pid" 2>/dev/null || true
                        sleep 2
                        sudo kill -KILL "$pid" 2>/dev/null || true
                    fi
                done
            fi
        fi
    done
fi

# Step 5: Complete Docker cleanup
echo ""
echo -e "${BLUE}🧹 Performing complete Docker cleanup...${NC}"

# Stop all pi-monitor containers
echo -e "${YELLOW}  🛑 Stopping all pi-monitor containers...${NC}"
docker-compose down --remove-orphans || echo "No containers to stop"

# Remove all pi-monitor containers (including stopped ones)
containers=$(docker ps -aq --filter "name=$PROJECT_NAME" 2>/dev/null || true)
if [[ -n "$containers" ]]; then
    echo -e "${YELLOW}  🗑️  Removing all pi-monitor containers...${NC}"
    docker rm -f $containers || echo "Some containers couldn't be removed"
fi

# Remove all pi-monitor images
images=$(docker images --filter "reference=*$PROJECT_NAME*" -q 2>/dev/null || true)
if [[ -n "$images" ]]; then
    echo -e "${YELLOW}  🗑️  Removing all pi-monitor images...${NC}"
    docker rmi -f $images || echo "Some images couldn't be removed"
fi

# Remove all pi-monitor volumes
volumes=$(docker volume ls --filter "name=$PROJECT_NAME" -q 2>/dev/null || true)
if [[ -n "$volumes" ]]; then
    echo -e "${YELLOW}  🗑️  Removing all pi-monitor volumes...${NC}"
    docker volume rm $volumes || echo "Some volumes couldn't be removed"
fi

# Remove specific volumes from docker-compose
echo -e "${YELLOW}  🗑️  Removing compose volumes...${NC}"
docker-compose down -v --remove-orphans || true

# Clean up Docker system
echo -e "${YELLOW}  🧽 Cleaning Docker system...${NC}"
docker system prune -f --volumes || true

echo -e "${GREEN}✅ Docker cleanup completed${NC}"

# Step 6: Build and deploy
echo ""
echo -e "${BLUE}🏗️  Building and deploying latest version...${NC}"

# Pull latest images
echo -e "${YELLOW}  📥 Pulling latest base images...${NC}"
docker-compose pull || echo "Pull completed with warnings"

# Build the application
echo -e "${YELLOW}  🔨 Building application images...${NC}"
docker-compose build --no-cache --pull

# Step 7: Create Python virtual environment for host tools (optional)
echo ""
echo -e "${BLUE}🐍 Setting up Python virtual environment for host tools...${NC}"
if command -v python3 &>/dev/null; then
    if [[ ! -d "venv" ]]; then
        echo -e "${YELLOW}  📦 Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    if [[ -f "backend/requirements.txt" ]]; then
        echo -e "${YELLOW}  📥 Installing Python packages in venv...${NC}"
        venv/bin/pip install --upgrade pip --quiet
        venv/bin/pip install -r backend/requirements.txt --quiet
        echo -e "${GREEN}    ✅ Python packages installed in venv${NC}"
    fi
else
    echo -e "${YELLOW}    ⚠️  Python3 not found - skipping host venv setup${NC}"
fi

# Step 8: Start services
echo ""
echo -e "${BLUE}🚀 Starting services...${NC}"
docker-compose up -d

# Step 9: Wait and perform health checks
echo ""
echo -e "${BLUE}🏥 Performing health checks...${NC}"
sleep 10

# Check if containers are running
echo -e "${YELLOW}  📊 Checking container status...${NC}"
docker-compose ps

# Detailed health checks
echo ""
echo -e "${YELLOW}  🩺 Running detailed health checks...${NC}"

# Check Redis
if docker-compose exec -T redis redis-cli ping &>/dev/null; then
    echo -e "${GREEN}    ✅ Redis is healthy${NC}"
else
    echo -e "${RED}    ❌ Redis health check failed${NC}"
fi

# Check Mosquitto (basic connection test)
if docker-compose exec -T mosquitto mosquitto_pub -h localhost -t test -m "health_check" &>/dev/null; then
    echo -e "${GREEN}    ✅ Mosquitto is healthy${NC}"
else
    echo -e "${YELLOW}    ⚠️  Mosquitto health check inconclusive${NC}"
fi

# Check Backend
echo -e "${YELLOW}    🔍 Testing backend...${NC}"
sleep 5
if curl -f -s http://localhost:5000/health &>/dev/null; then
    echo -e "${GREEN}    ✅ Backend is healthy and responding${NC}"
else
    echo -e "${YELLOW}    ⚠️  Backend health check failed - checking logs...${NC}"
    docker-compose logs backend --tail=10
fi

# Check Frontend
echo -e "${YELLOW}    🔍 Testing frontend...${NC}"
if curl -f -s http://localhost:80/ &>/dev/null; then
    echo -e "${GREEN}    ✅ Frontend is healthy and responding${NC}"
else
    echo -e "${YELLOW}    ⚠️  Frontend health check failed - checking logs...${NC}"
    docker-compose logs frontend --tail=10
fi

# Step 10: Final verification
echo ""
echo -e "${BLUE}📋 Final verification...${NC}"

# Show container status
echo ""
echo -e "${CYAN}📊 Container Status:${NC}"
docker-compose ps

# Show port usage
echo ""
echo -e "${CYAN}🔌 Port Status:${NC}"
for port in "${CONFLICTING_PORTS[@]}"; do
    if check_port "$port"; then
        echo -e "${GREEN}  ✅ Port $port: In use (by pi-monitor)${NC}"
    else
        echo -e "${RED}  ❌ Port $port: Not in use${NC}"
    fi
done

# Show logs summary
echo ""
echo -e "${CYAN}📝 Recent Logs Summary:${NC}"
docker-compose logs --tail=3

echo ""
echo -e "${GREEN}🎉 Pi Monitor Force Deployment Complete!${NC}"
echo ""
echo -e "${CYAN}📊 Deployment Information:${NC}"
echo "  Frontend URL:    http://localhost:80"
echo "  Backend API:     http://localhost:5000"
echo "  Backend Health:  http://localhost:5000/health"
echo "  Redis Port:      6379"
echo "  MQTT Port:       1883"
echo "  MQTT WebSocket:  9001"
echo ""
echo -e "${CYAN}🛠️  Useful Commands:${NC}"
echo "  View logs:       docker-compose logs -f"
echo "  View status:     docker-compose ps"
echo "  Stop all:        docker-compose down"
echo "  Restart:         docker-compose restart"
echo "  Force redeploy:  ./force_deploy.sh --yes"
echo ""
echo -e "${CYAN}🔧 Service-specific Commands:${NC}"
echo "  Backend logs:    docker-compose logs backend -f"
echo "  Frontend logs:   docker-compose logs frontend -f"
echo "  Redis logs:      docker-compose logs redis -f"
echo "  MQTT logs:       docker-compose logs mosquitto -f"
echo ""
echo -e "${CYAN}📱 Testing:${NC}"
echo "  Test backend:    curl http://localhost:5000/health"
echo "  Test frontend:   curl http://localhost:80"
echo "  Test Redis:      docker-compose exec redis redis-cli ping"
echo "  Test MQTT:       docker-compose exec mosquitto mosquitto_pub -h localhost -t test -m hello"
echo ""
echo -e "${CYAN}🐍 Python Virtual Environment (for host commands):${NC}"
if [[ -d "venv" ]]; then
    echo "  Virtual env:     source venv/bin/activate"
    echo "  Run agent:       venv/bin/python backend/agent.py"
    echo "  Install package: venv/bin/pip install <package>"
    echo "  Deactivate:      deactivate"
else
    echo "  Not created - run deployment again to set up venv"
fi
echo ""

# Final status check
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✨ Deployment successful! All services are running.${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some services may not be running properly. Check logs above.${NC}"
    exit 1
fi
