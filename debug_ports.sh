#!/bin/bash
# Pi Monitor - Port Debugging Script
# Use this to debug what's blocking deployment ports

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔍 Pi Monitor - Port Debugging Script${NC}"
echo "========================================"
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

# Critical ports for Pi Monitor
CRITICAL_PORTS=(1883 6379 5001 80)

echo -e "${YELLOW}📊 Checking critical ports for Pi Monitor...${NC}"
echo ""

for port in "${CRITICAL_PORTS[@]}"; do
    echo -e "${CYAN}🔍 Port $port analysis:${NC}"
    
    if check_port "$port"; then
        echo -e "${RED}  ❌ Port $port is IN USE${NC}"
        
        echo "  📋 netstat details:"
        netstat -tulpn 2>/dev/null | grep ":$port " | head -3 || echo "    No netstat results"
        
        echo "  📋 lsof details:"
        sudo lsof -i:$port 2>/dev/null | head -5 || echo "    No lsof results"
        
        echo "  📋 Process details:"
        pids=$(sudo lsof -ti:$port 2>/dev/null | head -5)
        if [[ -n "$pids" ]]; then
            for pid in $pids; do
                echo "    PID $pid: $(ps -p $pid -o comm= 2>/dev/null || echo 'Unknown')"
            done
        else
            echo "    No PIDs found"
        fi
        
        echo "  🔧 To fix:"
        case $port in
            1883)
                echo "    sudo systemctl stop mosquitto"
                echo "    sudo systemctl disable mosquitto"
                echo "    sudo pkill -9 -f mosquitto"
                echo "    sudo fuser -k 1883/tcp"
                ;;
            6379)
                echo "    sudo systemctl stop redis-server"
                echo "    sudo pkill -9 -f redis"
                echo "    sudo fuser -k 6379/tcp"
                ;;
            5001)
                echo "    sudo pkill -9 -f 'uvicorn|gunicorn|main_server'"
                echo "    sudo fuser -k 5001/tcp"
                ;;
            80)
                echo "    sudo systemctl stop nginx apache2"
                echo "    sudo fuser -k 80/tcp"
                ;;
        esac
    else
        echo -e "${GREEN}  ✅ Port $port is FREE${NC}"
    fi
    echo ""
done

echo -e "${CYAN}🔧 System Services Status:${NC}"
for service in mosquitto redis-server nginx apache2; do
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        echo -e "${RED}  ❌ $service is RUNNING${NC}"
        echo "    Fix: sudo systemctl stop $service && sudo systemctl disable $service"
    else
        echo -e "${GREEN}  ✅ $service is stopped${NC}"
    fi
done

echo ""
echo -e "${CYAN}🐳 Docker Status:${NC}"
if command -v docker &>/dev/null && docker info &>/dev/null; then
    echo -e "${GREEN}  ✅ Docker is running${NC}"
    
    # Check for existing pi-monitor containers
    existing_containers=$(docker ps -aq --filter "name=pi-monitor" 2>/dev/null || true)
    if [[ -n "$existing_containers" ]]; then
        echo -e "${YELLOW}  ⚠️  Existing pi-monitor containers found:${NC}"
        docker ps -a --filter "name=pi-monitor" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
    else
        echo -e "${GREEN}  ✅ No existing pi-monitor containers${NC}"
    fi
else
    echo -e "${RED}  ❌ Docker is not running or not installed${NC}"
fi

echo ""
echo -e "${BLUE}🎯 SUMMARY & RECOMMENDATIONS:${NC}"

# Check overall readiness
all_ports_free=true
for port in "${CRITICAL_PORTS[@]}"; do
    if check_port "$port"; then
        all_ports_free=false
        break
    fi
done

if [[ "$all_ports_free" == true ]]; then
    echo -e "${GREEN}✨ ALL PORTS ARE FREE! Ready for deployment.${NC}"
    echo ""
    echo -e "${CYAN}🚀 Run deployment:${NC}"
    echo "  ./force_deploy.sh --yes --verbose"
else
    echo -e "${RED}⚠️  PORTS ARE BLOCKED! Deployment will fail.${NC}"
    echo ""
    echo -e "${CYAN}🔧 Quick fix commands:${NC}"
    echo "  # Stop all conflicting services:"
    echo "  sudo systemctl stop mosquitto redis-server nginx apache2"
    echo "  sudo systemctl disable mosquitto redis-server"
    echo ""
    echo "  # Kill all processes:"
    echo "  sudo pkill -9 -f mosquitto"
    echo "  sudo pkill -9 -f redis"
    echo "  sudo fuser -k 1883/tcp"
    echo "  sudo fuser -k 6379/tcp"
    echo "  sudo fuser -k 5001/tcp"
    echo ""
    echo -e "${CYAN}🚀 Then run deployment:${NC}"
    echo "  ./force_deploy.sh --yes --verbose"
    echo ""
    echo -e "${YELLOW}⚡ Or use nuclear option:${NC}"
    echo "  ./force_deploy.sh --nuclear --yes"
fi

echo ""
echo -e "${BLUE}📝 Debug completed!${NC}"
