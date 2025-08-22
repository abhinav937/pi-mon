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
PIP_FLAGS="--no-cache-dir"

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
TEST_CHECKSUMS=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Derive defaults
[ -n "$PI_MON_DIR" ] || PI_MON_DIR="$SCRIPT_DIR"
[ -n "$SYSTEM_USER" ] || SYSTEM_USER="${SUDO_USER:-$(id -un)}"

CONFIG_FILE="$PI_MON_DIR/config.json"

# Pre-flight checks
pre_flight_checks() {
    log info "Running pre-flight checks..."
    local arch
    arch=$(uname -m)
    if [ "$arch" != "aarch64" ] && [ "$arch" != "arm64" ]; then
        log error "This script requires ARM64 architecture (Raspberry Pi 5)."
        exit 1
    fi
    if ! grep -qi "debian\|ubuntu\|raspbian" /etc/os-release; then
        log error "This script requires a Debian-based OS (e.g., Raspberry Pi OS)."
        exit 1
    fi
    if ! ping -c 1 8.8.8.8 &>/dev/null; then
        log error "No internet connectivity. Please check your network."
        exit 1
    fi
    available_space=$(df -k "$PI_MON_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 1048576 ]; then # 1GB in KB
        log error "Insufficient disk space (<1GB) in $PI_MON_DIR."
        exit 1
    fi
    if ! id "$SYSTEM_USER" &>/dev/null; then
        log error "Specified user '$SYSTEM_USER' does not exist."
        exit 1
    fi
    if [ -f "$CONFIG_FILE" ] && ! jq . "$CONFIG_FILE" >/dev/null 2>&1; then
        log error "Invalid JSON in $CONFIG_FILE."
        exit 1
    fi
    if [ "$ENABLE_CLOUDFLARE" = true ] && { [ -z "$CF_TOKEN" ] || [ -z "$CF_HOSTNAME" ]; }; then
        log error "Cloudflare enabled but missing token or hostname."
        exit 1
    fi
}

# Install jq if not present
command -v jq >/dev/null || {
    log info "Installing jq for JSON processing"
    run_cmd apt update
    run_cmd apt install jq -y
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
touch "$LOG_FILE" 2>/dev/null || log error "Cannot write to log file $LOG_FILE."

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
    printf "%b[%s] %-5s%b %b%s%b\n" "$color" "$ts" "$tag" "$reset" "$text" "$*" "$reset" >&2
    if [ -w "${LOG_FILE:-}" ]; then
        echo "[$ts] $tag $*" >> "$LOG_FILE" 2>/dev/null
    fi
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        log debug "DRY-RUN: $*"
    else
        log debug "EXEC: $*"
        "$@"
    fi
}

# ----------------------------------------------------------------------------
# Pi 5 System Detection and Optimization
# ----------------------------------------------------------------------------
detect_system() {
    local arch
    arch=$(uname -m)
    
    if [ "$arch" = "aarch64" ] || [ "$arch" = "arm64" ]; then
        if [ -f /proc/cpuinfo ] && grep -q "Raspberry Pi" /proc/cpuinfo; then
            local pi_model
            pi_model=$(grep "Model" /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)
            log info "Hardware: $pi_model (ARM64)"
        else
            log info "ARM64 architecture detected"
        fi
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
            run_cmd echo performance \| tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1
        fi
    fi
    
    # Monitor CPU temperature
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        temp=$(cat /sys/class/thermal/thermal_zone0/temp)
        temp=$((temp / 1000))
        if [ "$temp" -gt 80 ]; then
            log warn "High CPU temperature ($temp°C), risk of thermal throttling."
        fi
    fi
    
    # Set Pi 5 specific ulimits
    cat > /etc/security/limits.d/pi-monitor.conf <<EOF
# Pi 5 specific limits for pi-monitor
${SYSTEM_USER} soft nofile 65536
${SYSTEM_USER} hard nofile 65536
${SYSTEM_USER} soft nproc 4096
${SYSTEM_USER} hard nproc 4096
www-data soft nofile 65536
www-data hard nofile 65536
EOF
    
    log info "Pi 5 optimizations applied"
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

Assumptions:
- Debian-based OS (e.g., Raspberry Pi OS)
- ARM64 architecture
- Internet connectivity
- At least 1GB free disk space
- Sudo privileges

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
  --test-checksums             Test checksum generation and comparison
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
            --test-checksums) TEST_CHECKSUMS=true; shift 1 ;;
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
# Checksum-based update detection
# ----------------------------------------------------------------------------
generate_checksum() {
    local path="$1"
    if [ -f "$path" ]; then
        sha256sum "$path" | cut -d' ' -f1 || echo "0"
    elif [ -d "$path" ]; then
        find "$path" -type f -exec sha256sum {} \; | sort | sha256sum | cut -d' ' -f1 || echo "0"
    else
        echo "0"
    fi
}

check_checksums() {
    if [ "$TEST_CHECKSUMS" = true ]; then
        log info "=== CHECKSUM TESTING ==="
        
        local frontend_checksum=$(generate_checksum "$PI_MON_DIR/frontend")
        local backend_checksum=$(generate_checksum "$PI_MON_DIR/backend")
        local nginx_checksum=$(generate_checksum "$NGINX_SITES_AVAILABLE/pi-monitor")
        
        log info "Frontend checksum: $frontend_checksum"
        log info "Backend checksum: $backend_checksum"
        log info "Nginx checksum: $nginx_checksum"
        
        local stored_frontend=""
        local stored_backend=""
        local stored_nginx=""
        
        if [ -f "$STATE_DIR/frontend.checksum" ]; then
            stored_frontend=$(cat "$STATE_DIR/frontend.checksum")
            log info "Stored frontend checksum: $stored_frontend"
        fi
        
        if [ -f "$STATE_DIR/backend.checksum" ]; then
            stored_backend=$(cat "$STATE_DIR/backend.checksum")
            log info "Stored backend checksum: $stored_backend"
        fi
        
        if [ -f "$STATE_DIR/nginx.checksum" ]; then
            stored_nginx=$(cat "$STATE_DIR/nginx.checksum")
            log info "Stored nginx checksum: $stored_nginx"
        fi
        
        if [ "$frontend_checksum" != "$stored_frontend" ] && [ -n "$stored_frontend" ]; then
            log info "Frontend changes detected - rebuild needed"
            NEED_FRONTEND_BUILD=true
        fi
        
        if [ "$backend_checksum" != "$stored_backend" ] && [ -n "$stored_backend" ]; then
            log info "Backend changes detected - restart needed"
            FORCE_BACKEND=true
        fi
        
        if [ "$nginx_checksum" != "$stored_nginx" ] && [ -n "$stored_nginx" ]; then
            log info "Nginx changes detected - reconfiguration needed"
        fi
        
        log info "=== CHECKSUM TESTING COMPLETE ==="
        exit 0
    fi
}

# ----------------------------------------------------------------------------
# Discovery and state
# ----------------------------------------------------------------------------
log info "Checking current state"
log info "Starting deployment..."
log info "Note: This script will automatically stop/start services as needed"

mkdir -p "$STATE_DIR" || log error "Cannot create state directory $STATE_DIR."
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
for i in {1..3}; do
    if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
        BACKEND_ACCESSIBLE=true
        break
    fi
    log warn "Backend health check failed, retrying ($i/3)..."
    sleep 5
done

log info "Status: User:$USER_EXISTS | Project:$PI_MON_EXISTS | Venv:$VENV_EXISTS | Service:$SERVICE_RUNNING | Nginx:$NGINX_CONFIGURED | Frontend:$FRONTEND_BUILT"

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
    if [ ! -w "$PI_MON_DIR" ]; then
        log error "Directory $PI_MON_DIR is not writable by $SYSTEM_USER."
        exit 1
    fi
}

# ----------------------------------------------------------------------------
# Cloudflare tunnel setup
# ----------------------------------------------------------------------------
setup_cloudflare() {
    if [ "$ENABLE_CLOUDFLARE" = true ]; then
        log info "=== CLOUDFLARE TUNNEL SETUP ==="
        if ! command -v cloudflared >/dev/null 2>&1; then
            log info "Installing cloudflared..."
            run_cmd wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O /usr/local/bin/cloudflared
            run_cmd chmod +x /usr/local/bin/cloudflared
        fi
        if ! command -v cloudflared >/dev/null 2>&1; then
            log error "Failed to install cloudflared."
            exit 1
        fi
        log info "cloudflared present"
        
        log info "Configuring cloudflared service (token-based)"
        log info "- Domain: $CF_HOSTNAME"
        log info "- Tunnel Name: $CF_TUNNEL_NAME"
        log info "- Token: ${CF_TOKEN:0:10}...[redacted]"
        
        # Validate token format (basic check for non-empty and reasonable length)
        if [ ${#CF_TOKEN} -lt 50 ]; then
            log error "Invalid Cloudflare token format (too short)."
            exit 1
        fi
        
        log info "Creating systemd service configuration..."
        cat > /etc/systemd/system/cloudflared.service <<EOF
[Unit]
Description=Cloudflared tunnel for Pi Monitor
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token ${CF_TOKEN}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cloudflared

[Install]
WantedBy=multi-user.target
EOF
        
        log info "Reloading systemd and enabling service..."
        run_cmd systemctl daemon-reload
        run_cmd systemctl enable cloudflared
        
        log info "Stopping existing cloudflared service..."
        systemctl stop cloudflared >/dev/null 2>&1 || true
        
        log info "Starting cloudflared service..."
        run_cmd systemctl start cloudflared
        
        log info "Verifying service status..."
        if systemctl is-active --quiet cloudflared; then
            log info "✓ cloudflared service started successfully"
        else
            log error "cloudflared service failed to start. Check journalctl -u cloudflared."
            exit 1
        fi
        
        log info "Step 8: Waiting for tunnel to establish connection to Cloudflare..."
        log info "This may take 10-15 minutes as the tunnel connects to Cloudflare's edge network"
        log info "You can check progress manually with: journalctl -u cloudflared -f"
        
        # Try a few quick checks first
        for i in {1..3}; do
            if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
                log info "✓ Local tunnel endpoint responding"
                break
            else
                log warn "Local tunnel endpoint not responding, retrying ($i/3)..."
                sleep 10
            fi
        done
        
        # Check if local endpoint is working
        if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
            log warn "Local tunnel endpoint not responding after 3 attempts"
            log info "Tunnel may still be connecting. Please wait 10-15 minutes and check manually:"
            log info "  - Check tunnel status: journalctl -u cloudflared -n 50"
            log info "  - Check local health: curl http://127.0.0.1:${BACKEND_PORT}/health"
            log info "  - Check domain: curl https://$CF_HOSTNAME/health"
            log info "Continuing with deployment..."
            return 0
        fi
        
        # Try domain check a few times
        for i in {1..3}; do
            if curl -fsS "https://$CF_HOSTNAME/health" >/dev/null 2>&1; then
                log info "✓ Domain serving OK: https://$CF_HOSTNAME/health"
                break
            fi
            if [ $i -eq 1 ]; then
                log info "Waiting for Cloudflare routing to update... (this typically takes 10-15 minutes)"
            fi
            sleep 30
        done
        
        if ! curl -fsS "https://$CF_HOSTNAME/health" >/dev/null 2>&1; then
            log warn "Domain not yet accessible via Cloudflare"
            log info "This is normal for new tunnels. Please wait 10-15 minutes and check:"
            log info "  - Domain: https://$CF_HOSTNAME/health"
            log info "  - Tunnel logs: journalctl -u cloudflared -f"
            log info "Continuing with deployment..."
        fi
        
        log info "✓ Cloudflare tunnel setup completed"
        log info "Note: Domain may take 10-15 minutes to become accessible"

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
            run_cmd apt-get install -y python3 python3.11 python3.11-venv python3.11-dev python3-pip python3-setuptools
            if command -v python3.11 >/dev/null 2>&1; then
                run_cmd update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
            fi
        fi
        
        local python_cmd="python3"
        if command -v python3.11 >/dev/null 2>&1; then
            python_cmd="python3.11"
            log info "Using Python 3.11 for optimal Pi 5 performance"
        fi
        python_version=$("$python_cmd" -c "import sys; print(sys.version_info[:2] >= (3, 8))")
        if [ "$python_version" != "True" ]; then
            log error "Python 3.8 or higher is required."
            exit 1
        fi
        
        run_cmd sudo -u "$SYSTEM_USER" "$python_cmd" -m venv "$VENV_DIR"
        
        if ! [ -f "$VENV_DIR/bin/pip" ]; then
            log error "Virtual environment creation failed: pip not found in $VENV_DIR/bin."
            exit 1
        fi
        
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "$VENV_DIR/bin/pip" install -q --upgrade pip "$PIP_FLAGS" >> "$LOG_FILE" 2>&1 || {
                log error "pip upgrade failed, check $LOG_FILE."
                exit 1
            }
        else
            run_cmd "$VENV_DIR/bin/pip" install --upgrade pip "$PIP_FLAGS"
        fi
    fi
    
    if [ ! -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        log warn "requirements.txt missing, installing default dependencies."
        if [ "$SILENT_OUTPUT" = true ]; then
            run_cmd "$VENV_DIR/bin/pip" install -q psutil==5.9.6 "$PIP_FLAGS" >> "$LOG_FILE" 2>&1 || {
                log error "Failed to install default dependencies, check $LOG_FILE."
                exit 1
            }
        else
            run_cmd "$VENV_DIR/bin/pip" install psutil==5.9.6 "$PIP_FLAGS"
        fi
    else
        log info "Installing/updating backend dependencies (optimized for Pi 5)"
        log debug "requirements.txt contents:"
        log debug "$(cat "$PI_MON_DIR/backend/requirements.txt")"
        if [ "$SILENT_OUTPUT" = true ]; then
            log info "Installing/updating backend dependencies (optimized for Pi 5)"
            if ! "$VENV_DIR/bin/pip" install -q -r "$PI_MON_DIR/backend/requirements.txt" --upgrade "$PIP_FLAGS" >> "$LOG_FILE" 2>&1; then
                log error "pip install failed, check $LOG_FILE for details."
                exit 1
            fi
        else
            log info "Installing/updating backend dependencies (optimized for Pi 5)"
            if ! "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade "$PIP_FLAGS"; then
                log error "pip install failed"
                exit 1
            fi
        fi
    fi
}

setup_backend_service() {
    if [ "$SKIP_BACKEND" = true ]; then return 0; fi
    if [ ! -f "$PI_MON_DIR/backend/start_service.py" ]; then
        log error "Backend service script ($PI_MON_DIR/backend/start_service.py) is missing."
        exit 1
    fi
    # Stop the service if it's running to update configuration
    if systemctl is-active --quiet pi-monitor-backend.service; then
        log info "Stopping backend service to update configuration..."
        systemctl stop pi-monitor-backend.service
        sleep 2
    fi
    
    # Always update the service file to ensure correct configuration
    log info "Updating systemd service configuration"
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

    # Verify the service file was created correctly
    if ! grep -q "ExecStart=${VENV_DIR}/bin/python ${PI_MON_DIR}/backend/start_service.py" "$SERVICE_FILE"; then
        log error "Service file configuration is incorrect"
        log error "Expected: ExecStart=${VENV_DIR}/bin/python ${PI_MON_DIR}/backend/start_service.py"
        log error "Actual: $(grep 'ExecStart=' "$SERVICE_FILE")"
        exit 1
    fi
    
    log info "✓ Service file configured correctly"

    log info "Configuring backend .env"
    cat > "$PI_MON_DIR/backend/.env" <<EOF
PI_MONITOR_API_KEY=$API_KEY
PI_MONITOR_ENV=$ENV
EOF
    run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$PI_MON_DIR/backend/.env"
    run_cmd chmod u+rw "$PI_MON_DIR/backend/.env"

    run_cmd systemctl daemon-reload
    run_cmd systemctl enable pi-monitor-backend.service
    if [ "$SERVICE_RUNNING" = false ]; then
        log info "Starting backend service"
        run_cmd systemctl start pi-monitor-backend.service
        sleep 5
    fi

    if [ "$FORCE_BACKEND" = true ]; then
        log info "Restarting backend (force requested)"
        run_cmd systemctl restart pi-monitor-backend.service
        sleep 5
    fi
    
    # Ensure backend service is running
    if ! systemctl is-active --quiet pi-monitor-backend.service; then
        log info "Starting backend service..."
        run_cmd systemctl start pi-monitor-backend.service
        sleep 5
        
        # Verify it started
        if ! systemctl is-active --quiet pi-monitor-backend.service; then
            log error "Backend service failed to start"
            systemctl status pi-monitor-backend.service --no-pager -l || true
            exit 1
        fi
    fi
    
    local backend_checksum
    backend_checksum=$(generate_checksum "$PI_MON_DIR/backend")
    echo "$backend_checksum" > "$STATE_DIR/backend.checksum"
    log info "Backend checksum stored: $backend_checksum"
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
    
    if [ ! -f "$PI_MON_DIR/frontend/package.json" ]; then
        log error "Frontend directory ($PI_MON_DIR/frontend) is missing or invalid."
        exit 1
    fi
    
    free_mem=$(free -m | awk '/Mem:/ {print $7}')
    if [ "$free_mem" -lt 512 ]; then
        log warn "Low memory ($free_mem MB available), frontend build may fail."
    fi
    
    log info "Building frontend"
    if ! command -v npm >/dev/null 2>&1; then
        log info "Installing Node.js for Raspberry Pi 5"
        if ! curl -fsSL https://deb.nodesource.com/setup_20.x >/dev/null; then
            log warn "NodeSource repository unavailable, falling back to default nodejs."
            run_cmd apt-get install -y nodejs
        else
            if [ "$SILENT_OUTPUT" = true ]; then
                run_cmd curl -fsSL https://deb.nodesource.com/setup_20.x \| bash - >> "$LOG_FILE" 2>&1
                run_cmd apt-get install -y -qq nodejs >> "$LOG_FILE" 2>&1
            else
                run_cmd curl -fsSL https://deb.nodesource.com/setup_20.x \| bash -
                run_cmd apt-get install -y nodejs
            fi
        fi
        if ! command -v npm >/dev/null 2>&1; then
            log error "Node.js installation failed, cannot build frontend."
            exit 1
        fi
        local node_arch
        node_arch=$(node -p "process.arch" 2>/dev/null || echo "unknown")
        if [ "$node_arch" = "arm64" ]; then
            log info "Node.js ARM64 version installed successfully"
        else
            log warn "Node.js architecture: $node_arch (expected arm64)"
        fi
    fi
    
    local npm_flags="--no-audit --no-fund --no-optional"
    local build_env="DISABLE_ESLINT_PLUGIN=true BROWSERSLIST_IGNORE_OLD_DATA=1 NODE_OPTIONS=--max-old-space-size=512"
    
    if [ "$SILENT_OUTPUT" = true ]; then
        ( cd "$PI_MON_DIR/frontend" && \
          run_cmd npm install "$npm_flags" --silent --loglevel=error --no-progress >> "$LOG_FILE" 2>&1 || {
              log error "npm install failed, check $LOG_FILE."
              exit 1
          } && \
          run_cmd env "$build_env" npm run -s build >> "$LOG_FILE" 2>&1 || {
              log error "npm build failed, check $LOG_FILE."
              exit 1
          } )
    else
        ( cd "$PI_MON_DIR/frontend" && \
          run_cmd npm install "$npm_flags" && \
          run_cmd env "$build_env" npm run build )
    fi
    
    run_cmd mkdir -p "$WEB_ROOT"
    run_cmd chown www-data:www-data "$WEB_ROOT"
    if command -v rsync >/dev/null 2>&1; then
        run_cmd rsync -a --delete "$PI_MON_DIR/frontend/build/" "$WEB_ROOT/"
    else
        run_cmd find "$WEB_ROOT" -mindepth 1 -delete
        run_cmd cp -r "$PI_MON_DIR/frontend/build/"* "$WEB_ROOT/"
    fi
    run_cmd chown -R www-data:www-data "$WEB_ROOT"
    
    local frontend_checksum
    frontend_checksum=$(generate_checksum "$PI_MON_DIR/frontend")
    echo "$frontend_checksum" > "$STATE_DIR/frontend.checksum"
    log info "Frontend checksum stored: $frontend_checksum"
}

# ----------------------------------------------------------------------------
# Nginx config
# ----------------------------------------------------------------------------
configure_nginx() {
    if [ "$SKIP_NGINX" = true ]; then return 0; fi
    if [ "$ONLY_TARGET" = "backend" ] || [ "$ONLY_TARGET" = "frontend" ] || [ "$ONLY_TARGET" = "verify" ]; then return 0; fi
    
    if [ ! -d "$WEB_ROOT" ]; then
        log error "Web root directory ($WEB_ROOT) does not exist."
        exit 1
    fi
    if ss -tuln | grep -q ":80 "; then
        log info "Port 80 is in use, checking for Nginx..."
        if systemctl is-active --quiet nginx; then
            log info "Stopping Nginx to reconfigure..."
            systemctl stop nginx
            sleep 2
        else
            log warn "Port 80 in use by unknown service, attempting to free it..."
            # Try to stop common web servers
            systemctl stop apache2 2>/dev/null || true
            systemctl stop lighttpd 2>/dev/null || true
            sleep 2
        fi
        
        # Check again
        if ss -tuln | grep -q ":80 "; then
            log error "Port 80 still in use after stopping services. Please check manually."
            exit 1
        fi
    fi
    if ss -tuln | grep -q ":${BACKEND_PORT} "; then
        log info "Backend port ${BACKEND_PORT} is in use, checking for existing service..."
        if systemctl is-active --quiet pi-monitor-backend.service; then
            log info "Stopping existing backend service to reconfigure..."
            systemctl stop pi-monitor-backend.service
            sleep 2
        else
            log warn "Port ${BACKEND_PORT} in use by unknown service, attempting to free it..."
            # Try to kill any process using the port
            local pid
            pid=$(ss -tuln | grep ":${BACKEND_PORT} " | awk '{print $7}' | cut -d'/' -f1 | head -1)
            if [ -n "$pid" ] && [ "$pid" != "-" ]; then
                log info "Killing process $pid using port ${BACKEND_PORT}..."
                kill "$pid" 2>/dev/null || true
                sleep 2
            fi
        fi
        
        # Check again
        if ss -tuln | grep -q ":${BACKEND_PORT} "; then
            log error "Backend port ${BACKEND_PORT} still in use after stopping services. Please check manually."
            exit 1
        fi
    fi
    
    log info "Configuring Nginx for domain $DOMAIN"
    if ! command -v nginx >/dev/null 2>&1; then
        run_cmd apt-get update -y
        run_cmd apt-get install -y nginx nginx-extras || log error "Nginx installation failed."
    fi
    if ! command -v nginx >/dev/null 2>&1; then
        log error "Nginx installation failed."
        exit 1
    fi
    
    log info "Applying Pi 5 Nginx optimizations"
    
    # Check if gzip is already enabled in main nginx.conf
    if grep -q "gzip on" /etc/nginx/nginx.conf 2>/dev/null; then
        log info "Gzip already enabled in main config, skipping duplicate settings"
        cat > /etc/nginx/conf.d/pi-monitor-optimizations.conf <<EOF
# Pi 5 specific Nginx optimizations for pi-monitor (gzip excluded - already enabled)
client_body_buffer_size 16k;
client_header_buffer_size 1k;
large_client_header_buffers 2 1k;

open_file_cache max=1000 inactive=20s;
open_file_cache_valid 30s;
open_file_cache_min_uses 2;
open_file_cache_errors on;

keepalive_timeout 65;
keepalive_requests 100;
client_max_body_size 10m;
EOF
    else
        log info "Adding complete Pi 5 Nginx optimizations including gzip"
        cat > /etc/nginx/conf.d/pi-monitor-optimizations.conf <<EOF
# Pi 5 specific Nginx optimizations for pi-monitor
client_body_buffer_size 16k;
client_header_buffer_size 1k;
large_client_header_buffers 2 1k;

gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

open_file_cache max=1000 inactive=20s;
open_file_cache_valid 30s;
open_file_cache_min_uses 2;
open_file_cache_errors on;

keepalive_timeout 65;
keepalive_requests 100;
client_max_body_size 10m;
EOF
    fi

    cat > "$NGINX_SITES_AVAILABLE/pi-monitor" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    root ${WEB_ROOT};
    index index.html;

    location / {
        try_files \$uri /index.html;
    }

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

    location /health {
        proxy_pass http://127.0.0.1:${BACKEND_PORT}/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

    run_cmd ln -sf "$NGINX_SITES_AVAILABLE/pi-monitor" "$NGINX_SITES_ENABLED/pi-monitor"
    if [ -L "$NGINX_SITES_ENABLED/default" ]; then run_cmd rm "$NGINX_SITES_ENABLED/default"; fi
    
    if [ "$SILENT_OUTPUT" = true ]; then
        run_cmd nginx -t >/dev/null 2>&1 || {
            nginx -t
            log error "Nginx configuration test failed."
            exit 1
        }
    else
        run_cmd nginx -t || log error "Nginx configuration test failed."
    fi
    run_cmd systemctl restart nginx
    
    # Verify Nginx started successfully
    if ! systemctl is-active --quiet nginx; then
        log error "Nginx failed to start after configuration"
        systemctl status nginx --no-pager -l || true
        exit 1
    fi
    
    log info "✓ Nginx started successfully with new configuration"
    
    local nginx_checksum
    nginx_checksum=$(generate_checksum "$NGINX_SITES_AVAILABLE/pi-monitor")
    echo "$nginx_checksum" > "$STATE_DIR/nginx.checksum"
    log info "Nginx checksum stored: $nginx_checksum"
    
    # Configure UFW
    if command -v ufw >/dev/null 2>&1; then
        log info "Configuring UFW to allow HTTP (80/tcp)"
        run_cmd ufw allow 80/tcp
        log info "Configuring UFW to allow HTTPS (443/tcp)"
        run_cmd ufw allow 443/tcp
    fi
}

# ----------------------------------------------------------------------------
# Verification
# ----------------------------------------------------------------------------
verify_stack() {
    if [ -n "$ONLY_TARGET" ] && [ "$ONLY_TARGET" != "verify" ]; then return 0; fi
    
    log info "Verifying services and Pi 5 optimizations"
    
    log info "=== Pi 5 System Verification ==="
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
    
    local mem_info
    mem_info=$(free -h 2>/dev/null | grep "Mem:" || echo "Memory info unavailable")
    log info "Memory Status: $mem_info"
    
    if id "$SYSTEM_USER" &>/dev/null; then
        local user_limits
        user_limits=$(ulimit -n 2>/dev/null || echo "unknown")
        log info "User file descriptor limit: $user_limits"
    fi
    
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
    
    if [ "$BACKEND_ACCESSIBLE" = false ]; then
        log error "Backend health check failed after retries"
        exit 1
    fi
    
    if ! systemctl is-active --quiet nginx; then
        log error "Nginx is not running"
        systemctl status nginx --no-pager -l || true
        exit 1
    fi
    
    if [ ! -f "$WEB_ROOT/index.html" ]; then
        log error "Frontend build output ($WEB_ROOT/index.html) is missing."
        exit 1
    fi
    
    for i in {1..3}; do
        if curl -fsS "http://localhost/" >/dev/null 2>&1; then
            break
        fi
        log warn "Frontend HTTP root check failed, retrying ($i/3)..."
        sleep 5
    done
    
    for i in {1..3}; do
        if curl -fsS "http://localhost/health" >/dev/null 2>&1; then
            break
        fi
        log warn "Nginx HTTP proxy to /health failed, retrying ($i/3)..."
        sleep 5
    done
    
    if ! curl -fsS "http://localhost/health" >/dev/null 2>&1; then
        log error "Nginx HTTP proxy to /health failed"
        exit 1
    fi
    
    if [ "$ENABLE_CLOUDFLARE" = true ]; then
        if systemctl is-active --quiet cloudflared; then
            log info "cloudflared service: active"
            local dns_records
            dns_records=$(dig +short A "$CF_HOSTNAME" 2>/dev/null || echo "")
            log info "DNS A records: $dns_records"
            if curl -fsS "https://$CF_HOSTNAME/health" >/dev/null 2>&1; then
                log info "Domain serving OK: https://$CF_HOSTNAME/health"
                if curl -I "https://$CF_HOSTNAME/health" 2>/dev/null | grep -q "CF-Ray"; then
                    log info "Cloudflare edge detected"
                    log info "Cloudflare CF-Ray present"
                fi
            else
                log warn "Domain not reachable (yet): https://$CF_HOSTNAME/health"
            fi
        else
            log error "cloudflared service not running"
            journalctl -u cloudflared -n 50 --no-pager || true
            exit 1
        fi
    fi
    
    log info "=== VERIFICATION COMPLETE ==="
}

# ----------------------------------------------------------------------------
# Main execution
# ----------------------------------------------------------------------------
pre_flight_checks
detect_system
optimize_pi5_system
ensure_user
check_checksums
setup_cloudflare
ensure_venv
setup_backend_service
build_frontend
configure_nginx
verify_stack

log info "deploy complete"