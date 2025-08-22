#!/bin/bash
set -euo pipefail

# ----------------------------------------------------------------------------
# Color and logging (unchanged)
# ----------------------------------------------------------------------------
if [ -t 1 ] && [ "${NO_COLOR:-false}" = false ]; then
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

LOG_LEVEL_NUM=$(_level_value "${LOG_LEVEL:-info}")

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
    if [ "${NO_COLOR:-false}" = true ]; then color=""; text=""; reset=""; fi
    printf "%b[%s] %-5s%b %b%s%b\n" "$color" "$ts" "$tag" "$reset" "$text" "$*" "$reset" >&2
    if [ -w "${LOG_FILE:-}" ]; then
        echo "[$ts] $tag $*" >> "$LOG_FILE" 2>/dev/null
    fi
}

# Defaults (unchanged except for SILENT_OUTPUT)
# ----------------------------------------------------------------------------
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
ENABLE_CLOUDFLARE=false
CF_HOSTNAME=""
CF_TUNNEL_NAME="pi-monitor"
CF_TOKEN=""
LOG_LEVEL="info"
NO_COLOR=false
DRY_RUN=false
ONLY_TARGET=""
SKIP_FRONTEND=false
SKIP_BACKEND=false
FORCE_FRONTEND=false
FORCE_BACKEND=false
SILENT_OUTPUT=true # Default to silent for cleaner output
SHOW_CONFIG=false
NEED_FRONTEND_BUILD=false
TEST_CHECKSUMS=false

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -n "$PI_MON_DIR" ] || PI_MON_DIR="$SCRIPT_DIR"
[ -n "$SYSTEM_USER" ] || SYSTEM_USER="${SUDO_USER:-$(id -un)}"
CONFIG_FILE="$PI_MON_DIR/config.json"
[ -n "$VENV_DIR" ] || VENV_DIR="$PI_MON_DIR/.venv"
[ -n "$STATE_DIR" ] || STATE_DIR="$PI_MON_DIR/.deploy_state"

# Ensure state directory and log file are writable
mkdir -p "$STATE_DIR" || { log error "Cannot create state directory $STATE_DIR."; exit 1; }
chown "$SYSTEM_USER":"$SYSTEM_USER" "$STATE_DIR"
LOG_FILE="$STATE_DIR/deploy.log"
touch "$LOG_FILE" || { log error "Cannot create log file $LOG_FILE."; exit 1; }
chmod 664 "$LOG_FILE"
chown "$SYSTEM_USER":"$SYSTEM_USER" "$LOG_FILE"

# Load configurations (unchanged)
# ----------------------------------------------------------------------------
command -v jq >/dev/null || {
    log info "Installing jq for JSON processing"
    apt update
    apt install jq -y
}
if [ -f "$CONFIG_FILE" ]; then
    DOMAIN=${DOMAIN:-$(jq -r '.deployment_defaults.domain // "pi.cabhinav.com"' "$CONFIG_FILE")}
    API_KEY=${API_KEY:-$(jq -r '.deployment_defaults.api_key // "pi-monitor-api-key-2024"' "$CONFIG_FILE")}
    ENV=${ENV:-$(jq -r '.deployment_defaults.env // "production"' "$CONFIG_FILE")}
    BACKEND_PORT=${BACKEND_PORT:-$(jq -r '.deployment_defaults.backend_port // "5001"' "$CONFIG_FILE")}
    ENABLE_CLOUDFLARE=$(jq -r '.cloudflare.enable // false' "$CONFIG_FILE")
    CF_HOSTNAME=$(jq -r '.cloudflare.hostname // ""' "$CONFIG_FILE")
    CF_TUNNEL_NAME=$(jq -r '.cloudflare.tunnel_name // "pi-monitor"' "$CONFIG_FILE")
    CF_TOKEN=$(jq -r '.cloudflare.token // ""' "$CONFIG_FILE")
else
    DOMAIN=${DOMAIN:-"pi.cabhinav.com"}
    API_KEY=${API_KEY:-"pi-monitor-api-key-2024"}
    ENV=${ENV:-"production"}
    BACKEND_PORT=${BACKEND_PORT:-"5001"}
fi
if [ -n "$CF_HOSTNAME" ]; then
    DOMAIN="$CF_HOSTNAME"
fi

# Utility functions (unchanged)
# ----------------------------------------------------------------------------
run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        log debug "DRY-RUN: $*"
    else
        log debug "EXEC: $*"
        "$@"
    fi
}

wait_for_space_to_skip() {
    local timeout="${1:-5}"
    local key=""
    if [ -e /dev/tty ]; then
        if IFS= read -r -s -n 1 -t "$timeout" key < /dev/tty; then
            [ "$key" = " " ] && return 0
        fi
    else
        if IFS= read -r -s -n 1 -t "$timeout" key 2>/dev/null; then
            [ "$key" = " " ] && return 0
        fi
    fi
    return 1
}

# System detection and optimization (unchanged)
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
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors ]; then
        local available_govs
        available_govs=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors)
        if echo "$available_govs" | grep -q "performance"; then
            log info "Setting CPU governor to performance mode"
            run_cmd echo performance \| tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor >/dev/null 2>&1
        fi
    fi
    if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        temp=$(cat /sys/class/thermal/thermal_zone0/temp)
        temp=$((temp / 1000))
        if [ "$temp" -gt 80 ]; then
            log warn "High CPU temperature ($temp°C), risk of thermal throttling."
        fi
    fi
    cat > /etc/security/limits.d/pi-monitor.conf <<EOF
${SYSTEM_USER} soft nofile 65536
${SYSTEM_USER} hard nofile 65536
${SYSTEM_USER} soft nproc 4096
${SYSTEM_USER} hard nproc 4096
www-data soft nofile 65536
www-data hard nofile 65536
EOF
    log info "Pi 5 optimizations applied"
}

# Pre-flight checks (unchanged)
# ----------------------------------------------------------------------------
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
    if [ "$available_space" -lt 1048576 ]; then
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

# Modified functions
# ----------------------------------------------------------------------------
ensure_venv() {
    if [ "$SKIP_BACKEND" = true ]; then return 0; fi
    if [ "$VENV_EXISTS" = false ]; then
        log info "Setting up Python venv at $VENV_DIR"
        if ! command -v python3 >/dev/null 2>&1; then
            log info "Installing Python 3.11 for Raspberry Pi 5"
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
        run_cmd "$VENV_DIR/bin/pip" install -q --upgrade pip "$PIP_FLAGS" >> "$LOG_FILE" 2>&1 || {
            log error "pip upgrade failed, check $LOG_FILE."
            exit 1
        }
    fi
    if [ ! -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        log warn "requirements.txt missing, installing default dependencies."
        run_cmd "$VENV_DIR/bin/pip" install -q psutil==5.9.6 "$PIP_FLAGS" >> "$LOG_FILE" 2>&1 || {
            log error "Failed to install default dependencies, check $LOG_FILE."
            exit 1
        }
    else
        log info "Installing/updating backend dependencies"
        if ! "$VENV_DIR/bin/pip" install -q -r "$PI_MON_DIR/backend/requirements.txt" --upgrade "$PIP_FLAGS" >> "$LOG_FILE" 2>&1; then
            log error "pip install failed, check $LOG_FILE for details."
            exit 1
        fi
    fi
}

setup_backend_service() {
    if [ "$SKIP_BACKEND" = true ]; then return 0; fi
    if [ ! -f "$PI_MON_DIR/backend/start_service.py" ]; then
        log error "Backend service script ($PI_MON_DIR/backend/start_service.py) is missing."
        exit 1
    fi
    # Validate start_service.py
    if ! "$VENV_DIR/bin/python" -m py_compile "$PI_MON_DIR/backend/start_service.py" >/dev/null 2>&1; then
        log error "Syntax error in start_service.py. Please fix the script."
        exit 1
    fi
    if systemctl is-active --quiet pi-monitor-backend.service; then
        log info "Stopping backend service to update configuration..."
        run_cmd systemctl stop pi-monitor-backend.service
        sleep 2
    fi
    log info "Configuring backend .env"
    cat > "$PI_MON_DIR/backend/.env" <<EOF
PI_MONITOR_API_KEY=$API_KEY
PI_MONITOR_ENV=$ENV
EOF
    run_cmd chown "$SYSTEM_USER":"$SYSTEM_USER" "$PI_MON_DIR/backend/.env"
    run_cmd chmod u+rw "$PI_MON_DIR/backend/.env"
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
MemoryMax=512M
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
    if ! grep -q "ExecStart=${VENV_DIR}/bin/python ${PI_MON_DIR}/backend/start_service.py" "$SERVICE_FILE"; then
        log error "Service file configuration is incorrect"
        exit 1
    fi
    log info "Service file configured"
    run_cmd systemctl daemon-reload
    run_cmd systemctl enable pi-monitor-backend.service
    log info "Starting backend service..."
    run_cmd systemctl start pi-monitor-backend.service
    sleep 5
    if ! systemctl is-active --quiet pi-monitor-backend.service; then
        log error "Backend service failed to start. Check logs with: journalctl -u pi-monitor-backend -n 50"
        systemctl status pi-monitor-backend.service --no-pager -l || true
        exit 1
    fi
    local backend_checksum
    backend_checksum=$(generate_checksum "$PI_MON_DIR/backend")
    echo "$backend_checksum" > "$STATE_DIR/backend.checksum"
    log info "Backend deployed"
}

setup_cloudflare() {
    if [ "$ENABLE_CLOUDFLARE" = true ]; then
        log info "Setting up Cloudflare tunnel..."
        if ! command -v cloudflared >/dev/null 2>&1; then
            log info "Installing cloudflared..."
            run_cmd wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O /usr/local/bin/cloudflared
            run_cmd chmod +x /usr/local/bin/cloudflared
        fi
        if ! command -v cloudflared >/dev/null 2>&1; then
            log error "Failed to install cloudflared."
            exit 1
        fi
        if [ ${#CF_TOKEN} -lt 50 ]; then
            log error "Invalid Cloudflare token format."
            exit 1
        fi
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
        log info "Starting Cloudflare tunnel..."
        run_cmd systemctl daemon-reload
        run_cmd systemctl enable cloudflared
        systemctl stop cloudflared >/dev/null 2>&1 || true
        run_cmd systemctl start cloudflared
        if systemctl is-active --quiet cloudflared; then
            log info "Cloudflared service started"
        else
            log error "Cloudflared service failed to start. Check: journalctl -u cloudflared"
            exit 1
        fi
        log info "Waiting for tunnel connection (may take 10-15 minutes)..."
        for i in {1..3}; do
            if curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
                log info "Local tunnel endpoint responding"
                break
            else
                log warn "Local tunnel endpoint not responding, retrying ($i/3)..."
                if wait_for_space_to_skip 10; then
                    log info "Skipping tunnel check"
                    break
                fi
                sleep 10
            fi
        done
        if ! curl -fsS "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
            log warn "Local tunnel endpoint not responding. Check after 10-15 minutes:"
            log info "  - Tunnel status: journalctl -u cloudflared -n 50"
            log info "  - Local health: curl http://127.0.0.1:${BACKEND_PORT}/health"
            log info "  - Domain: curl https://$CF_HOSTNAME/health"
        fi
        log info "Cloudflare tunnel setup completed"
    fi
}

# Main execution (modified to streamline flow and ensure backend is up before tunnel)
# ----------------------------------------------------------------------------
log info "Starting deployment..."
pre_flight_checks
detect_system
optimize_pi5_system
ensure_user
check_checksums
ensure_venv
setup_backend_service
setup_cloudflare
build_frontend
configure_reverse_proxy
verify_stack
log info "Deployment completed successfully"