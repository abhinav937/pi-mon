#!/bin/bash
# Pi Monitor - Mosquitto Auto-Restart Fix
# Fixes the mosquitto service that keeps restarting and blocking port 1883

set +e  # Don't exit on errors

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔧 Pi Monitor - Mosquitto Auto-Restart Fix${NC}"
echo "==========================================="
echo ""

echo -e "${YELLOW}🎯 Problem: System mosquitto keeps auto-restarting and blocking port 1883${NC}"
echo -e "${CYAN}🔧 Solution: MASK the service to prevent systemd from restarting it${NC}"
echo ""

# Step 1: MASK the mosquitto service (this prevents any restart)
echo -e "${RED}🚫 MASKING mosquitto service (prevents auto-restart)...${NC}"
sudo systemctl mask mosquitto
echo "  ✅ Mosquitto service masked"

# Step 2: Stop the service
echo -e "${YELLOW}🛑 Stopping mosquitto service...${NC}"
sudo systemctl stop mosquitto
echo "  ✅ Stop command sent"

# Step 3: Kill the service process if still running  
echo -e "${YELLOW}💀 Killing mosquitto service process...${NC}"
sudo systemctl kill mosquitto 2>/dev/null || true
sleep 2

# Step 4: Hunt down any remaining mosquitto processes
echo -e "${RED}🔫 Hunting remaining mosquitto processes...${NC}"
for attempt in {1..3}; do
    mosquitto_pids=$(pgrep mosquitto 2>/dev/null || true)
    if [[ -n "$mosquitto_pids" ]]; then
        echo "  🎯 Attempt $attempt: Found PIDs: $mosquitto_pids"
        echo "$mosquitto_pids" | xargs -r sudo kill -9 2>/dev/null || true
        sudo pkill -9 -f mosquitto 2>/dev/null || true
        sleep 3
    else
        echo "  ✅ No mosquitto processes found (attempt $attempt)"
        break
    fi
done

# Step 5: Final port liberation
echo -e "${YELLOW}🔓 Liberating port 1883...${NC}"
sudo fuser -k 1883/tcp 2>/dev/null || true
sudo lsof -ti:1883 | xargs -r sudo kill -9 2>/dev/null || true
sleep 2

# Step 6: Verification
echo ""
echo -e "${BLUE}🔍 Verification...${NC}"

# Check service status
echo -e "${CYAN}Service status:${NC}"
if systemctl is-active --quiet mosquitto 2>/dev/null; then
    echo -e "${RED}  ❌ Mosquitto service is STILL active${NC}"
    systemctl status mosquitto --no-pager 2>/dev/null || true
else
    echo -e "${GREEN}  ✅ Mosquitto service is stopped${NC}"
fi

if systemctl is-masked --quiet mosquitto 2>/dev/null; then
    echo -e "${GREEN}  ✅ Mosquitto service is masked (auto-restart disabled)${NC}"
else
    echo -e "${RED}  ❌ Mosquitto service is NOT masked${NC}"
fi

# Check port 1883
echo -e "${CYAN}Port 1883 status:${NC}"
if netstat -tuln 2>/dev/null | grep -q ":1883 " || ss -tuln 2>/dev/null | grep -q ":1883 "; then
    echo -e "${RED}  ❌ Port 1883 is STILL in use:${NC}"
    sudo lsof -i:1883 2>/dev/null | head -5 || echo "    (No lsof results)"
else
    echo -e "${GREEN}  ✅ Port 1883 is FREE!${NC}"
fi

# Check for any mosquitto processes
echo -e "${CYAN}Process status:${NC}"
mosquitto_procs=$(pgrep -l mosquitto 2>/dev/null || true)
if [[ -n "$mosquitto_procs" ]]; then
    echo -e "${RED}  ❌ Mosquitto processes still running:${NC}"
    echo "$mosquitto_procs" | sed 's/^/    /'
else
    echo -e "${GREEN}  ✅ No mosquitto processes running${NC}"
fi

echo ""
echo -e "${BLUE}🎯 SUMMARY:${NC}"

# Final check
if ! (netstat -tuln 2>/dev/null | grep -q ":1883 " || ss -tuln 2>/dev/null | grep -q ":1883 "); then
    echo -e "${GREEN}🎉 SUCCESS! Port 1883 is now free for deployment!${NC}"
    echo ""
    echo -e "${CYAN}🚀 Now run your deployment:${NC}"
    echo "  ./force_deploy.sh --yes --verbose"
    echo ""
    echo -e "${YELLOW}📋 What was done:${NC}"
    echo "  • Mosquitto service MASKED (prevents auto-restart)"
    echo "  • All mosquitto processes killed"
    echo "  • Port 1883 freed"
    echo ""
    echo -e "${CYAN}📝 To re-enable mosquitto later (after testing):${NC}"
    echo "  sudo systemctl unmask mosquitto"
    echo "  sudo systemctl enable mosquitto"
    echo "  sudo systemctl start mosquitto"
else
    echo -e "${RED}❌ FAILED! Port 1883 is still in use.${NC}"
    echo -e "${CYAN}🔍 Debug info:${NC}"
    sudo lsof -i:1883 2>/dev/null || echo "  No lsof results"
    echo ""
    echo -e "${YELLOW}💣 Try nuclear option:${NC}"
    echo "  ./force_deploy.sh --nuclear --yes"
fi

echo ""
echo -e "${BLUE}🔧 Fix completed!${NC}"
