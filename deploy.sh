#!/usr/bin/env bash
# Pi Monitor - Robust Deployment Script (HTTP Only)
# Simplified and robust deployment for Pi Monitor system

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="pi.cabhinav.com"
STATIC_IP="65.36.123.68"
WEB_ROOT="/var/www/pi-monitor"
NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"
PRODUCTION_URL="http://65.36.123.68"
PI_MON_DIR="/home/abhinav/pi-mon"
VENV_DIR="$PI_MON_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/pi-monitor-backend.service"

# Port configuration
PUBLIC_PORT="80"
NGINX_PORT="80"
BACKEND_PORT="5001"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ "$EUID" -ne 0 ]]; then
        log_error "This script must be run with sudo"
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update package list
    apt-get update -y
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-venv \
        python3-pip \
        nginx \
        curl \
        wget \
        git \
        nodejs \
        npm
    
    log_success "System dependencies installed"
}

# Create user if it doesn't exist
create_user() {
    if ! id "abhinav" &>/dev/null; then
        log_info "Creating user 'abhinav'..."
        
        # Create group if it doesn't exist
        if ! getent group "abhinav" &>/dev/null; then
            groupadd abhinav
        fi
        
        # Create user with home directory
        useradd -m -g abhinav -s /bin/bash abhinav
        
        # Set default password
        echo "abhinav:raspberry" | chpasswd
        
        log_success "User 'abhinav' created"
    else
        log_info "User 'abhinav' already exists"
    fi
}

# Setup project directory
setup_project_directory() {
    log_info "Setting up project directory..."
    
    # Create pi-mon directory if it doesn't exist
    if [ ! -d "$PI_MON_DIR" ]; then
        mkdir -p "$PI_MON_DIR"
        chown abhinav:abhinav "$PI_MON_DIR"
        log_success "Created project directory: $PI_MON_DIR"
    else
        log_info "Project directory already exists"
    fi
    
    # Copy project files if we're not already in the target directory
    if [ "$SCRIPT_DIR" != "$PI_MON_DIR" ]; then
        log_info "Copying project files..."
        cp -r "$SCRIPT_DIR"/* "$PI_MON_DIR/"
        chown -R abhinav:abhinav "$PI_MON_DIR"
        log_success "Project files copied"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    log_info "Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        # Create virtual environment as abhinav user
        sudo -u abhinav python3 -m venv "$VENV_DIR"
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Upgrade pip and install requirements
    log_info "Installing Python dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    
    if [ -f "$PI_MON_DIR/backend/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$PI_MON_DIR/backend/requirements.txt"
        log_success "Python dependencies installed"
    else
        log_error "requirements.txt not found at $PI_MON_DIR/backend/requirements.txt"
        exit 1
    fi
}

# Setup backend service
setup_backend_service() {
    log_info "Setting up backend service..."
    
    # Create systemd service file
    cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Pi Monitor Backend Service
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
ExecStart=$VENV_DIR/bin/python $PI_MON_DIR/backend/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pi-monitor

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$PI_MON_DIR

# Auto-restart on failure
StartLimitInterval=60
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

    # Create .env file if it doesn't exist
    if [ ! -f "$PI_MON_DIR/backend/.env" ]; then
        cat > "$PI_MON_DIR/backend/.env" <<EOF
# Environment for Pi Monitor backend
PI_MONITOR_API_KEY=pi-monitor-api-key-2024
PI_MONITOR_ENV=production
PI_MONITOR_PRODUCTION_URL=$PRODUCTION_URL
EOF
        chown abhinav:abhinav "$PI_MON_DIR/backend/.env"
        log_success "Backend .env file created"
    fi
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable pi-monitor-backend.service
    
    log_success "Backend service configured"
}

# Build frontend
build_frontend() {
    log_info "Building frontend..."
    
    cd "$PI_MON_DIR/frontend"
    
    # Create production environment file
    cat > ".env.production" <<EOF
# Production Environment Configuration
REACT_APP_SERVER_URL=$PRODUCTION_URL
REACT_APP_API_BASE_URL=$PRODUCTION_URL
REACT_APP_ENVIRONMENT=production
REACT_APP_BACKEND_PORT=$BACKEND_PORT
REACT_APP_FRONTEND_PORT=$NGINX_PORT
EOF
    
    # Install dependencies and build
    npm install --no-audit --no-fund
    npm run build
    
    # Deploy to web root
    mkdir -p "$WEB_ROOT"
    cp -r build/* "$WEB_ROOT/"
    chown -R www-data:www-data "$WEB_ROOT"
    
    cd "$SCRIPT_DIR"
    log_success "Frontend built and deployed"
}

# Setup Nginx
setup_nginx() {
    log_info "Setting up Nginx..."
    
    # Copy nginx configuration
    if [ -f "$PI_MON_DIR/nginx/pi-subdomain.conf" ]; then
        cp "$PI_MON_DIR/nginx/pi-subdomain.conf" "$NGINX_SITES_AVAILABLE/$DOMAIN"
    else
        # Create fallback configuration
        cat > "$NGINX_SITES_AVAILABLE/$DOMAIN" <<EOF
server {
    listen 80;
    server_name $DOMAIN $STATIC_IP;

    root $WEB_ROOT;
    index index.html;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # React Router - serve index.html for app routes
    location / {
        try_files \$uri /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With";
    }

    # Health check endpoint
    location = /health {
        proxy_pass http://127.0.0.1:5001/health;
        proxy_http_version 1.0;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection close;
    }

    # Static file caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files \$uri =404;
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
}
EOF
    fi
    
    # Enable site
    ln -sf "$NGINX_SITES_AVAILABLE/$DOMAIN" "$NGINX_SITES_ENABLED/$DOMAIN"
    
    # Remove default site if it exists
    if [ -L "$NGINX_SITES_ENABLED/default" ]; then
        rm "$NGINX_SITES_ENABLED/default"
    fi
    
    # Test nginx configuration
    if nginx -t; then
        log_success "Nginx configuration is valid"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
    
    # Enable and start nginx
    systemctl enable nginx
    systemctl restart nginx
    
    log_success "Nginx configured and started"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Start backend service
    systemctl start pi-monitor-backend.service
    sleep 3
    
    # Check if backend service is running
    if systemctl is-active --quiet pi-monitor-backend.service; then
        log_success "Backend service is running"
    else
        log_error "Backend service failed to start"
        systemctl status pi-monitor-backend.service --no-pager -l
        exit 1
    fi
    
    # Ensure nginx is running
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx is not running"
        systemctl status nginx --no-pager -l
        exit 1
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check backend health
    if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
        log_success "Backend health check passed"
    else
        log_error "Backend health check failed"
        exit 1
    fi
    
    # Check frontend through nginx
    if curl -fsS http://localhost/ &>/dev/null; then
        log_success "Frontend is accessible"
    else
        log_warn "Frontend test failed (may be starting up)"
    fi
    
    # Check if services are enabled for auto-start
    if systemctl is-enabled --quiet pi-monitor-backend.service; then
        log_success "Backend service is enabled for auto-start"
    else
        systemctl enable pi-monitor-backend.service
        log_success "Backend service enabled for auto-start"
    fi
    
    if systemctl is-enabled --quiet nginx; then
        log_success "Nginx is enabled for auto-start"
    else
        systemctl enable nginx
        log_success "Nginx enabled for auto-start"
    fi
    
    log_success "Deployment verification completed"
}

# Main deployment function
main() {
    log_info "Starting Pi Monitor deployment..."
    
    check_root
    install_dependencies
    create_user
    setup_project_directory
    setup_python_env
    setup_backend_service
    build_frontend
    setup_nginx
    start_services
    verify_deployment
    
    log_success "Pi Monitor deployment completed successfully!"
    log_info "Access your Pi Monitor at: $PRODUCTION_URL"
    log_info "Backend API: $PRODUCTION_URL/api/"
    log_info "Health check: $PRODUCTION_URL/health"
}

# Run main function
main "$@"
