#!/usr/bin/env bash

# Pi Monitor: setup without Docker (venv + systemd + nginx)
# Usage: sudo ./scripts/setup_venv_systemd.sh [APP_DIR]
# Default APP_DIR is current working directory

set -euo pipefail

APP_DIR="${1:-$(pwd)}"
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

echo "==> Config"
echo "APP_DIR=$APP_DIR"
echo "APP_USER=$APP_USER"
echo "VENV_DIR=$VENV_DIR"

if [[ "$EUID" -ne 0 ]]; then
  echo "This script must be run as root (use sudo)." >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 not found" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "npm not found (install Node 18+)" >&2; exit 1; }

echo "==> Installing system packages (nginx, rsync)"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y nginx rsync

echo "==> Creating Python venv and installing backend requirements"
sudo -u "$APP_USER" mkdir -p "$APP_DIR"
sudo -u "$APP_USER" python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"

echo "==> Writing backend environment file ($ENV_FILE) if missing"
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<EOF
# Environment for Pi Monitor backend
PI_MONITOR_API_KEY=pi-monitor-api-key-2024
EOF
  chown "$APP_USER":"$APP_GROUP" "$ENV_FILE"
fi

echo "==> Building frontend"
pushd "$FRONTEND_DIR" >/dev/null
sudo -u "$APP_USER" npm ci --no-audit --no-fund || {
  echo "npm ci failed (lockfile out of sync). Falling back to 'npm install'..."
  sudo -u "$APP_USER" npm install --no-audit --no-fund
}
sudo -u "$APP_USER" npm run build
popd >/dev/null

echo "==> Deploying frontend to $WWW_ROOT"
mkdir -p "$WWW_ROOT"
rsync -a --delete "$FRONTEND_DIR/build/" "$WWW_ROOT/"
chown -R www-data:www-data "$WWW_ROOT"

echo "==> Installing nginx site"
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
  echo "==> Port 80 is in use. Attempting to stop conflicting services (apache2, httpd, lighttpd, nginx)"
  systemctl stop apache2 2>/dev/null || true
  systemctl disable apache2 2>/dev/null || true
  systemctl stop httpd 2>/dev/null || true
  systemctl disable httpd 2>/dev/null || true
  systemctl stop lighttpd 2>/dev/null || true
  systemctl disable lighttpd 2>/dev/null || true
  systemctl stop nginx 2>/dev/null || true
  # Re-check after stopping
  if ss -ltnp 2>/dev/null | grep -q ":80 "; then
    echo "WARNING: Port 80 still occupied. Please run 'sudo ss -lntp | grep :80' to identify the process, stop/disable it, then run 'sudo systemctl restart nginx'."
  fi
fi

nginx -t
set +e
systemctl enable nginx
systemctl restart nginx
set -e

echo "==> Installing systemd service for backend ($SYSTEMD_SERVICE)"
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
ExecStart=$VENV_DIR/bin/python simple_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now pi-monitor-backend.service
systemctl status pi-monitor-backend.service | cat || true

echo "==> Configuring passwordless sudo for pi-monitor commands"
SUDOERS_FILE="/etc/sudoers.d/pi-monitor"
if [[ ! -f "$SUDOERS_FILE" ]]; then
  cat > "$SUDOERS_FILE" <<EOF
$APP_USER ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown, /bin/systemctl, /usr/bin/tail
EOF
  chmod 0440 "$SUDOERS_FILE"
  if visudo -c -f "$SUDOERS_FILE"; then
    echo "Sudoers configuration validated and installed."
  else
    echo "WARNING: Sudoers validation failed. Please check $SUDOERS_FILE manually."
    rm -f "$SUDOERS_FILE"
  fi
else
  echo "Sudoers file already exists, skipping."
fi

echo "==> Done. Frontend on http://<host>/, backend on http://127.0.0.1:5001 (proxied at /api)"


