#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Pi Monitor Deployment (leveled logging, flags, subdomain-aware Nginx)
# ============================================================================

# Defaults (overridable via flags)
DOMAIN="_"
STATIC_IP=""
WEB_ROOT="/var/www/pi-monitor"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
PRODUCTION_URL="http://localhost"
PI_MON_DIR=""
VENV_DIR=""
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"
STATE_DIR=""
PUBLIC_PORT="80"
NGINX_PORT="80"
BACKEND_PORT="5001"
SYSTEM_USER=""

# Behavior flags
LOG_LEVEL="info"   # debug|info|warn|error
NO_COLOR=false
DRY_RUN=false
ONLY_TARGET=""     # frontend|backend|nginx|verify
SKIP_FRONTEND=false
SKIP_BACKEND=false
SKIP_NGINX=false
FORCE_FRONTEND=false
FORCE_BACKEND=false
USE_SETUP_SCRIPT=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Derive sane defaults based on runtime
[ -n "$PI_MON_DIR" ] || PI_MON_DIR="$SCRIPT_DIR"
[ -n "$SYSTEM_USER" ] || SYSTEM_USER="${SUDO_USER:-$(id -un)}"
[ -n "$PRODUCTION_URL" ] || PRODUCTION_URL="http://localhost"

# ----------------------------------------------------------------------------
# Color and logging
# ----------------------------------------------------------------------------
if [ -t 1 ] && [ "${NO_COLOR}" = false ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

_level_value() {
    case "$1" in
        debug) echo 10 ;;
        info)  echo 20 ;;
        warn)  echo 30 ;;
        error) echo 40 ;;
        *)     echo 20 ;;
    esac
}

LOG_LEVEL_NUM=$(_level_value "$LOG_LEVEL")

log() {
    local level="$1"; shift
    local level_num=$(_level_value "$level")
    [ "$level_num" -lt "$LOG_LEVEL_NUM" ] && return 0
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    local color=""; local tag=""
    case "$level" in
        debug) color="$BLUE"; tag="DEBUG" ;;
        info)  color="$GREEN"; tag="INFO" ;;
        warn)  color="$YELLOW"; tag="WARN" ;;
        error) color="$RED"; tag="ERROR" ;;
        *)     color=""; tag="INFO" ;;
    esac
    printf "%b[%s] %-5s%b %s\n" "$color" "$ts" "$tag" "$NC" "$*"
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        log debug "DRY-RUN: $*"
    else
        log debug "EXEC: $*"
        eval "$@"
    fi
}

on_error() {
    local ec=$?; local ln=${BASH_LINENO[0]}
    log error "Failed at line $ln with exit code $ec"
}
trap on_error ERR

# ----------------------------------------------------------------------------
# CLI args
# ----------------------------------------------------------------------------
usage() {
    cat <<USAGE
Usage: sudo ./deploy.sh [flags]

Flags:
  --domain VALUE               Subdomain/host (default: ${DOMAIN})
  --static-ip VALUE            Public IP used in URLs (default: ${STATIC_IP})
  --web-root PATH              Nginx web root (default: ${WEB_ROOT})
  --pi-mon-dir PATH            Project root (default: ${PI_MON_DIR})
  --venv-dir PATH              Python venv dir (default: <pi-mon-dir>/.venv)
  --backend-port N             Backend port (default: ${BACKEND_PORT})
  --nginx-port N               Nginx listen port (default: ${NGINX_PORT})
  --user NAME                  System user (default: ${SYSTEM_USER})
  --log-level LEVEL            debug|info|warn|error (default: ${LOG_LEVEL})
  --debug                      Shortcut for --log-level debug
  --quiet                      Shortcut for --log-level warn
  --no-color                   Disable ANSI colors
  --dry-run                    Print actions without executing
  --only TARGET                frontend|backend|nginx|verify
  --skip-frontend              Skip frontend build/deploy
  --skip-backend               Skip backend service setup
  --skip-nginx                 Skip nginx setup
  --force-frontend             Force frontend rebuild
  --force-backend              Force backend restart
  --use-setup-script           Run scripts/setup_venv_systemd.sh as a bootstrap (optional)
  -h, --help                   Show this help
USAGE
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --domain) DOMAIN="$2"; shift 2 ;;
            --static-ip) STATIC_IP="$2"; PRODUCTION_URL="http://$2"; shift 2 ;;
            --web-root) WEB_ROOT="$2"; shift 2 ;;
            --pi-mon-dir) PI_MON_DIR="$2"; shift 2 ;;
            --venv-dir) VENV_DIR="$2"; shift 2 ;;
            --backend-port) BACKEND_PORT="$2"; shift 2 ;;
            --nginx-port) NGINX_PORT="$2"; shift 2 ;;
            --user) SYSTEM_USER="$2"; shift 2 ;;
            --log-level) LOG_LEVEL="$2"; shift 2 ;;
            --debug) LOG_LEVEL="debug"; shift 1 ;;
            --quiet) LOG_LEVEL="warn"; shift 1 ;;
            --no-color) NO_COLOR=true; shift 1 ;;
            --dry-run) DRY_RUN=true; shift 1 ;;
            --only) ONLY_TARGET="$2"; shift 2 ;;
            --skip-frontend) SKIP_FRONTEND=true; shift 1 ;;
            --skip-backend) SKIP_BACKEND=true; shift 1 ;;
            --skip-nginx) SKIP_NGINX=true; shift 1 ;;
            --force-frontend) FORCE_FRONTEND=true; shift 1 ;;
            --force-backend) FORCE_BACKEND=true; shift 1 ;;
            --use-setup-script) USE_SETUP_SCRIPT=true; shift 1 ;;
            -h|--help) usage; exit 0 ;;
            *) log error "Unknown flag: $1"; usage; exit 2 ;;
        esac
    done
    LOG_LEVEL_NUM=$(_level_value "$LOG_LEVEL")
}

parse_args "$@"

[ -n "$VENV_DIR" ] || VENV_DIR="$PI_MON_DIR/.venv"
[ -n "$STATE_DIR" ] || STATE_DIR="$PI_MON_DIR/.deploy_state"

# If STATIC_IP not provided, attempt to detect a primary IPv4 (best-effort)
if [ -z "$STATIC_IP" ]; then
    STATIC_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || true
fi
if [ -z "$STATIC_IP" ]; then
    STATIC_IP="127.0.0.1"
fi

if [[ "$EUID" -ne 0 ]]; then
    log error "This script must be run with sudo"
    exit 1
fi

# ----------------------------------------------------------------------------
# Discovery and state
# ----------------------------------------------------------------------------
log info "Checking current state"

mkdir -p "$STATE_DIR"
run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$STATE_DIR"

USER_EXISTS=false
if id "$SYSTEM_USER" &>/dev/null; then USER_EXISTS=true; else log error "User '$SYSTEM_USER' does not exist"; fi

PI_MON_EXISTS=false
[ -d "$PI_MON_DIR" ] && PI_MON_EXISTS=true

VENV_EXISTS=false
if [ -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    if "$VENV_DIR/bin/python" -c 'import sys; print(sys.version)' >/dev/null 2>&1; then
        VENV_EXISTS=true
    fi
fi

SERVICE_EXISTS=false
SERVICE_RUNNING=false
if [ -f "$SERVICE_FILE" ]; then
    SERVICE_EXISTS=true
    if systemctl is-active --quiet pi-monitor-backend.service; then SERVICE_RUNNING=true; fi
fi

NGINX_CONFIGURED=false
if [ -f "$NGINX_SITES_AVAILABLE/$DOMAIN" ] && [ -L "$NGINX_SITES_ENABLED/$DOMAIN" ]; then
    NGINX_CONFIGURED=true
fi

FRONTEND_BUILT=false
[ -f "$WEB_ROOT/index.html" ] && FRONTEND_BUILT=true

BACKEND_ACCESSIBLE=false
if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then BACKEND_ACCESSIBLE=true; fi

# Versions and checksums
FRONTEND_CHECKSUM_FILE="$STATE_DIR/frontend_checksum"
FRONTEND_ENV_SIG_FILE="$STATE_DIR/frontend_env_sig"
BACKEND_CHECKSUM_FILE="$STATE_DIR/backend_checksum"
BACKEND_VERSION_FILE="$STATE_DIR/backend_version"
NGINX_CHECKSUM_FILE="$STATE_DIR/nginx_checksum"

SOURCE_FRONTEND_VERSION=""; DEPLOYED_FRONTEND_VERSION=""; SOURCE_BACKEND_VERSION=""
if [ -f "$PI_MON_DIR/frontend/public/version.json" ]; then
    SOURCE_FRONTEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$PI_MON_DIR/frontend/public/version.json" | head -n1)
fi
if [ -z "$SOURCE_FRONTEND_VERSION" ] && [ -f "$PI_MON_DIR/frontend/package.json" ]; then
    SOURCE_FRONTEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$PI_MON_DIR/frontend/package.json" | head -n1)
fi
if [ -f "$WEB_ROOT/version.json" ]; then
    DEPLOYED_FRONTEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$WEB_ROOT/version.json" | head -n1)
fi
if [ -f "$PI_MON_DIR/config.json" ]; then
    SOURCE_BACKEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$PI_MON_DIR/config.json" | head -n1)
fi

CURRENT_FRONTEND_CHECKSUM=""
if [ -d "$PI_MON_DIR/frontend" ]; then
    CURRENT_FRONTEND_CHECKSUM=$(find "$PI_MON_DIR/frontend" \
        -path "$PI_MON_DIR/frontend/node_modules" -prune -o \
        -path "$PI_MON_DIR/frontend/build" -prune -o \
        -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.css" -o -name "*.json" -o -name "*.html" -o -name "*.config.js" -o -name "postcss.config.js" -o -name "tailwind.config.js" -o -name "package.json" \) -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
fi

CURRENT_FRONTEND_ENV_SIG=$(printf "%s|%s|%s" "$PRODUCTION_URL" "$BACKEND_PORT" "$NGINX_PORT" | sha256sum | awk '{print $1}')

CURRENT_BACKEND_CHECKSUM=""
if [ -d "$PI_MON_DIR/backend" ]; then
    CURRENT_BACKEND_CHECKSUM=$(find "$PI_MON_DIR/backend" -type f \( -name "*.py" -o -name "requirements.txt" -o -name "*.sh" \) -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
fi

NEED_FRONTEND_BUILD=false
if [ "$SKIP_FRONTEND" = false ]; then
    if [ "$FORCE_FRONTEND" = true ]; then
        NEED_FRONTEND_BUILD=true
    elif [ "$FRONTEND_BUILT" = false ]; then
        NEED_FRONTEND_BUILD=true
    elif [ -n "$SOURCE_FRONTEND_VERSION" ] && [ -n "$DEPLOYED_FRONTEND_VERSION" ] && [ "$SOURCE_FRONTEND_VERSION" != "$DEPLOYED_FRONTEND_VERSION" ]; then
        NEED_FRONTEND_BUILD=true
    elif [ -n "$CURRENT_FRONTEND_CHECKSUM" ] && [ -f "$FRONTEND_CHECKSUM_FILE" ] && [ "$(cat "$FRONTEND_CHECKSUM_FILE" 2>/dev/null || true)" != "$CURRENT_FRONTEND_CHECKSUM" ]; then
        NEED_FRONTEND_BUILD=true
    elif [ -n "$CURRENT_FRONTEND_ENV_SIG" ] && [ -f "$FRONTEND_ENV_SIG_FILE" ] && [ "$(cat "$FRONTEND_ENV_SIG_FILE" 2>/dev/null || true)" != "$CURRENT_FRONTEND_ENV_SIG" ]; then
        NEED_FRONTEND_BUILD=true
    elif [ ! -f "$FRONTEND_CHECKSUM_FILE" ] || [ ! -f "$FRONTEND_ENV_SIG_FILE" ]; then
        NEED_FRONTEND_BUILD=true
    fi
fi

NEED_BACKEND_RESTART=false
if [ "$SKIP_BACKEND" = false ]; then
    if [ "$FORCE_BACKEND" = true ]; then
        NEED_BACKEND_RESTART=true
    elif [ -n "$CURRENT_BACKEND_CHECKSUM" ] && [ -f "$BACKEND_CHECKSUM_FILE" ] && [ "$(cat "$BACKEND_CHECKSUM_FILE" 2>/dev/null || true)" != "$CURRENT_BACKEND_CHECKSUM" ]; then
        NEED_BACKEND_RESTART=true
    elif [ -n "$SOURCE_BACKEND_VERSION" ] && [ -f "$BACKEND_VERSION_FILE" ] && [ "$(cat "$BACKEND_VERSION_FILE" 2>/dev/null || true)" != "$SOURCE_BACKEND_VERSION" ]; then
        NEED_BACKEND_RESTART=true
    elif [ ! -f "$BACKEND_CHECKSUM_FILE" ]; then
        NEED_BACKEND_RESTART=true
    fi
fi

log info "User exists: $USER_EXISTS | Project: $PI_MON_EXISTS | Venv: $VENV_EXISTS | Service: $SERVICE_RUNNING | Nginx: $NGINX_CONFIGURED | Frontend: $FRONTEND_BUILT"

# ----------------------------------------------------------------------------
# Ensure user and directories
# ----------------------------------------------------------------------------
ensure_user() {
    if [ "$USER_EXISTS" = false ]; then
        log error "Target user '$SYSTEM_USER' not found. Re-run with sudo as the desired user or pass --user <name>."
        exit 1
    fi
    if [ "$PI_MON_EXISTS" = false ]; then
        log info "Creating project directory at $PI_MON_DIR"
        run_cmd mkdir -p "$PI_MON_DIR"
        run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$PI_MON_DIR"
    fi
}

# ----------------------------------------------------------------------------
# Python venv and backend service
# ----------------------------------------------------------------------------
refresh_backend_state() {
    VENV_EXISTS=false
    if [ -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        if "$VENV_DIR/bin/python" -c 'import sys; print(sys.version)' >/dev/null 2>&1; then
            VENV_EXISTS=true
        fi
    fi
    SERVICE_EXISTS=false
    SERVICE_RUNNING=false
    if [ -f "$SERVICE_FILE" ]; then
        SERVICE_EXISTS=true
        if systemctl is-active --quiet pi-monitor-backend.service; then SERVICE_RUNNING=true; fi
    fi
}

bootstrap_with_setup_script() {
    local setup_script="$SCRIPT_DIR/scripts/setup_venv_systemd.sh"
    if [ ! -f "$setup_script" ]; then
        log warn "Bootstrap script not found: $setup_script"
        return 0
    fi
    log info "Bootstrapping via scripts/setup_venv_systemd.sh"
    # Ensure prerequisites the bootstrap script expects
    if ! command -v python3 >/dev/null 2>&1; then
        run_cmd apt-get update -y
        run_cmd apt-get install -y python3 python3-venv python3-pip
    fi
    if ! command -v npm >/dev/null 2>&1; then
        log info "Installing Node.js for bootstrap"
        run_cmd curl -fsSL https://deb.nodesource.com/setup_18.x \| bash -
        run_cmd apt-get install -y nodejs
    fi
    run_cmd bash "$setup_script" "$PI_MON_DIR"
    refresh_backend_state
}

ensure_venv() {
    if [ "$SKIP_BACKEND" = true ]; then return 0; fi
    if [ "$VENV_EXISTS" = false ]; then
        log info "Setting up Python venv at $VENV_DIR"
        if ! command -v python3 >/dev/null 2>&1; then
            run_cmd apt-get update -y
            run_cmd apt-get install -y python3 python3-venv python3-pip
        fi
        run_cmd sudo -u "$SYSTEM_USER" python3 -m venv "$VENV_DIR"
        run_cmd "$VENV_DIR/bin/pip" install --upgrade pip
    fi
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        log info "Installing/updating backend dependencies"
        run_cmd "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade
    fi
}

setup_backend_service() {
    if [ "$SKIP_BACKEND" = true ]; then return 0; fi
    if [ "$SERVICE_EXISTS" = false ]; then
        log info "Creating systemd service"
        cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pi Monitor Backend Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=${SYSTEM_USER}
Group=${SYSTEM_USER}
WorkingDirectory=${PI_MON_DIR}/backend
Environment=PYTHONUNBUFFERED=1
Environment=PI_MONITOR_ENV=production
Environment=PI_MONITOR_PRODUCTION_URL=${PRODUCTION_URL}
EnvironmentFile=${PI_MON_DIR}/backend/.env
ExecStart=${VENV_DIR}/bin/python ${PI_MON_DIR}/backend/start_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-monitor
LimitNOFILE=65536
LimitNPROC=4096
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${PI_MON_DIR}/backend ${PI_MON_DIR}
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF
    fi

    if [ ! -f "$PI_MON_DIR/backend/.env" ]; then
        log info "Creating backend .env"
        cat > "$PI_MON_DIR/backend/.env" <<EOF
PI_MONITOR_API_KEY=pi-monitor-api-key-2024
PI_MONITOR_ENV=production
PI_MONITOR_PRODUCTION_URL=${PRODUCTION_URL}
EOF
        run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$PI_MON_DIR/backend/.env"
    fi

    run_cmd systemctl daemon-reload
    run_cmd systemctl enable pi-monitor-backend.service
    if [ "$SERVICE_RUNNING" = false ]; then
        log info "Starting backend service"
        run_cmd systemctl start pi-monitor-backend.service
        sleep 2
    fi

    if [ "$NEED_BACKEND_RESTART" = true ]; then
        log info "Restarting backend (changes detected)"
        run_cmd systemctl restart pi-monitor-backend.service || true
        sleep 2
        echo "$CURRENT_BACKEND_CHECKSUM" > "$BACKEND_CHECKSUM_FILE" || true
        [ -n "$SOURCE_BACKEND_VERSION" ] && echo "$SOURCE_BACKEND_VERSION" > "$BACKEND_VERSION_FILE" || true
        run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$BACKEND_CHECKSUM_FILE" || true
        [ -f "$BACKEND_VERSION_FILE" ] && run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$BACKEND_VERSION_FILE" || true
    fi
}

# ----------------------------------------------------------------------------
# Frontend build
# ----------------------------------------------------------------------------
build_frontend() {
    if [ "$SKIP_FRONTEND" = true ]; then return 0; fi
    if [ "$ONLY_TARGET" = "backend" ] || [ "$ONLY_TARGET" = "nginx" ] || [ "$ONLY_TARGET" = "verify" ]; then return 0; fi
    if [ "$NEED_FRONTEND_BUILD" = false ]; then
        local v="$DEPLOYED_FRONTEND_VERSION"; [ -z "$v" ] && v="$SOURCE_FRONTEND_VERSION"
        log info "Frontend up-to-date${v:+ (version $v)}"
        return 0
    fi
    log info "Building frontend"
    if ! command -v npm >/dev/null 2>&1; then
        log info "Installing Node.js"
        run_cmd curl -fsSL https://deb.nodesource.com/setup_18.x \| bash -
        run_cmd apt-get install -y nodejs
    fi
    cat > "$PI_MON_DIR/frontend/.env.production" <<EOF
REACT_APP_SERVER_URL=dynamic
REACT_APP_API_BASE_URL=dynamic
REACT_APP_ENVIRONMENT=production
REACT_APP_BACKEND_PORT=${BACKEND_PORT}
REACT_APP_FRONTEND_PORT=${NGINX_PORT}
EOF
    ( cd "$PI_MON_DIR/frontend" && run_cmd npm install --no-audit --no-fund && run_cmd npm run build )
    run_cmd mkdir -p "$WEB_ROOT"
    run_cmd cp -r "$PI_MON_DIR/frontend/build/"* "$WEB_ROOT/"
    run_cmd chown -R www-data:www-data "$WEB_ROOT"
    echo "$CURRENT_FRONTEND_CHECKSUM" > "$FRONTEND_CHECKSUM_FILE" || true
    echo "$CURRENT_FRONTEND_ENV_SIG" > "$FRONTEND_ENV_SIG_FILE" || true
    run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$FRONTEND_CHECKSUM_FILE" "$FRONTEND_ENV_SIG_FILE" || true
}

# ----------------------------------------------------------------------------
# Nginx config for subdomain
# ----------------------------------------------------------------------------
configure_nginx() {
    if [ "$SKIP_NGINX" = true ]; then return 0; fi
    if [ "$ONLY_TARGET" = "backend" ] || [ "$ONLY_TARGET" = "frontend" ] || [ "$ONLY_TARGET" = "verify" ]; then return 0; fi
    log info "Configuring Nginx for domain $DOMAIN"
    if ! command -v nginx >/dev/null 2>&1; then
        run_cmd apt-get update -y
        run_cmd apt-get install -y nginx
    fi

    local site_conf_src="$PI_MON_DIR/nginx/pi-monitor.conf"
    local site_name="pi-monitor"
    local site_conf_dst="$NGINX_SITES_AVAILABLE/$site_name"
    local tmp_conf
    tmp_conf="$(mktemp)"

    if [ -f "$site_conf_src" ]; then
        cp "$site_conf_src" "$tmp_conf"
        sed -i -E "s/server_name[[:space:]].*;/server_name ${DOMAIN};/" "$tmp_conf" || true
        sed -i -E "s@root[[:space:]].*;@root ${WEB_ROOT};@" "$tmp_conf"
        sed -i -E "s/(listen[[:space:]]+)[0-9]+;/\1${NGINX_PORT};/" "$tmp_conf" || true
        sed -i -E "s@proxy_pass[[:space:]]+http://127.0.0.1:[0-9]+/api/@proxy_pass http://127.0.0.1:${BACKEND_PORT}/api/@g" "$tmp_conf" || true
        sed -i -E "s@proxy_pass[[:space:]]+http://127.0.0.1:[0-9]+/health@proxy_pass http://127.0.0.1:${BACKEND_PORT}/health@g" "$tmp_conf" || true
    else
        cat > "$tmp_conf" <<EOF
server {
  listen ${NGINX_PORT};
  server_name ${DOMAIN};

  root ${WEB_ROOT};
  index index.html;

  location / {
    try_files $uri /index.html;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT}/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }

  location /health {
    proxy_pass http://127.0.0.1:${BACKEND_PORT}/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
EOF
    fi

    local desired_checksum existing_checksum stored_checksum
    desired_checksum="$(sha256sum "$tmp_conf" | awk '{print $1}')"
    if [ -f "$site_conf_dst" ]; then
        existing_checksum="$(sha256sum "$site_conf_dst" | awk '{print $1}')"
    else
        existing_checksum=""
    fi
    if [ -f "$NGINX_CHECKSUM_FILE" ]; then
        stored_checksum="$(cat "$NGINX_CHECKSUM_FILE" 2>/dev/null || true)"
    else
        stored_checksum=""
    fi

    local need_update=false
    if [ ! -f "$site_conf_dst" ] || [ "$desired_checksum" != "$existing_checksum" ] || [ "$desired_checksum" != "$stored_checksum" ]; then
        need_update=true
    fi

    if [ "$need_update" = true ]; then
        log info "Updating Nginx config (changes detected)"
        run_cmd cp "$tmp_conf" "$site_conf_dst"
        run_cmd ln -sf "$site_conf_dst" "$NGINX_SITES_ENABLED/$site_name"
        if [ -L "$NGINX_SITES_ENABLED/default" ]; then run_cmd rm "$NGINX_SITES_ENABLED/default"; fi
        run_cmd nginx -t
        run_cmd systemctl restart nginx
        echo "$desired_checksum" > "$NGINX_CHECKSUM_FILE" || true
        run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$NGINX_CHECKSUM_FILE" || true
    else
        log info "Nginx config up-to-date"
        run_cmd ln -sf "$site_conf_dst" "$NGINX_SITES_ENABLED/$site_name"
    fi

    rm -f "$tmp_conf" || true
}

# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------
verify_stack() {
    if [ -n "$ONLY_TARGET" ] && [ "$ONLY_TARGET" != "verify" ]; then return 0; fi
    log info "Verifying services"
    if ! systemctl is-active --quiet pi-monitor-backend.service; then
        log error "Backend service is not running"
        systemctl status pi-monitor-backend.service --no-pager -l || true
        journalctl -u pi-monitor-backend.service --no-pager -n 20 || true
        exit 1
    fi
    if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        log error "Backend health check failed"
        if command -v ss >/dev/null 2>&1; then ss -tlnp | grep ":${BACKEND_PORT}" || true; else netstat -tlnp 2>/dev/null | grep ":${BACKEND_PORT}" || true; fi
        exit 1
    fi
    if ! systemctl is-active --quiet nginx; then
        log error "Nginx is not running"; systemctl status nginx --no-pager -l || true; exit 1
    fi
    if ! curl -fsS "http://localhost:${NGINX_PORT}/" >/dev/null 2>&1; then
        log warn "Frontend root check failed (may be starting). Re-testing Nginx config"
        nginx -t || true
    fi
    if ! curl -fsS "http://localhost:${NGINX_PORT}/health" >/dev/null 2>&1; then
        log error "Nginx proxy to /health failed"; exit 1
    fi

    local API_KEY=""; local AUTH_HEADER=""
    if [ -f "$PI_MON_DIR/backend/.env" ]; then
        API_KEY=$(grep -E '^PI_MONITOR_API_KEY=' "$PI_MON_DIR/backend/.env" | cut -d'=' -f2 | tr -d '\r')
    fi
    if [ -n "$API_KEY" ]; then AUTH_HEADER="-H 'Authorization: Bearer ${API_KEY}'"; fi
    for endpoint in "/health" "/api/system" "/api/metrics/history?minutes=5" "/api/metrics/database"; do
        if [ "$endpoint" = "/health" ]; then
            curl -fsS "http://127.0.0.1:${BACKEND_PORT}${endpoint}" >/dev/null 2>&1 || log error "API ${endpoint} failed"
        else
            if [ -n "$API_KEY" ]; then
                eval curl -fsS ${AUTH_HEADER} "http://127.0.0.1:${BACKEND_PORT}${endpoint}" >/dev/null 2>&1 || log error "API ${endpoint} failed"
            else
                log warn "Skipping ${endpoint} (no API key)"
            fi
        fi
    done
}

# ----------------------------------------------------------------------------
# Orchestration respecting --only/--skip
# ----------------------------------------------------------------------------
ensure_user
# Bootstrap during full update (no --only) or when explicitly requested
if { [ "$SKIP_BACKEND" = false ] && [ -z "${ONLY_TARGET}" ]; } || [ "$USE_SETUP_SCRIPT" = true ]; then
    bootstrap_with_setup_script
fi
ensure_venv
setup_backend_service
build_frontend
configure_nginx
verify_stack

log info "Done"
