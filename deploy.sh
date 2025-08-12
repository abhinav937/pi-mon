#!/usr/bin/env bash
# Pi Monitor - Deployment (venv + systemd + nginx)

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Deployment (No Docker)${NC}"
echo "========================================="

if [[ ! -f "config.json" ]]; then
  echo -e "${YELLOW}⚠️  config.json not found; proceeding with defaults${NC}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}🔧 Running setup script with sudo...${NC}"
sudo bash "$SCRIPT_DIR/scripts/setup_venv_systemd.sh" "$SCRIPT_DIR"

echo -e "${BLUE}🧪 Verifying services...${NC}"
sleep 3
set +e
curl -fsS http://127.0.0.1/ >/dev/null && echo -e "${GREEN}✅ Frontend reachable at http://<host>/${NC}" || echo -e "${YELLOW}⚠️  Frontend test failed (nginx may be starting)${NC}"
curl -fsS http://127.0.0.1:5001/health >/dev/null && echo -e "${GREEN}✅ Backend healthy on :5001${NC}" || echo -e "${RED}❌ Backend health check failed${NC}"
set -e

echo -e "${GREEN}🎉 Deployment complete (venv + systemd + nginx)${NC}"
echo -e "${BLUE}🌐 Access:${NC} http://<host>/"
