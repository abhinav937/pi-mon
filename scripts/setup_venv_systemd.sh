#!/usr/bin/bash

# Pi Monitor: setup without Docker (venv + systemd + nginx)
# Usage: sudo ./scripts/setup_venv_systemd.sh [APP_DIR]
# Default APP_DIR is current working directory

set -euo pipefail

# Quiet mode controlled by environment (set by deploy.sh)
QUIET="${PMON_QUIET:-0}"

# Fix: If we're in a scripts subdirectory, go up to the parent
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" == "scripts" ]]; then
    APP_DIR="${1:-$(dirname "$SCRIPT_DIR")}"
else
    APP_DIR="${1:-$(pwd)}"
fi

BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$APP_DIR/.venv"
APP_USER="${SUDO_USER:-$(id -un)}"
APP_GROUP="${SUDO_GID:-$(id -gn "$APP_USER")}"
ENV_FILE="$BACKEND_DIR/.env"
WWW_ROOT="/var/www/pi-monitor"
SYSTEMD_SERVICE="/etc/systemd/system/pi-monitor-backend.service"
NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/pi-monitor"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/pi-monitor"

if [[ "$QUIET" != "1" ]]; then
echo "==> Config"
echo "SCRIPT_DIR=$SCRIPT_DIR"
echo "APP_DIR=$APP_DIR"
echo "APP_USER=$APP_USER"
echo "VENV_DIR=$VENV_DIR"
echo "BACKEND_DIR=$BACKEND_DIR"
echo "FRONTEND_DIR=$FRONTEND_DIR"
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "This script must be run as root (use sudo)." >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 not found" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm not found (install Node 18+)" >&2; exit 1; }

if [[ "$QUIET" != "1" ]]; then echo "==> Installing system packages (nginx, rsync)"; fi
if [[ "$QUIET" = "1" ]]; then
  apt-get update -y -qq >/dev/null 2>&1
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx rsync >/dev/null 2>&1
else
  apt-get update -y -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nginx rsync
fi

if [[ "$QUIET" != "1" ]]; then echo "==> Creating Python venv and installing backend requirements"; fi
sudo -u "$APP_USER" mkdir -p "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
if [[ "$QUIET" = "1" ]]; then
  "$VENV_DIR/bin/pip" install -q --upgrade pip >/dev/null 2>&1
else
  "$VENV_DIR/bin/pip" install --upgrade pip
fi
if [[ "$QUIET" = "1" ]]; then
  "$VENV_DIR/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt" >/dev/null 2>&1
else
  "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
fi
if [[ "$QUIET" != "1" ]]; then echo "==> Backend dependencies installed"; fi

if [[ "$QUIET" != "1" ]]; then echo "==> Writing backend environment file ($ENV_FILE) if missing"; fi
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<EOF
# Environment for Pi Monitor backend
PI_MONITOR_API_KEY=pi-monitor-api-key-2024
EOF
  chown "$APP_USER":"$APP_GROUP" "$ENV_FILE"
fi
if [[ "$QUIET" != "1" ]]; then echo "==> Backend environment ready ($ENV_FILE)"; fi

if [[ "$QUIET" != "1" ]]; then echo "==> Building frontend"; fi
# Ensure correct ownership before installing dependencies
chown -R "$APP_USER":"$APP_GROUP" "$FRONTEND_DIR"
pushd "$FRONTEND_DIR" >/dev/null
if [[ "$QUIET" = "1" ]]; then
  sudo -u "$APP_USER" npm install --no-audit --no-fund --no-optional --silent --loglevel=error --no-progress >/dev/null 2>&1
  DISABLE_ESLINT_PLUGIN=true BROWSERSLIST_IGNORE_OLD_DATA=1 CI=true sudo -u "$APP_USER" npm run -s build >/dev/null 2>&1
else
  sudo -u "$APP_USER" npm install --no-audit --no-fund --no-optional --silent --loglevel=error --no-progress
  DISABLE_ESLINT_PLUGIN=true BROWSERSLIST_IGNORE_OLD_DATA=1 sudo -u "$APP_USER" npm run -s build
fi
popd >/dev/null

if [[ "$QUIET" != "1" ]]; then echo "==> Deploying frontend to $WWW_ROOT"; fi
mkdir -p "$WWW_ROOT"
rsync -a --delete "$FRONTEND_DIR/build/" "$WWW_ROOT/"
chown -R www-data:www-data "$WWW_ROOT"

if [[ "$QUIET" != "1" ]]; then echo "==> Installing nginx site"; fi
if [[ -f "$APP_DIR/nginx/pi-monitor.conf" ]]; then
  cp "$APP_DIR/nginx/pi-monitor.conf" "$NGINX_SITE_AVAILABLE"
else
  # Fallback minimal config
  cat > "$NGINX_SITE_AVAILABLE" <<'NGINX'
server {
  listen 80;
  server_name _;

  root /var/www/pi-monitor;
  index index.html;

  location / {
    try_files $uri /index.html;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:5001/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}
NGINX
fi
ln -sf "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"
if [[ -f /etc/nginx/sites-enabled/default ]]; then rm -f /etc/nginx/sites-enabled/default; fi

# If port 80 is already in use, try to stop common web servers
if ss -ltnp 2>/dev/null | grep -q ":80 "; then
  if [[ "$QUIET" != "1" ]]; then echo "==> Port 80 is in use. Attempting to stop conflicting services (apache2, httpd, lighttpd, nginx)"; fi
  if [[ "$QUIET" = "1" ]]; then true; fi
  systemctl stop apache2 2>/dev/null || true
  systemctl disable apache2 2>/dev/null || true
  systemctl stop httpd 2>/dev/null || true
  systemctl disable httpd 2>/dev/null || true
  systemctl stop lighttpd 2>/dev/null || true
  systemctl disable lighttpd 2>/dev/null || true
  systemctl stop nginx 2>/dev/null || true
  # Re-check after stopping
  if ss -ltnp 2>/dev/null | grep -q ":80 "; then
    if [[ "$QUIET" != "1" ]]; then echo "WARNING: Port 80 still occupied. Please run 'sudo ss -lntp | grep :80' to identify the process, stop/disable it, then run 'sudo systemctl restart nginx'."; fi
  fi
fi

if [[ "$QUIET" = "1" ]]; then nginx -t >/dev/null 2>&1 || true; else nginx -t; fi
set +e
systemctl enable nginx >/dev/null 2>&1
systemctl restart nginx >/dev/null 2>&1
set -e

if [[ "$QUIET" != "1" ]]; then echo "==> Installing systemd service for backend ($SYSTEMD_SERVICE)"; fi
cat > "$SYSTEMD_SERVICE" <<EOF
[Unit]
Description=Pi Monitor Backend (venv)
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$BACKEND_DIR
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/python start_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload >/dev/null 2>&1
systemctl enable --now pi-monitor-backend.service >/dev/null 2>&1
systemctl status pi-monitor-backend.service | cat >/dev/null 2>&1 || true

if [[ "$QUIET" != "1" ]]; then echo "==> Backend service installed and started (pi-monitor-backend.service)"; fi
if [[ "$QUIET" != "1" ]]; then echo "==> Backend setup complete"; fi

if [[ "$QUIET" != "1" ]]; then echo "==> Configuring passwordless sudo for pi-monitor commands"; fi
SUDOERS_FILE="/etc/sudoers.d/pi-monitor"
if [[ ! -f "$SUDOERS_FILE" ]]; then
  cat > "$SUDOERS_FILE" <<EOF
$APP_USER ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown, /bin/systemctl, /usr/bin/systemctl, /usr/bin/tail
EOF
  chmod 0440 "$SUDOERS_FILE"
  if visudo -c -f "$SUDOERS_FILE" >/dev/null 2>&1; then
    if [[ "$QUIET" != "1" ]]; then echo "Sudoers configuration validated and installed."; fi
  else
    if [[ "$QUIET" != "1" ]]; then echo "WARNING: Sudoers validation failed. Please check $SUDOERS_FILE manually."; fi
    rm -f "$SUDOERS_FILE"
  fi
else
  if [[ "$QUIET" != "1" ]]; then echo "Sudoers file already exists, skipping."; fi
fi

if [[ "$QUIET" != "1" ]]; then echo "==> Done. Frontend on http://<host>/, backend on http://127.0.0.1:5001 (proxied at /api)"; fi


