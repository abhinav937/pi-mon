#!/bin/bash
set -euo pipefail

# Pi Monitor Deployment Script - Optimized for Raspberry Pi 5
# ============================================================================

# Defaults
DOMAIN=""
API_KEY=""
ENV=""
BACKEND_PORT="5001"
PI_MON_DIR=""
WEB_ROOT="/var/www/pi-monitor"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
VENV_DIR=""
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"
STATE_DIR=""
SYSTEM_USER=""

# Cloudflare Tunnel
ENABLE_CLOUDFLARE=false
CF_HOSTNAME=""
CF_TUNNEL_NAME="pi-monitor"
CF_TOKEN=""

# Behavior flags
LOG_LEVEL="info"
NO_COLOR=false
DRY_RUN=false
ONLY_TARGET=""
SKIP_FRONTEND=false
SKIP_BACKEND=false
SKIP_NGINX=false
FORCE_FRONTEND=false
FORCE_BACKEND=false
SILENT_OUTPUT=true
SHOW_CONFIG=false
NEED_FRONTEND_BUILD=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Derive defaults
[ -n "$PI_MON_DIR" ] || PI_MON_DIR="$SCRIPT_DIR"
[ -n "$SYSTEM_USER" ] || SYSTEM_USER="${SUDO_USER:-$(id -un)}"

CONFIG_FILE="$PI_MON_DIR/config.json"

# Install jq if not present
command -v jq >/dev/null || {
  echo "Installing jq for JSON processing"
  sudo apt update && sudo apt install jq -y
}

# Load configurations from JSON
if [ -f "$CONFIG_FILE" ]; then
    DOMAIN=${DOMAIN:-$(jq -r '.deployment_defaults.domain // "pi.cabhinav.com"' "$CONFIG_FILE")}
    API_KEY=${API_KEY:-$(jq -r '.deployment_defaults.api_key // "pi-monitor-api-key-2024"' "$CONFIG_FILE")}
    ENV=${ENV:-$(jq -r '.deployment_defaults.env // "production"' "$CONFIG_FILE")}
    BACKEND_PORT=${BACKEND_PORT:-$(jq -r '.deployment_defaults.backend_port // "5001"' "$CONFIG_FILE")}
    
    # Load Cloudflare settings
    ENABLE_CLOUDFLARE=$(jq -r '.cloudflare.enable // false' "$CONFIG_FILE")
    CF_HOSTNAME=$(jq -r '.cloudflare.hostname // ""' "$CONFIG_FILE")
    CF_TUNNEL_NAME=$(jq -r '.cloudflare.tunnel_name // "pi-monitor"' "$CONFIG_FILE")
    CF_TOKEN=$(jq -r '.cloudflare.token // ""' "$CONFIG_FILE")
    CF_USE_CERT=$(jq -r '.cloudflare.use_certificate // false' "$CONFIG_FILE")
    CF_CERT_PATH=$(jq -r '.cloudflare.cert_path // ""' "$CONFIG_FILE")
    CF_USE_UUID=$(jq -r '.cloudflare.use_uuid_config // false' "$CONFIG_FILE")
    CF_TUNNEL_UUID=$(jq -r '.cloudflare.tunnel_uuid // ""' "$CONFIG_FILE")
    CF_CREDENTIALS_FILE=$(jq -r '.cloudflare.credentials_file // ""' "$CONFIG_FILE")
else
    # Fallback defaults
    DOMAIN=${DOMAIN:-"pi.cabhinav.com"}
    API_KEY=${API_KEY:-"pi-monitor-api-key-2024"}
    ENV=${ENV:-"production"}
    BACKEND_PORT=${BACKEND_PORT:-"5001"}
fi

# If CF hostname exists, use it as DOMAIN
if [ -n "$CF_HOSTNAME" ]; then
    DOMAIN="$CF_HOSTNAME"
fi

[ -n "$VENV_DIR" ] || VENV_DIR="$PI_MON_DIR/.venv"
[ -n "$STATE_DIR" ] || STATE_DIR="$PI_MON_DIR/.deploy_state"

LOG_FILE="$STATE_DIR/deploy.log"
[ -f "$LOG_FILE" ] || touch "$LOG_FILE" 2>/dev/null || true

# ----------------------------------------------------------------------------
# Color and logging
# ----------------------------------------------------------------------------
if [ -t 1 ] && [ "${NO_COLOR}" = false ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    WHITE='\033[1;37m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; WHITE=''; NC=''
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
    local tag=""; local color=""; local text="$WHITE"; local reset="$NC"
    case "$level" in
        debug) tag="DEBUG"; color="$BLUE" ;;
        info)  tag="INFO";  color="$GREEN" ;;
        warn)  tag="WARN";  color="$YELLOW" ;;
        error) tag="ERROR"; color="$RED" ;;
        *)     tag="INFO";  color="" ;;
    esac
    if [ "$NO_COLOR" = true ]; then color=""; text=""; reset=""; fi
    printf "%b[%s] %-5s%b %b%s%b\n" "$color" "$ts" "$tag" "$reset" "$text" "$*" "$reset"
    if [ -n "${LOG_FILE:-}" ]; then
        echo "[$ts] $tag $*" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        log debug "DRY-RUN: $*"
    else
        log debug "EXEC: $*"
        eval "$@"
    fi
}

# ----------------------------------------------------------------------------
# Pi 5 System Detection and Optimization
# ----------------------------------------------------------------------------
detect_system() {
    local arch
    arch=$(uname -m)
    
    if [ "$arch" = "aarch64" ] || [ "$arch" = "arm64" ]; then
        log info "Detected ARM64 architecture (Raspberry Pi 5 compatible)"
        # Check if running on actual Pi hardware
        if [ -f /proc/cpuinfo ] && grep -q "Raspberry Pi" /proc/cpuinfo; then
            local pi_model
            pi_model=$(grep "Model" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
            log info "Hardware: $pi_model"
        fi
    else
        log warn "Non-ARM64 architecture detected: $arch"
        log warn "This script is optimized for Raspberry Pi 5 (ARM64)"
    fi
}

optimize_pi5_system() {
    log info "Applying Raspberry Pi 5 system optimizations"
    
    # Enable performance governor for Pi 5
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors ]; then
        local available_govs
        available_govs=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors)
        if echo "$available_govs" | grep -q "performance"; then
            log info "Setting CPU governor to performance mode"
            echo performance | tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1 || true
        fi
    fi
    
    # Set Pi 5 specific ulimits
    log info "Setting Pi 5 specific system limits"
    cat > /etc/security/limits.d/pi-monitor.conf <<EOF
# Pi 5 specific limits for pi-monitor
${SYSTEM_USER} soft nofile 65536
${SYSTEM_USER} hard nofile 65536
${SYSTEM_USER} soft nproc 4096
${SYSTEM_USER} hard nproc 4096
www-data soft nofile 65536
www-data hard nofile 65536
EOF
    
    log info "Pi 5 system optimizations applied"
}

# ----------------------------------------------------------------------------
# CLI args
# ----------------------------------------------------------------------------
usage() {
    cat <<USAGE
Usage: sudo ./deploy.sh [flags]

Pi Monitor Deployment Script - Optimized for Raspberry Pi 5
================================================================

This script is specifically optimized for Raspberry Pi 5 (ARM64) with:
- ARM64-optimized Python 3.11+ installation
- Node.js 20.x ARM64 compatibility
- Pi 5 specific system optimizations (CPU governor, memory limits)
- Enhanced Nginx configuration for Pi 5 performance
- Optimized systemd service settings

Flags:
  --domain VALUE               Domain (default: ${DOMAIN})
  --api-key VALUE              Backend API key (default: ${API_KEY})
  --env VALUE                  Backend environment (default: ${ENV})
  --backend-port N             Backend port (default: ${BACKEND_PORT})
  --pi-mon-dir PATH            Project root (default: ${PI_MON_DIR})
  --venv-dir PATH              Python venv dir (default: <pi-mon-dir>/.venv)
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
  --show-config                Print resolved configuration and exit
  -h, --help                   Show this help

Pi 5 Optimizations Applied:
  ✓ CPU performance governor
  ✓ Memory and file descriptor limits
  ✓ ARM64-optimized package installation
  ✓ Enhanced Nginx configuration
  ✓ Optimized systemd service settings

USAGE
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --domain) DOMAIN="$2"; shift 2 ;;
            --api-key) API_KEY="$2"; shift 2 ;;
            --env) ENV="$2"; shift 2 ;;
            --backend-port) BACKEND_PORT="$2"; shift 2 ;;
            --pi-mon-dir) PI_MON_DIR="$2"; shift 2 ;;
            --venv-dir) VENV_DIR="$2"; shift 2 ;;
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
            --show-config) SHOW_CONFIG=true; shift 1 ;;
            -h|--help) usage; exit 0 ;;
            *) log error "Unknown flag: $1"; usage; exit 2 ;;
        esac
    done
    LOG_LEVEL_NUM=$(_level_value "$LOG_LEVEL")
}

parse_args "$@"

# Show resolved configuration and exit early if requested
if [ "$SHOW_CONFIG" = true ]; then
    cat <<CFG
domain:            $DOMAIN
pi_mon_dir:        $PI_MON_DIR
venv_dir:          $VENV_DIR
web_root:          $WEB_ROOT
backend_port:      $BACKEND_PORT
system_user:       $SYSTEM_USER
log_level:         $LOG_LEVEL
only:              ${ONLY_TARGET:-}
skip_frontend:     $SKIP_FRONTEND
skip_backend:      $SKIP_BACKEND
skip_nginx:        $SKIP_NGINX
force_frontend:    $FORCE_FRONTEND
force_backend:     $FORCE_BACKEND
enable_cloudflare: $ENABLE_CLOUDFLARE
cf_hostname:       ${CF_HOSTNAME:-}
cf_tunnel_name:    ${CF_TUNNEL_NAME:-}
CFG
    exit 0
fi

if [[ "$EUID" -ne 0 ]]; then
    log error "This script must be run with sudo"
    exit 1
fi

# ----------------------------------------------------------------------------
# Discovery and state
# ----------------------------------------------------------------------------
log info "Checking current state"
log info "pi-mon deploy starting"

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
if [ -f "$NGINX_SITES_AVAILABLE/pi-monitor" ] && [ -L "$NGINX_SITES_ENABLED/pi-monitor" ]; then
    NGINX_CONFIGURED=true
fi

FRONTEND_BUILT=false
[ -f "$WEB_ROOT/index.html" ] && FRONTEND_BUILT=true

# Determine if frontend needs building
NEED_FRONTEND_BUILD=false
if [ "$FRONTEND_BUILT" = false ] || [ "$FORCE_FRONTEND" = true ]; then
        NEED_FRONTEND_BUILD=true
fi

BACKEND_ACCESSIBLE=false
if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then BACKEND_ACCESSIBLE=true; fi

log info "User exists: $USER_EXISTS | Project: $PI_MON_EXISTS | Venv: $VENV_EXISTS | Service: $SERVICE_RUNNING | Nginx: $NGINX_CONFIGURED | Frontend: $FRONTEND_BUILT"
log info "paths: PI_MON_DIR=$PI_MON_DIR WEB_ROOT=$WEB_ROOT VENV_DIR=$VENV_DIR"

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
ensure_venv() {
    if [ "$SKIP_BACKEND" = true ]; then return 0; fi
    if [ "$VENV_EXISTS" = false ]; then
        log info "Setting up Python venv at $VENV_DIR"
        if ! command -v python3 >/dev/null 2>&1; then
            log info "Installing Python 3 for Raspberry Pi 5"
            run_cmd apt-get update -y
            # Install Python 3.11+ which is optimized for Pi 5
            run_cmd apt-get install -y python3 python3.11 python3.11-venv python3.11-dev python3-pip python3-setuptools
            # Ensure python3 points to the latest version
            if command -v python3.11 >/dev/null 2>&1; then
                run_cmd update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            fi
        fi
        
        # Create venv with optimized Python version
        local python_cmd="python3"
        if command -v python3.11 >/dev/null 2>&1; then
            python_cmd="python3.11"
            log info "Using Python 3.11 for optimal Pi 5 performance"
        fi
        
        run_cmd sudo -u "$SYSTEM_USER" "$python_cmd" -m venv "$VENV_DIR"
        
        # Upgrade pip with Pi 5 optimized flags
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "\"$VENV_DIR/bin/pip\" install -q --upgrade pip --no-cache-dir >> \"$LOG_FILE\" 2>&1"
        else
            run_cmd "$VENV_DIR/bin/pip" install --upgrade pip --no-cache-dir
        fi
    fi
    
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        log info "Installing/updating backend dependencies (optimized for Pi 5)"
        # Use Pi 5 optimized pip flags
        local pip_flags="--no-cache-dir --prefer-binary"
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "\"$VENV_DIR/bin/pip\" install -q -r \"$PI_MON_DIR/backend/requirements.txt\" --upgrade $pip_flags >> \"$LOG_FILE\" 2>&1"
        else
            run_cmd "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade $pip_flags
        fi
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
EnvironmentFile=${PI_MON_DIR}/backend/.env
ExecStart=${VENV_DIR}/bin/python ${PI_MON_DIR}/backend/start_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-monitor

# Pi 5 optimizations
Nice=-10
IOSchedulingClass=1
IOSchedulingPriority=4
CPUSchedulingPolicy=1
CPUSchedulingPriority=50

# Memory and resource limits for Pi 5
MemoryMax=512M
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    fi

    log info "Configuring backend .env"
    cat > "$PI_MON_DIR/backend/.env" <<EOF
PI_MONITOR_API_KEY=$API_KEY
PI_MONITOR_ENV=$ENV
EOF
    run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$PI_MON_DIR/backend/.env"

    run_cmd systemctl daemon-reload
    run_cmd systemctl enable pi-monitor-backend.service
    if [ "$SERVICE_RUNNING" = false ]; then
        log info "Starting backend service"
        run_cmd systemctl start pi-monitor-backend.service
        sleep 2
    fi

    if [ "$FORCE_BACKEND" = true ]; then
        log info "Restarting backend (force requested)"
        run_cmd systemctl restart pi-monitor-backend.service
        sleep 2
    fi
}

# ----------------------------------------------------------------------------
# Frontend build
# ----------------------------------------------------------------------------
build_frontend() {
    if [ "$SKIP_FRONTEND" = true ]; then return 0; fi
    if [ "$ONLY_TARGET" = "backend" ] || [ "$ONLY_TARGET" = "nginx" ] || [ "$ONLY_TARGET" = "verify" ]; then return 0; fi
    if [ "$NEED_FRONTEND_BUILD" = false ] && [ "$FORCE_FRONTEND" = false ]; then
        log info "Frontend up-to-date"
        return 0
    fi
    
    log info "Building frontend"
    if ! command -v npm >/dev/null 2>&1; then
        log info "Installing Node.js for Raspberry Pi 5"
        # Use NodeSource repository optimized for ARM64
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >> \"$LOG_FILE\" 2>&1"
            run_cmd "apt-get install -y -qq nodejs >> \"$LOG_FILE\" 2>&1"
        else
            run_cmd curl -fsSL https://deb.nodesource.com/setup_20.x \| bash -
            run_cmd apt-get install -y nodejs
        fi
        
        # Verify ARM64 compatibility
        local node_arch
        node_arch=$(node -p "process.arch" 2>/dev/null || echo "unknown")
        if [ "$node_arch" = "arm64" ]; then
            log info "Node.js ARM64 version installed successfully"
        else
            log warn "Node.js architecture: $node_arch (expected arm64)"
        fi
    fi
    
    # Pi 5 optimized build flags
    local npm_flags="--no-audit --no-fund --no-optional"
    local build_env="DISABLE_ESLINT_PLUGIN=true BROWSERSLIST_IGNORE_OLD_DATA=1 NODE_OPTIONS=--max-old-space-size=512"
    
    if [ "$SILENT_OUTPUT" = true ]; then
        ( cd "$PI_MON_DIR/frontend" && \
          run_cmd "npm install $npm_flags --silent --loglevel=error --no-progress >> \"$LOG_FILE\" 2>&1" && \
          run_cmd "$build_env npm run -s build >> \"$LOG_FILE\" 2>&1" )
    else
        ( cd "$PI_MON_DIR/frontend" && \
          run_cmd npm install $npm_flags && \
          run_cmd $build_env npm run build )
    fi
    
    run_cmd mkdir -p "$WEB_ROOT"
    if command -v rsync >/dev/null 2>&1; then
        run_cmd rsync -a --delete "$PI_MON_DIR/frontend/build/" "$WEB_ROOT/"
    else
        run_cmd "find \"$WEB_ROOT\" -mindepth 1 -delete"
        run_cmd cp -r "$PI_MON_DIR/frontend/build/"* "$WEB_ROOT/"
    fi
    run_cmd chown -R www-data:www-data "$WEB_ROOT"
}

# ----------------------------------------------------------------------------
# Nginx config
# ----------------------------------------------------------------------------
configure_nginx() {
    if [ "$SKIP_NGINX" = true ]; then return 0; fi
    if [ "$ONLY_TARGET" = "backend" ] || [ "$ONLY_TARGET" = "frontend" ] || [ "$ONLY_TARGET" = "verify" ]; then return 0; fi
    
    log info "Configuring Nginx for Raspberry Pi 5"
    if ! command -v nginx >/dev/null 2>&1; then
        run_cmd apt-get update -y
        run_cmd apt-get install -y nginx nginx-extras
    fi
    
    # Pi 5 specific Nginx optimizations
    log info "Applying Pi 5 Nginx optimizations"
    cat > /etc/nginx/conf.d/pi-monitor-optimizations.conf <<EOF
# Pi 5 specific Nginx optimizations
worker_processes auto;
worker_rlimit_nofile 65536;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    # Pi 5 memory optimizations
    client_body_buffer_size 16k;
    client_header_buffer_size 1k;
    large_client_header_buffers 2 1k;
    
    # Gzip compression for Pi 5
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Pi 5 caching optimizations
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
EOF

    # Simple Nginx configuration for Cloudflare tunnel (HTTP only)
    cat > "$NGINX_SITES_AVAILABLE/pi-monitor" <<EOF
# HTTP server - Cloudflare tunnel handles SSL termination
server {
    listen 80;
    server_name localhost;

  root ${WEB_ROOT};
  index index.html;

    # Handle static files
  location / {
    try_files \$uri /index.html;
  }

    # API endpoints - proxy to backend
  location /api/ {
    proxy_pass http://127.0.0.1:${BACKEND_PORT}/api/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
  }

    # Health endpoint
  location /health {
    proxy_pass http://127.0.0.1:${BACKEND_PORT}/health;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }

  # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

    run_cmd ln -sf "$NGINX_SITES_AVAILABLE/pi-monitor" "$NGINX_SITES_ENABLED/pi-monitor"
        if [ -L "$NGINX_SITES_ENABLED/default" ]; then run_cmd rm "$NGINX_SITES_ENABLED/default"; fi
    
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "nginx -t >/dev/null 2>&1 || nginx -t"
        else
            run_cmd nginx -t
        fi
        run_cmd systemctl restart nginx
}

# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------
verify_stack() {
    if [ -n "$ONLY_TARGET" ] && [ "$ONLY_TARGET" != "verify" ]; then return 0; fi
    
    log info "Verifying services and Pi 5 optimizations"
    
    # Pi 5 specific verification
    log info "=== Pi 5 System Verification ==="
    
    # Check CPU governor
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
        local current_gov
        current_gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
        log info "CPU Governor: $current_gov"
        if [ "$current_gov" = "performance" ]; then
            log info "[OK] CPU running in performance mode"
        else
            log warn "CPU not in performance mode (current: $current_gov)"
        fi
    fi
    
    # Check memory usage
    local mem_info
    mem_info=$(free -h 2>/dev/null | grep "Mem:" || echo "Memory info unavailable")
    log info "Memory Status: $mem_info"
    
    # Check system limits
    if id "$SYSTEM_USER" &>/dev/null; then
        local user_limits
        user_limits=$(ulimit -n 2>/dev/null || echo "unknown")
        log info "User file descriptor limit: $user_limits"
    fi
    
    # Check Pi 5 specific optimizations
    if [ -f /etc/security/limits.d/pi-monitor.conf ]; then
        log info "[OK] Pi 5 system limits configured"
    else
        log warn "Pi 5 system limits not configured"
    fi
    
    if ! systemctl is-active --quiet pi-monitor-backend.service; then
        log error "Backend service is not running"
        systemctl status pi-monitor-backend.service --no-pager -l || true
        exit 1
    fi
    
    if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        log error "Backend health check failed"
        exit 1
    fi
    
    if ! systemctl is-active --quiet nginx; then
        log error "Nginx is not running"
        systemctl status nginx --no-pager -l || true
        exit 1
    fi
    
    # Check HTTP endpoints (Cloudflare tunnel handles HTTPS)
    if ! curl -fsS "http://localhost/" >/dev/null 2>&1; then
        log warn "Frontend HTTP root check failed"
    fi
    
    if ! curl -fsS "http://localhost/health" >/dev/null 2>&1; then
        log error "Nginx HTTP proxy to /health failed"
        exit 1
    fi
    
    log info "=== VERIFICATION COMPLETE ==="
}

# ----------------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------------
detect_system
optimize_pi5_system
ensure_user
ensure_venv
setup_backend_service
build_frontend
configure_nginx
verify_stack

log info "deploy complete"
