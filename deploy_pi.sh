#!/usr/bin/env bash
# Pi Monitor - Pi Deployment (No Docker, backend only)

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Pi Backend Deployment (No Docker)${NC}"
echo "===================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sudo bash "$SCRIPT_DIR/scripts/setup_venv_systemd.sh" "$SCRIPT_DIR"

echo -e "${BLUE}🧪 Checking backend health...${NC}"
sleep 3
if curl -fsS http://127.0.0.1:5001/health >/dev/null; then
  echo -e "${GREEN}✅ Backend healthy on :5001${NC}"
else
  echo -e "${YELLOW}⚠️  Backend health check failed${NC}"
fi

echo -e "${GREEN}🎉 Backend deployment complete (systemd + venv)${NC}"
