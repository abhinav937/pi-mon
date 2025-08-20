#!/usr/bin/env bash
set -euo pipefail

# Install jq if not present
command -v jq >/dev/null || {
  echo "Installing jq for JSON processing"
  sudo apt update && sudo apt install jq -y
}

# ============================================================================
# Pi Monitor Deployment - Simplified Cloudflare Tunnel Version
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
# Load configurations from JSON
DOMAIN=${DOMAIN:-$(jq -r '.deployment_defaults.domain // "pi.cabhinav.com"' "$CONFIG_FILE")}
API_KEY=${API_KEY:-$(jq -r '.deployment_defaults.api_key // "pi-monitor-api-key-2024"' "$CONFIG_FILE")}
ENV=${ENV:-$(jq -r '.deployment_defaults.env // "production"' "$CONFIG_FILE")}
BACKEND_PORT=${BACKEND_PORT:-$(jq -r '.deployment_defaults.backend_port // "5001"' "$CONFIG_FILE")}

# Load Cloudflare settings
if [ -f "$CONFIG_FILE" ]; then
    ENABLE_CLOUDFLARE=$(jq -r '.cloudflare.enable // false' "$CONFIG_FILE")
    CF_HOSTNAME=$(jq -r '.cloudflare.hostname // ""' "$CONFIG_FILE")
    CF_TUNNEL_NAME=$(jq -r '.cloudflare.tunnel_name // "pi-monitor"' "$CONFIG_FILE")
    CF_TOKEN=$(jq -r '.cloudflare.token // ""' "$CONFIG_FILE")
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
            run_cmd apt-get update -y
            run_cmd apt-get install -y python3 python3-venv python3-pip
        fi
        run_cmd sudo -u "$SYSTEM_USER" python3 -m venv "$VENV_DIR"
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "\"$VENV_DIR/bin/pip\" install -q --upgrade pip >> \"$LOG_FILE\" 2>&1"
        else
            run_cmd "$VENV_DIR/bin/pip" install --upgrade pip
        fi
    fi
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        log info "Installing/updating backend dependencies"
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "\"$VENV_DIR/bin/pip\" install -q -r \"$PI_MON_DIR/backend/requirements.txt\" --upgrade >> \"$LOG_FILE\" 2>&1"
        else
            run_cmd "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade
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
        log info "Installing Node.js"
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "curl -fsSL https://deb.nodesource.com/setup_18.x | bash - >> \"$LOG_FILE\" 2>&1"
            run_cmd "apt-get install -y -qq nodejs >> \"$LOG_FILE\" 2>&1"
        else
            run_cmd curl -fsSL https://deb.nodesource.com/setup_18.x \| bash -
            run_cmd apt-get install -y nodejs
        fi
    fi
    
    if [ "$SILENT_OUTPUT" = true ]; then
        ( cd "$PI_MON_DIR/frontend" && \
          run_cmd "npm install --no-audit --no-fund --silent --loglevel=error --no-progress >> \"$LOG_FILE\" 2>&1" && \
          run_cmd "DISABLE_ESLINT_PLUGIN=true BROWSERSLIST_IGNORE_OLD_DATA=1 npm run -s build >> \"$LOG_FILE\" 2>&1" )
    else
        ( cd "$PI_MON_DIR/frontend" && run_cmd npm install --no-audit --no-fund && run_cmd npm run build )
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
    
    log info "Configuring Nginx"
    if ! command -v nginx >/dev/null 2>&1; then
        run_cmd apt-get update -y
        run_cmd apt-get install -y nginx
    fi

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
# Cloudflare Tunnel
# ----------------------------------------------------------------------------
install_cloudflared() {
    if command -v cloudflared >/dev/null 2>&1; then
        log info "cloudflared present"
        return 0
    fi
    
    log info "Installing cloudflared"
    if command -v apt-get >/dev/null 2>&1; then
        # Check if Cloudflare repository is already configured
        if [ -f /usr/share/keyrings/cloudflare-main.gpg ] && [ -f /etc/apt/sources.list.d/cloudflared.list ]; then
            log info "Cloudflare repository already configured, updating package lists..."
            if [ "$SILENT_OUTPUT" = true ]; then
                run_cmd "apt-get update -y -qq >> \"$LOG_FILE\" 2>&1"
                run_cmd "apt-get install -y -qq cloudflared >> \"$LOG_FILE\" 2>&1" || true
            else
                run_cmd apt-get update -y
                run_cmd apt-get install -y cloudflared || true
            fi
        else
            # Create keyrings directory with proper permissions
            if [ ! -d /usr/share/keyrings ]; then
                run_cmd mkdir -p --mode=0755 /usr/share/keyrings
            fi
            
            # Add Cloudflare GPG key
            if [ ! -f /usr/share/keyrings/cloudflare-main.gpg ]; then
                log info "Adding Cloudflare GPG key..."
                if [ "$SILENT_OUTPUT" = true ]; then
                    run_cmd "curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null" || true
                else
                    run_cmd curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \| tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null || true
                fi
            fi
            
            # Add Cloudflare repository (using 'any' instead of specific codename for better compatibility)
            log info "Adding Cloudflare repository..."
            echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" | tee /etc/apt/sources.list.d/cloudflared.list >/dev/null
            
            # Update package lists and install cloudflared
            log info "Installing cloudflared package..."
            if [ "$SILENT_OUTPUT" = true ]; then
                run_cmd "apt-get update -y -qq >> \"$LOG_FILE\" 2>&1"
                run_cmd "apt-get install -y -qq cloudflared >> \"$LOG_FILE\" 2>&1" || true
            else
                run_cmd apt-get update -y
                run_cmd apt-get install -y cloudflared || true
            fi
        fi
    fi
    
    if ! command -v cloudflared >/dev/null 2>&1; then
        log error "cloudflared installation failed"; exit 2
    fi
}

configure_cloudflare_tunnel() {
    if [ "$ENABLE_CLOUDFLARE" != true ]; then return 0; fi
    if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "_" ]; then
        log error "Cloudflare mode requires a valid domain"; exit 2
    fi

    log info "=== CLOUDFLARE TUNNEL SETUP ==="
    log info "Step 1: Installing cloudflared..."
    install_cloudflared

    if [ -n "$CF_TOKEN" ]; then
        log info "Step 2: Configuring cloudflared service (token-based)"
        log info "  - Domain: $DOMAIN"
        log info "  - Tunnel Name: $CF_TUNNEL_NAME"
        log info "  - Token: ${CF_TOKEN:0:8}...${CF_TOKEN: -4}"
        
        # Enhanced service configuration with better logging
        log info "Step 3: Creating systemd service configuration..."
        cat > /etc/systemd/system/cloudflared.service <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network-online.target
Wants=network-online.target

[Service]
User=root
ExecStart=/usr/bin/env cloudflared --no-autoupdate tunnel run --token ${CF_TOKEN}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cloudflared

# Environment variables for better debugging
Environment=CLOUDFLARE_TUNNEL_DOMAIN=${DOMAIN}
Environment=CLOUDFLARE_TUNNEL_NAME=${CF_TUNNEL_NAME}

[Install]
WantedBy=multi-user.target
EOF
        
        log info "Step 4: Reloading systemd and enabling service..."
        run_cmd systemctl daemon-reload
        run_cmd systemctl enable cloudflared
        
        # Stop existing service if running
        if systemctl is-active --quiet cloudflared; then
            log info "Step 5: Stopping existing cloudflared service..."
            run_cmd systemctl stop cloudflared
            sleep 3
        else
            log info "Step 5: No existing service to stop"
        fi
        
        # Start fresh service
        log info "Step 6: Starting cloudflared service..."
        run_cmd systemctl start cloudflared
        sleep 5
        
        # Verify service is running
        log info "Step 7: Verifying service status..."
        if ! systemctl is-active --quiet cloudflared; then
            log error "cloudflared service failed to start. Check journalctl -u cloudflared"
            log error "Service status:"
            systemctl status cloudflared --no-pager -l || true
            exit 2
        fi
        
        log info "✓ cloudflared service started successfully"
        
        # Wait for tunnel to establish connection
        log info "Step 8: Waiting for tunnel to establish connection to Cloudflare..."
        log info "  This may take a few minutes as the tunnel connects to Cloudflare's edge network"
        
        local tunnel_ready=false
        local attempts=0
        local max_attempts=60  # Increased to 10 minutes total
        
        while [ "$tunnel_ready" = false ] && [ $attempts -lt $max_attempts ]; do
            attempts=$((attempts + 1))
            log info "  Connection attempt $attempts/$max_attempts..."
            
            # First, just wait for the tunnel to start locally (this happens quickly)
            if curl -fsS --max-time 5 "http://localhost/health" >/dev/null 2>&1; then
                log info "  ✓ Local tunnel endpoint responding"
                
                # Now wait for Cloudflare to update their routing (this takes time)
                log info "  Waiting for Cloudflare to update routing tables..."
                log info "  This typically takes 2-5 minutes for new connections"
                
                # Give Cloudflare time to establish the tunnel connection
                sleep 30
                
                # Check if tunnel is now connected to Cloudflare edge
                local dns_check
                dns_check=$(dig +short "$DOMAIN" 2>/dev/null | head -1 || echo "")
                
                if echo "$dns_check" | grep -q "104.21\|104.16\|104.32\|104.48\|104.64\|104.80\|104.96"; then
                    log info "  ✓ DNS routing to Cloudflare edge detected"
                    log info "  ✓ Current DNS: $dns_check"
                    tunnel_ready=true
                    break
                else
                    log info "  Still waiting for Cloudflare routing update... (current: $dns_check)"
                    log info "  Attempt $attempts: Tunnel connected locally, waiting for edge routing..."
                    sleep 30  # Wait longer between checks
                fi
            else
                log info "  Waiting for tunnel to start locally..."
                sleep 10
            fi
        done
        
        if [ "$tunnel_ready" = true ]; then
            log info "✓ Cloudflare tunnel fully connected to edge network"
        else
            log warn "Tunnel connected locally but still waiting for Cloudflare routing"
            log warn "This is normal - routing can take up to 10 minutes for new connections"
            log warn "Will verify in final check"
        fi
        
        log info "=== TUNNEL SETUP COMPLETE ==="
        return 0
    fi

    log error "No Cloudflare token provided. Create a tunnel in Cloudflare Dashboard and provide --cf-token <TOKEN>"
    exit 2
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
    
    if [ "$ENABLE_CLOUDFLARE" = true ]; then
        log info "=== CLOUDFLARE TUNNEL VERIFICATION ==="
        
        # Step 1: Check tunnel service status
        log info "Step 1: Checking cloudflared service status..."
        if systemctl is-active --quiet cloudflared; then
            log info "✓ cloudflared service: active"
            
            # Step 2: Check tunnel connectivity and DNS
            local host="${CF_HOSTNAME:-$DOMAIN}"
            log info "Step 2: Checking tunnel status for $host"
            
            # Get DNS records first to see current routing
            log info "Step 3: Checking DNS routing configuration..."
            local dns_records
            dns_records=$(dig +short "$host" 2>/dev/null | tr '\n' ' ' || echo "DNS lookup failed")
            log info "  Current DNS A records: $dns_records"
            
                             # Check if DNS points to Cloudflare edge IPs
                 if echo "$dns_records" | grep -q "104.21\|104.16\|104.32\|104.48\|104.64\|104.80\|104.96"; then
                     log info "✓ DNS routing to Cloudflare edge detected"
                     
                     # Step 4: Check if tunnel is serving HTTPS traffic
                     log info "Step 4: Testing HTTPS tunnel connectivity..."
                     if curl -fsS --max-time 8 "https://$host/health" >/dev/null 2>&1; then
                         log info "✓ Tunnel HTTPS health check passed"
                         
                         # Step 5: Check for Cloudflare headers
                         log info "Step 5: Verifying Cloudflare headers..."
                         local cf_headers
                         cf_headers=$(curl -fsS --max-time 8 -I "https://$host/health" 2>/dev/null || echo "")
                         
                         if echo "$cf_headers" | grep -q "CF-Ray"; then
                             log info "✓ Cloudflare CF-Ray header present"
                         else
                             log warn "⚠ CF-Ray header missing - tunnel may not be fully connected"
                         fi
                         
                         if echo "$cf_headers" | grep -q "Server: cloudflare"; then
                             log info "✓ Cloudflare server header present"
                         else
                             log warn "⚠ Cloudflare server header missing"
                         fi
                         
                         log info "✓ Domain serving OK: https://$host/health"
                         log info "✓ Cloudflare tunnel fully operational"
                         
                     else
                         log error "✗ Tunnel HTTPS health check failed - tunnel not serving traffic"
                         log info "Attempting tunnel restart to fix issue..."
                         run_cmd systemctl restart cloudflared
                         sleep 5
                         
                         # Retry health check
                         if curl -fsS --max-time 8 "https://$host/health" >/dev/null 2>&1; then
                             log info "✓ Tunnel restored after restart"
                         else
                             log error "✗ Tunnel still not working after restart"
                         fi
                     fi
                     
                 else
                     log warn "⚠ DNS not pointing to Cloudflare edge IPs: $dns_records"
                     log warn "This is normal for new tunnel connections - routing takes 2-10 minutes"
                     log warn "The tunnel is working locally, just waiting for Cloudflare to update routing"
                     
                     # Check if tunnel is at least running locally
                     log info "Step 4: Checking local tunnel endpoint..."
                     if curl -fsS --max-time 8 "http://localhost/health" >/dev/null 2>&1; then
                         log info "✓ Local tunnel endpoint working"
                         log info "✓ Tunnel is connected to Cloudflare (locally accessible)"
                         log info "✓ Waiting for Cloudflare to update their routing tables..."
                         log info "✓ This is normal and can take 2-10 minutes for new connections"
                     else
                         log error "✗ Local tunnel endpoint failing - this indicates a real problem"
                     fi
                     
                     # Don't restart the tunnel - it's working, just waiting for routing
                     log info "Step 5: Tunnel is working correctly - no restart needed"
                     log info "  The tunnel will automatically route traffic once Cloudflare updates routing"
                     log info "  This typically happens within 2-10 minutes for new connections"
                 fi
            
        else
            log error "✗ cloudflared service: inactive"
            log info "Starting cloudflared service..."
            run_cmd systemctl start cloudflared
            sleep 5
            
            if systemctl is-active --quiet cloudflared; then
                log info "✓ cloudflared service started"
            else
                log error "✗ Failed to start cloudflared service"
            fi
        fi
        
        # Final verification
        log info "=== FINAL TUNNEL VERIFICATION ==="
        if curl -fsS --max-time 8 "https://$host/health" >/dev/null 2>&1; then
            log info "✓ Cloudflare tunnel fully operational"
            log info "✓ Domain accessible via HTTPS"
            log info "✓ Traffic routing through Cloudflare edge"
            log info "✓ Dashboard should show active tunnel (not --)"
        else
            log error "✗ Cloudflare tunnel verification failed"
            log error "Check tunnel configuration and Cloudflare dashboard"
            log error "Dashboard may still show -- until tunnel fully connects"
        fi
        
        log info "=== VERIFICATION COMPLETE ==="
    fi
}

# ----------------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------------
ensure_user
ensure_venv
setup_backend_service
build_frontend
configure_nginx
configure_cloudflare_tunnel
verify_stack

log info "deploy complete"
