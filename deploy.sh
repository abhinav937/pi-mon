#!/usr/bin/env bash
# Pi Monitor - Smart Deployment Script (efficient, state-aware)
# Only sets up what's missing or needs updating

set -euo pipefail

BLUE=''
GREEN=''
YELLOW=''
RED=''
NC=''

# Configuration
DOMAIN="pi.cabhinav.com"
STATIC_IP="65.36.123.68"
WEB_ROOT="/var/www/pi-monitor"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
PRODUCTION_URL="https://65.36.123.68"  # Changed to HTTPS
PI_MON_DIR="/home/abhinav/pi-mon"
VENV_DIR="$PI_MON_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"
STATE_DIR="$PI_MON_DIR/.deploy_state"

# Port configuration
PUBLIC_PORT="443"  # HTTPS port for external access
NGINX_PORT="443"   # HTTPS port for Nginx
BACKEND_PORT="5001" # HTTP port for backend (internal)

# Security configuration
SSL_ENABLED=true
SSL_CERT_DIR="$PI_MON_DIR/backend/certs"
SSL_CERT_FILE="$SSL_CERT_DIR/server.crt"
SSL_KEY_FILE="$SSL_CERT_DIR/server.key"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if running as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: This script must be run with sudo"
  exit 1
fi

# Quiet mode: suppress stdout. Use FD 3 for minimal notices (version updates), stderr for errors.
exec 3>&1
exec 1>/dev/null

# =============================================================================
# 1. CHECK CURRENT STATE
# =============================================================================
echo "Checking state..." >&3
# Check if user exists
USER_EXISTS=false
if id "abhinav" &>/dev/null; then
    :
    USER_EXISTS=true
else
    echo "WARN: User 'abhinav' does not exist" >&2
fi

# Ensure deploy state directory exists
mkdir -p "$STATE_DIR"
chown abhinav:abhinav "$STATE_DIR"

# Determine if frontend needs rebuild based on version bump
NEED_FRONTEND_BUILD=false
SOURCE_FRONTEND_VERSION=""
DEPLOYED_FRONTEND_VERSION=""
FRONTEND_PRESENT=false
FRONTEND_CHECKSUM_FILE="$STATE_DIR/frontend_checksum"
CURRENT_FRONTEND_CHECKSUM=""
FRONTEND_ENV_SIG_FILE="$STATE_DIR/frontend_env_sig"
CURRENT_FRONTEND_ENV_SIG=""
BACKEND_VERSION_FILE="$STATE_DIR/backend_version"
SOURCE_BACKEND_VERSION=""

if [ -f "$PI_MON_DIR/frontend/public/version.json" ]; then
    # Parse version without jq
    SOURCE_FRONTEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$PI_MON_DIR/frontend/public/version.json" | head -n1)
fi

# Backend version from config.json (if present)
if [ -f "$PI_MON_DIR/config.json" ]; then
    SOURCE_BACKEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$PI_MON_DIR/config.json" | head -n1)
fi

# Fallback to package.json if public version.json not present
if [ -z "$SOURCE_FRONTEND_VERSION" ] && [ -f "$PI_MON_DIR/frontend/package.json" ]; then
    SOURCE_FRONTEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$PI_MON_DIR/frontend/package.json" | head -n1)
fi

if [ -f "$WEB_ROOT/version.json" ]; then
    DEPLOYED_FRONTEND_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"\n]*\)".*/\1/p' "$WEB_ROOT/version.json" | head -n1)
fi

# Compute checksum of frontend sources to detect changes independent of version
if [ -d "$PI_MON_DIR/frontend" ]; then
    CURRENT_FRONTEND_CHECKSUM=$(find "$PI_MON_DIR/frontend" \
        -path "$PI_MON_DIR/frontend/node_modules" -prune -o \
        -path "$PI_MON_DIR/frontend/build" -prune -o \
        -type f \( -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.css" -o -name "*.json" -o -name "*.html" -o -name "*.config.js" -o -name "postcss.config.js" -o -name "tailwind.config.js" -o -name "package.json" \) -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
fi

# Compute frontend env signature (values embedded at build time)
CURRENT_FRONTEND_ENV_SIG=$(printf "%s|%s|%s" "$PRODUCTION_URL" "$BACKEND_PORT" "$NGINX_PORT" | sha256sum | awk '{print $1}')

if [ -f "$WEB_ROOT/index.html" ]; then
    FRONTEND_PRESENT=true
fi

if [ "$FRONTEND_PRESENT" = false ]; then
	NEED_FRONTEND_BUILD=true
elif [ -n "$SOURCE_FRONTEND_VERSION" ] && [ -n "$DEPLOYED_FRONTEND_VERSION" ] && [ "$SOURCE_FRONTEND_VERSION" != "$DEPLOYED_FRONTEND_VERSION" ]; then
    echo "UPDATE: Frontend version $DEPLOYED_FRONTEND_VERSION -> $SOURCE_FRONTEND_VERSION" >&3
	NEED_FRONTEND_BUILD=true
elif [ -n "$SOURCE_FRONTEND_VERSION" ] && [ -z "$DEPLOYED_FRONTEND_VERSION" ]; then
    echo "UPDATE: Frontend version file missing; building $SOURCE_FRONTEND_VERSION" >&3
    NEED_FRONTEND_BUILD=true
elif [ -n "$CURRENT_FRONTEND_CHECKSUM" ]; then
    if [ -f "$FRONTEND_CHECKSUM_FILE" ]; then
        PREV_FRONTEND_CHECKSUM=$(cat "$FRONTEND_CHECKSUM_FILE" 2>/dev/null || true)
        if [ "$CURRENT_FRONTEND_CHECKSUM" != "$PREV_FRONTEND_CHECKSUM" ]; then
            echo "UPDATE: Frontend source changes detected (checksum)" >&3
            NEED_FRONTEND_BUILD=true
        fi
    else
        # First-time record
        NEED_FRONTEND_BUILD=true
    fi
fi

# If env signature changed, require rebuild
if [ -n "$CURRENT_FRONTEND_ENV_SIG" ]; then
    if [ -f "$FRONTEND_ENV_SIG_FILE" ]; then
        PREV_FRONTEND_ENV_SIG=$(cat "$FRONTEND_ENV_SIG_FILE" 2>/dev/null || true)
        if [ "$CURRENT_FRONTEND_ENV_SIG" != "$PREV_FRONTEND_ENV_SIG" ]; then
            echo "UPDATE: Frontend environment changed; rebuild required" >&3
            NEED_FRONTEND_BUILD=true
        fi
    else
        NEED_FRONTEND_BUILD=true
    fi
fi

# Determine if backend changed using checksum
NEED_BACKEND_RESTART=false
BACKEND_CHECKSUM_FILE="$STATE_DIR/backend_checksum"
CURRENT_BACKEND_CHECKSUM=""

if [ -d "$PI_MON_DIR/backend" ]; then
    # Compute checksum over backend Python sources and requirements
    CURRENT_BACKEND_CHECKSUM=$(find "$PI_MON_DIR/backend" -type f \
        \( -name "*.py" -o -name "requirements.txt" -o -name "*.sh" \) -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
    if [ -n "$CURRENT_BACKEND_CHECKSUM" ]; then
        if [ -f "$BACKEND_CHECKSUM_FILE" ]; then
            PREV_BACKEND_CHECKSUM=$(cat "$BACKEND_CHECKSUM_FILE" 2>/dev/null || true)
            if [ "$CURRENT_BACKEND_CHECKSUM" != "$PREV_BACKEND_CHECKSUM" ]; then
                echo "UPDATE: Backend changes detected (checksum)" >&3
                NEED_BACKEND_RESTART=true
            fi
        else
            # First-time record
            NEED_BACKEND_RESTART=true
        fi
    fi
fi

# If backend version changed (from config.json), note and force restart
if [ -n "$SOURCE_BACKEND_VERSION" ]; then
    if [ -f "$BACKEND_VERSION_FILE" ]; then
        PREV_BACKEND_VERSION=$(cat "$BACKEND_VERSION_FILE" 2>/dev/null || true)
        if [ "$SOURCE_BACKEND_VERSION" != "$PREV_BACKEND_VERSION" ]; then
            echo "UPDATE: Backend version $PREV_BACKEND_VERSION -> $SOURCE_BACKEND_VERSION" >&3
            NEED_BACKEND_RESTART=true
        fi
    else
        # First-time: write later after restart
        :
    fi
fi

# Check if pi-mon directory exists
PI_MON_EXISTS=false
if [ -d "$PI_MON_DIR" ]; then
    echo -e "${GREEN}✅ Pi-mon directory exists: $PI_MON_DIR${NC}"
    PI_MON_EXISTS=true
else
    echo -e "${YELLOW}⚠️  Pi-mon directory does not exist${NC}"
fi

# Check if virtual environment exists and is working
VENV_EXISTS=false
if [ -f "$VENV_DIR/bin/python" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${GREEN}✅ Virtual environment exists: $VENV_DIR${NC}"
    VENV_EXISTS=true
    
    # Test if venv Python works
    if "$VENV_DIR/bin/python" -c "import sys; print('Python version:', sys.version)" &>/dev/null; then
        echo -e "${GREEN}✅ Virtual environment Python is working${NC}"
    else
        echo -e "${RED}❌ Virtual environment Python is broken${NC}"
        VENV_EXISTS=false
    fi
else
    echo -e "${YELLOW}⚠️  Virtual environment does not exist or is broken${NC}"
fi

# Check if backend service exists and is configured
SERVICE_EXISTS=false
SERVICE_RUNNING=false
if [ -f "$SERVICE_FILE" ]; then
    echo -e "${GREEN}✅ Backend service file exists${NC}"
    SERVICE_EXISTS=true
    
    # Check if service is running
    if systemctl is-active --quiet pi-monitor-backend.service; then
        echo -e "${GREEN}✅ Backend service is running${NC}"
        SERVICE_RUNNING=true
    else
        echo -e "${YELLOW}⚠️  Backend service exists but is not running${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Backend service file does not exist${NC}"
fi

# Check if Nginx is configured
NGINX_CONFIGURED=false
if [ -f "$NGINX_SITES_AVAILABLE/$DOMAIN" ] && [ -L "$NGINX_SITES_ENABLED/$DOMAIN" ]; then
    NGINX_CONFIGURED=true
fi

# Check if frontend is built
FRONTEND_BUILT=false
if [ -f "$WEB_ROOT/index.html" ]; then
    FRONTEND_BUILT=true
fi

# Check if backend is accessible
BACKEND_ACCESSIBLE=false
if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
    BACKEND_ACCESSIBLE=true
fi

# Check SSL certificate status
SSL_CERT_EXISTS=false
if [ -f "$SSL_CERT_FILE" ] && [ -f "$SSL_KEY_FILE" ]; then
    SSL_CERT_EXISTS=true
    echo -e "${GREEN}✅ SSL certificates found${NC}"
else
    echo -e "${YELLOW}⚠️  SSL certificates not found${NC}"
fi

# =============================================================================
# 2. CREATE USER AND DIRECTORY (if needed)
# =============================================================================
if [ "$USER_EXISTS" = false ]; then
    echo -e "\n${BLUE}👤 Creating user 'abhinav'...${NC}"
    
    # Create group 'abhinav' if it doesn't exist
    if ! getent group "abhinav" &>/dev/null; then
        echo "Creating group 'abhinav'..."
        groupadd abhinav
    fi
    
    # Create user 'abhinav' with home directory
    echo "Creating user 'abhinav'..."
    useradd -m -g abhinav -s /bin/bash abhinav
    
    # Set a default password (you can change this later)
    echo "abhinav:raspberry" | chpasswd
    
    echo -e "${GREEN}✅ User 'abhinav' created successfully${NC}"
fi

if [ "$PI_MON_EXISTS" = false ]; then
    echo -e "\n${BLUE}📁 Creating pi-mon directory...${NC}"
    mkdir -p "$PI_MON_DIR"
    chown abhinav:abhinav "$PI_MON_DIR"
    echo -e "${GREEN}✅ Pi-mon directory created${NC}"
fi

# =============================================================================
# 2.1 SETUP SSL CERTIFICATES (if needed)
# =============================================================================
if [ "$SSL_CERT_EXISTS" = false ] && [ "$SSL_ENABLED" = true ]; then
    echo -e "\n${BLUE}🔒 Setting up SSL certificates...${NC}"
    
    # Install OpenSSL if not available
    if ! command -v openssl &>/dev/null; then
        echo "Installing OpenSSL..."
        apt-get update -y
        apt-get install -y openssl
    fi
    
    # Create certs directory
    mkdir -p "$SSL_CERT_DIR"
    chown abhinav:abhinav "$SSL_CERT_DIR"
    
    # Generate self-signed certificate
    echo "Generating self-signed SSL certificate..."
    cd "$SSL_CERT_DIR"
    
    # Generate private key
    openssl genrsa -out server.key 4096
    
    # Generate certificate signing request
    openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=PiMonitor/CN=$DOMAIN"
    
    # Generate self-signed certificate
    openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365
    
    # Set proper permissions
    chmod 600 server.key
    chmod 644 server.crt
    
    # Clean up CSR file
    rm server.csr
    
    # Set ownership
    chown abhinav:abhinav server.key server.crt
    
    echo -e "${GREEN}✅ SSL certificates generated successfully${NC}"
    
    cd "$SCRIPT_DIR"
fi

# =============================================================================
# 3. SETUP VIRTUAL ENVIRONMENT (if needed)
# =============================================================================
if [ "$VENV_EXISTS" = false ]; then
    echo -e "\n${BLUE}🐍 Setting up Python virtual environment...${NC}"
    
    # Install Python venv if not available
    if ! command -v python3 &>/dev/null; then
        echo "Installing Python3..."
        apt-get update -y
        apt-get install -y python3 python3-venv python3-pip
    fi
    
    # Create virtual environment
    sudo -u abhinav python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    
    # Install requirements
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        echo "Installing Python dependencies..."
        "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt"
        echo -e "${GREEN}✅ Virtual environment setup complete${NC}"
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        exit 1
    fi
else
    echo -e "\n${BLUE}🔄 Updating virtual environment dependencies...${NC}"
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade
        echo -e "${GREEN}✅ Dependencies updated${NC}"
    fi
fi

# =============================================================================
# 4. SETUP BACKEND SERVICE (if needed or broken)
# =============================================================================
if [ "$SERVICE_EXISTS" = false ] || [ "$SERVICE_RUNNING" = false ]; then
    echo -e "\n${BLUE}🔧 Setting up backend service...${NC}"
    
    # Create proper service file
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pi Monitor Secure Backend Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=abhinav
Group=abhinav
WorkingDirectory=$PI_MON_DIR/backend
Environment=PYTHONUNBUFFERED=1
Environment=PI_MONITOR_ENV=production
Environment=PI_MONITOR_PRODUCTION_URL=$PRODUCTION_URL
Environment=PI_MONITOR_SSL_ENABLED=$SSL_ENABLED
Environment=PI_MONITOR_SSL_CERT_FILE=$SSL_CERT_FILE
Environment=PI_MONITOR_SSL_KEY_FILE=$SSL_KEY_FILE
EnvironmentFile=$PI_MON_DIR/backend/.env
ExecStart=$VENV_DIR/bin/python $PI_MON_DIR/backend/secure_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-monitor-secure

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$PI_MON_DIR/backend $PI_MON_DIR $SSL_CERT_DIR

# Auto-restart on failure
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

    # Create .env file if it doesn't exist
    if [ ! -f "$PI_MON_DIR/backend/.env" ]; then
        cat > "$PI_MON_DIR/backend/.env" <<EOF
# Environment for Pi Monitor secure backend
PI_MONITOR_API_KEY=pi-monitor-api-key-2024
PI_MONITOR_ENV=production
PI_MONITOR_PRODUCTION_URL=$PRODUCTION_URL
PI_MONITOR_SSL_ENABLED=$SSL_ENABLED
PI_MONITOR_SSL_CERT_FILE=$SSL_CERT_FILE
PI_MONITOR_SSL_KEY_FILE=$SSL_KEY_FILE
EOF
        chown abhinav:abhinav "$PI_MON_DIR/backend/.env"
    fi

    # Create security configuration if it doesn't exist
    if [ ! -f "$PI_MON_DIR/backend/security_config.json" ]; then
        cat > "$PI_MON_DIR/backend/security_config.json" <<EOF
{
  "ssl": {
    "enabled": $SSL_ENABLED,
    "cert_file": "$SSL_CERT_FILE",
    "key_file": "$SSL_KEY_FILE",
    "verify_mode": "none",
    "check_hostname": false
  },
  "security_headers": {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
  },
  "rate_limiting": {
    "enabled": true,
    "max_requests": 100,
    "window_seconds": 60,
    "burst_limit": 20
  },
  "authentication": {
    "enabled": true,
    "session_timeout": 3600,
    "max_login_attempts": 5,
    "lockout_duration": 900,
    "require_https": true
  }
}
EOF
        chown abhinav:abhinav "$PI_MON_DIR/backend/security_config.json"
    fi

    # Reload systemd and start service
    systemctl daemon-reload
    systemctl enable pi-monitor-backend.service
    
    if [ "$SERVICE_RUNNING" = false ]; then
        echo "Starting backend service..."
        systemctl start pi-monitor-backend.service
        sleep 3
        
        # Check if service started successfully
        if systemctl is-active --quiet pi-monitor-backend.service; then
            echo "Backend service started" >&3
        else
            echo "ERROR: Backend service failed to start" >&2
            systemctl status pi-monitor-backend.service
            exit 1
        fi
    fi
else
    :
fi

# =============================================================================
# 4.1 APPLY BACKEND UPDATES IF CHANGED
# =============================================================================
if [ "$NEED_BACKEND_RESTART" = true ]; then
    echo "UPDATE: Restarting backend (changes detected)" >&3
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        echo "Updating Python dependencies (if needed)..."
        "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt" --upgrade
    fi
    echo "Restarting backend service..."
    systemctl restart pi-monitor-backend.service || true
    sleep 3
    if systemctl is-active --quiet pi-monitor-backend.service; then
        echo "Backend service restarted" >&3
        echo "$CURRENT_BACKEND_CHECKSUM" > "$BACKEND_CHECKSUM_FILE"
        chown abhinav:abhinav "$BACKEND_CHECKSUM_FILE"
        if [ -n "$SOURCE_BACKEND_VERSION" ]; then
            echo "$SOURCE_BACKEND_VERSION" > "$BACKEND_VERSION_FILE"
            chown abhinav:abhinav "$BACKEND_VERSION_FILE"
        fi
    else
        echo "ERROR: Backend service failed to restart" >&2
        systemctl status pi-monitor-backend.service --no-pager -l || true
        journalctl -u pi-monitor-backend.service --no-pager -n 20 || true
        exit 1
    fi
else
    if [ -n "$SOURCE_BACKEND_VERSION" ]; then
        echo "OK: Backend up-to-date (version $SOURCE_BACKEND_VERSION)" >&3
    else
        echo "OK: Backend up-to-date" >&3
    fi
fi

# =============================================================================
# 5. BUILD FRONTEND (if needed)
# =============================================================================
if [ "$NEED_FRONTEND_BUILD" = true ]; then
    echo "UPDATE: Building frontend" >&3
    
    # Install Node.js if not available
    if ! command -v npm &>/dev/null; then
        echo "Installing Node.js and npm..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
    fi
    
    # Create production environment file
    cat > "$PI_MON_DIR/frontend/.env.production" <<EOF
# Production Environment Configuration
REACT_APP_SERVER_URL=$PRODUCTION_URL
REACT_APP_API_BASE_URL=$PRODUCTION_URL
REACT_APP_ENVIRONMENT=production
REACT_APP_BACKEND_PORT=$BACKEND_PORT
REACT_APP_FRONTEND_PORT=$NGINX_PORT
REACT_APP_HTTPS_ENABLED=$SSL_ENABLED
REACT_APP_INTERNAL_BACKEND_URL=http://127.0.0.1:$BACKEND_PORT
EOF
    
    # Build frontend
    cd "$PI_MON_DIR/frontend"
    npm install --no-audit --no-fund
    npm run build
    
    # Deploy to web root
    mkdir -p "$WEB_ROOT"
    cp -r build/* "$WEB_ROOT/"
    chown -R www-data:www-data "$WEB_ROOT"
    
    cd "$SCRIPT_DIR"
    echo "Frontend built and deployed" >&3
    # Persist frontend checksum if available
    if [ -n "$CURRENT_FRONTEND_CHECKSUM" ]; then
        echo "$CURRENT_FRONTEND_CHECKSUM" > "$FRONTEND_CHECKSUM_FILE"
        chown abhinav:abhinav "$FRONTEND_CHECKSUM_FILE"
    fi
    if [ -n "$CURRENT_FRONTEND_ENV_SIG" ]; then
        echo "$CURRENT_FRONTEND_ENV_SIG" > "$FRONTEND_ENV_SIG_FILE"
        chown abhinav:abhinav "$FRONTEND_ENV_SIG_FILE"
    fi
else
    DISPLAY_FRONTEND_VERSION="$DEPLOYED_FRONTEND_VERSION"
    if [ -z "$DISPLAY_FRONTEND_VERSION" ]; then DISPLAY_FRONTEND_VERSION="$SOURCE_FRONTEND_VERSION"; fi
    if [ -n "$DISPLAY_FRONTEND_VERSION" ]; then
        echo "OK: Frontend up-to-date (version $DISPLAY_FRONTEND_VERSION)" >&3
    else
        echo "OK: Frontend up-to-date" >&3
    fi
fi

# =============================================================================
# 6. SETUP NGINX (if needed)
# =============================================================================
if [ "$NGINX_CONFIGURED" = false ]; then
    echo "Setting up Nginx..." >&3
    
    # Install Nginx if not available
    if ! command -v nginx &>/dev/null; then
        echo "Installing Nginx..."
        apt-get update -y
        apt-get install -y nginx
    fi
    
    # Copy Nginx configuration
    if [ -f "$PI_MON_DIR/nginx/pi-subdomain.conf" ]; then
        cp "$PI_MON_DIR/nginx/pi-subdomain.conf" "$NGINX_SITES_AVAILABLE/$DOMAIN"
    else
        # Fallback configuration with HTTPS support
        cat > "$NGINX_SITES_AVAILABLE/$DOMAIN" <<EOF
server {
  listen 80;
  server_name $DOMAIN;
  return 301 https://\$server_name\$request_uri;
}

server {
  listen 443 ssl http2;
  server_name $DOMAIN;

  ssl_certificate $SSL_CERT_FILE;
  ssl_certificate_key $SSL_KEY_FILE;
  
  # SSL configuration
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
  ssl_prefer_server_ciphers off;
  ssl_session_cache shared:SSL:10m;
  ssl_session_timeout 10m;

  root $WEB_ROOT;
  index index.html;

  # Security headers
  add_header X-Content-Type-Options nosniff;
  add_header X-Frame-Options DENY;
  add_header X-XSS-Protection "1; mode=block";
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

  location / {
    try_files \$uri /index.html;
  }

  location /api/ {
    proxy_pass http://127.0.0.1:5001/api/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
  }

  location /health {
    proxy_pass http://127.0.0.1:5001/health;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
  }
}
EOF
    fi
    
    # Enable site
    ln -sf "$NGINX_SITES_AVAILABLE/$DOMAIN" "$NGINX_SITES_ENABLED/$DOMAIN"
    
    # Remove default site
    if [ -L "$NGINX_SITES_ENABLED/default" ]; then
        rm "$NGINX_SITES_ENABLED/default"
    fi
    
    # Test and restart Nginx
    nginx -t
    systemctl restart nginx
    echo "Nginx configured and started" >&3
else
    :
fi

# =============================================================================
# 7. FINAL VERIFICATION
# =============================================================================
echo "Verifying..." >&3
sleep 5

# Check backend service
if systemctl is-active --quiet pi-monitor-backend.service; then
    :
else
    echo "ERROR: Backend service is not running" >&2
    echo "Service status:" >&2
    systemctl status pi-monitor-backend.service --no-pager -l
    echo "Recent logs:" >&2
    journalctl -u pi-monitor-backend.service --no-pager -n 10
    echo "ERROR: Backend service failed to start properly" >&2
    exit 1
fi

# Check backend health
echo "Checking backend health..." >&3
if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
    :
else
    echo "ERROR: Backend health check failed" >&2
    echo "Checking what's happening on port 5001..." >&2
    if netstat -tlnp 2>/dev/null | grep :5001; then
        echo "WARN: Port 5001 is listening but health check failed" >&2
    else
        echo "ERROR: Port 5001 is not listening" >&2
    fi
    exit 1
fi

# Check Nginx
echo "Checking Nginx..." >&3
if systemctl is-active --quiet nginx; then
    :
else
    echo "ERROR: Nginx is not running" >&2
    systemctl status nginx --no-pager -l
    exit 1
fi

# Check frontend
echo "Testing frontend..." >&3
if curl -fsS -k https://localhost/ &>/dev/null; then
    :
else
    echo "WARN: Frontend test failed (may be starting)" >&2
    echo "Checking Nginx configuration..." >&2
    nginx -t
fi

# Check all services are properly configured
echo "Checking service enablement..." >&3

# Check if service is enabled
if systemctl is-enabled --quiet pi-monitor-backend.service; then
    :
else
    echo "WARN: Backend service is not enabled" >&2
    systemctl enable pi-monitor-backend.service
    echo "Backend service now enabled" >&3
fi

# Check if Nginx is enabled
if systemctl is-enabled --quiet nginx; then
    :
else
    echo "WARN: Nginx is not enabled" >&2
    systemctl enable nginx
    echo "Nginx now enabled" >&3
fi

# Final comprehensive test
echo "Running API checks..." >&3

# Prepare auth header from .env if available
API_KEY=""
if [ -f "$PI_MON_DIR/backend/.env" ]; then
    API_KEY=$(grep -E '^PI_MONITOR_API_KEY=' "$PI_MON_DIR/backend/.env" | cut -d'=' -f2 | tr -d '\r')
fi
AUTH_HEADER=""
if [ -n "$API_KEY" ]; then
    AUTH_HEADER="Authorization: Bearer $API_KEY"
fi

# Test API endpoints (use auth where required)
:
ENDPOINTS=("/health" "/api/system" "/api/metrics/history?minutes=5" "/api/metrics/database")
for endpoint in "${ENDPOINTS[@]}"; do
    if [ "$endpoint" = "/health" ]; then
        if curl -fsS "http://127.0.0.1:5001$endpoint" &>/dev/null; then
            :
        else
            echo "ERROR: $endpoint failed" >&2
        fi
    else
        if [ -n "$AUTH_HEADER" ]; then
            if curl -fsS -H "$AUTH_HEADER" "http://127.0.0.1:5001$endpoint" &>/dev/null; then
                :
            else
                echo "ERROR: $endpoint failed" >&2
            fi
        else
            echo "WARN: Skipping $endpoint (no API key available)" >&2
        fi
    fi
done

# Test Nginx proxy to health
echo "Checking Nginx proxy..." >&3
if curl -fsS -k "https://localhost/health" &>/dev/null; then :; else echo "ERROR: Nginx proxy to /health failed" >&2; fi

# Check system resources
:

# Success summary
echo "Done." >&3
