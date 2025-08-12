#!/usr/bin/env bash

# Pi Monitor Domain Deployment (No Docker)
# Sets up nginx with SSL for pi.cabhinav.com and uses systemd backend

set -euo pipefail

echo "🚀 Starting Pi Monitor Domain Deployment (No Docker)..."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -eq 0 ]]; then
  print_error "Run without sudo; the script will use sudo when needed."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_status "Running base setup (venv + systemd + nginx)"
sudo bash "$SCRIPT_DIR/scripts/setup_venv_systemd.sh" "$SCRIPT_DIR"

print_status "Ensuring certbot and nginx are installed"
if ! command -v certbot >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y certbot python3-certbot-nginx
fi

DOMAIN="pi.cabhinav.com"

print_status "Obtaining/Configuring SSL via certbot for $DOMAIN"
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@cabhinav.com || print_warning "Certbot run failed; check DNS and ports 80/443"

print_status "Verifying services"
sleep 3
curl -fsS http://127.0.0.1:5001/health >/dev/null && print_success "Backend healthy" || print_warning "Backend health check failed"
curl -fsS https://$DOMAIN/ >/dev/null && print_success "Frontend reachable via HTTPS" || print_warning "Frontend HTTPS check failed"

print_success "Domain deployment complete"
