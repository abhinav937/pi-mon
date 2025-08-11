#!/bin/bash
# Pi Monitor - Quick Conflict Fix Script
# Fixes the specific issues found by debug_ports.sh

set +e  # Don't exit on errors during cleanup

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔧 Pi Monitor - Quick Conflict Fix${NC}"
echo "==================================="
echo ""

echo -e "${YELLOW}🛑 Stopping system mosquitto service...${NC}"
if systemctl is-active --quiet mosquitto 2>/dev/null; then
    echo "  Stopping mosquitto service..."
    sudo systemctl stop mosquitto
    echo "  Disabling mosquitto auto-start..."
    sudo systemctl disable mosquitto
    sleep 2
    
    # Double-check it's stopped
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        echo "  🚨 Mosquitto still active - force killing..."
        sudo systemctl kill mosquitto
        sleep 2
    fi
else
    echo "  ✅ Mosquitto service already stopped"
fi

echo ""
echo -e "${YELLOW}🐳 Stopping existing pi-monitor containers...${NC}"

# Stop and remove existing pi-monitor containers
echo "  Stopping existing containers..."
docker-compose down --remove-orphans -v 2>/dev/null || true

# Force remove specific containers
for container in pi-monitor-redis pi-monitor-mosquitto pi-monitor-backend pi-monitor-frontend; do
    if docker ps -aq --filter "name=^${container}$" | grep -q .; then
        echo "  Force removing $container..."
        docker stop "$container" 2>/dev/null || true
        docker rm -f "$container" 2>/dev/null || true
    fi
done

echo ""
echo -e "${YELLOW}💀 Killing remaining conflicting processes...${NC}"

# Kill mosquitto processes
echo "  Killing mosquitto processes..."
sudo pkill -9 -f mosquitto 2>/dev/null || true
sudo killall mosquitto 2>/dev/null || true

# Kill redis processes (but not docker ones we want)
echo "  Killing system redis processes..."
sudo pkill -9 -f "redis-server" 2>/dev/null || true

# Kill any web servers on our ports
echo "  Killing web server processes..."
sudo pkill -9 -f "uvicorn.*5001\|gunicorn.*5001" 2>/dev/null || true

echo ""
echo -e "${YELLOW}🔌 Force freeing ports...${NC}"

# Force free the ports
for port in 1883 6379 5001 80; do
    echo "  Force freeing port $port..."
    sudo fuser -k ${port}/tcp 2>/dev/null || true
    sudo lsof -ti:$port | xargs -r sudo kill -9 2>/dev/null || true
    sleep 1
done

echo ""
echo -e "${BLUE}⏳ Waiting for cleanup to complete...${NC}"
sleep 5

echo ""
echo -e "${BLUE}🔍 Verifying fix...${NC}"

# Check if ports are now free
all_free=true
for port in 1883 6379 5001 80; do
    if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        echo -e "${RED}  ❌ Port $port still in use${NC}"
        all_free=false
    else
        echo -e "${GREEN}  ✅ Port $port is now free${NC}"
    fi
done

echo ""
if [[ "$all_free" == true ]]; then
    echo -e "${GREEN}🎉 SUCCESS! All conflicts resolved!${NC}"
    echo ""
    echo -e "${CYAN}🚀 Now run the deployment:${NC}"
    echo "  ./force_deploy.sh --yes --verbose"
else
    echo -e "${RED}⚠️  Some conflicts remain. Run debug_ports.sh again to see what's left.${NC}"
    echo ""
    echo -e "${CYAN}💣 Nuclear option:${NC}"
    echo "  ./force_deploy.sh --nuclear --yes"
fi

echo ""
echo -e "${BLUE}🔧 Fix completed!${NC}"
