#!/bin/bash
# Fix Pi Monitor Deployment Issues
# This script resolves common deployment problems

set -e

echo "🔧 Fixing Pi Monitor deployment issues..."

# Configuration
PI_MON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PI_MON_DIR/backend"
CERTS_DIR="$BACKEND_DIR/certs"

# Check if running as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
    echo "❌ This script must be run with sudo"
    exit 1
fi

echo "📍 Pi-mon directory: $PI_MON_DIR"

# 1. Check and fix SSL certificates
echo "🔒 Checking SSL certificates..."
if [ ! -f "$CERTS_DIR/server.crt" ] || [ ! -f "$CERTS_DIR/server.key" ]; then
    echo "📝 SSL certificates missing, generating them..."
    
    # Install OpenSSL if not available
    if ! command -v openssl &>/dev/null; then
        echo "📦 Installing OpenSSL..."
        apt-get update -y
        apt-get install -y openssl
    fi
    
    # Create certs directory
    mkdir -p "$CERTS_DIR"
    
    # Generate self-signed certificate
    cd "$CERTS_DIR"
    
    echo "🔑 Generating private key..."
    openssl genrsa -out server.key 4096
    
    echo "📄 Generating certificate signing request..."
    openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=PiMonitor/CN=localhost"
    
    echo "📜 Generating self-signed certificate..."
    openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365
    
    # Set proper permissions
    chmod 600 server.key
    chmod 644 server.crt
    
    # Clean up CSR file
    rm server.csr
    
    # Set ownership
    chown abhinav:abhinav server.key server.crt
    
    echo "✅ SSL certificates generated successfully"
    cd "$PI_MON_DIR"
else
    echo "✅ SSL certificates exist"
fi

# 2. Check backend service
echo "🔍 Checking backend service..."
if systemctl is-active --quiet pi-monitor-backend.service; then
    echo "✅ Backend service is running"
else
    echo "⚠️  Backend service is not running, starting it..."
    systemctl start pi-monitor-backend.service
    sleep 3
    
    if systemctl is-active --quiet pi-monitor-backend.service; then
        echo "✅ Backend service started successfully"
    else
        echo "❌ Backend service failed to start"
        systemctl status pi-monitor-backend.service
        exit 1
    fi
fi

# 3. Test backend connectivity
echo "🧪 Testing backend connectivity..."
if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
    echo "Checking backend logs..."
    journalctl -u pi-monitor-backend.service --no-pager -n 10
    exit 1
fi

# 4. Check Nginx configuration
echo "🌐 Checking Nginx configuration..."
if nginx -t &>/dev/null; then
    echo "✅ Nginx configuration is valid"
else
    echo "❌ Nginx configuration has errors"
    nginx -t
    exit 1
fi

# 5. Restart Nginx
echo "🔄 Restarting Nginx..."
systemctl restart nginx
sleep 2

if systemctl is-active --quiet nginx; then
    echo "✅ Nginx restarted successfully"
else
    echo "❌ Nginx failed to restart"
    systemctl status nginx
    exit 1
fi

# 6. Test frontend connectivity
echo "🧪 Testing frontend connectivity..."
if curl -fsS -k https://localhost/ &>/dev/null; then
    echo "✅ Frontend HTTPS access working"
else
    echo "⚠️  Frontend HTTPS access failed, trying HTTP..."
    if curl -fsS http://localhost/ &>/dev/null; then
        echo "✅ Frontend HTTP access working"
    else
        echo "❌ Frontend access failed"
    fi
fi

# 7. Test API proxy
echo "🧪 Testing API proxy..."
if curl -fsS -k https://localhost/health &>/dev/null; then
    echo "✅ API proxy working via HTTPS"
else
    echo "⚠️  API proxy failed via HTTPS, trying HTTP..."
    if curl -fsS http://localhost/health &>/dev/null; then
        echo "✅ API proxy working via HTTP"
    else
        echo "❌ API proxy failed"
    fi
fi

# 8. Show current status
echo ""
echo "📊 Current Deployment Status:"
echo "=============================="
echo "🔒 SSL Certificates: $(if [ -f "$CERTS_DIR/server.crt" ]; then echo "✅ Present"; else echo "❌ Missing"; fi)"
echo "🐍 Backend Service: $(if systemctl is-active --quiet pi-monitor-backend.service; then echo "✅ Running"; else echo "❌ Stopped"; fi)"
echo "🌐 Nginx Service: $(if systemctl is-active --quiet nginx; then echo "✅ Running"; else echo "❌ Stopped"; fi)"
echo "🔍 Backend Health: $(if curl -fsS http://127.0.0.1:5001/health &>/dev/null; then echo "✅ OK"; else echo "❌ Failed"; fi)"
echo "🌐 Frontend Access: $(if curl -fsS -k https://localhost/ &>/dev/null 2>/dev/null; then echo "✅ HTTPS OK"; elif curl -fsS http://localhost/ &>/dev/null 2>/dev/null; then echo "⚠️  HTTP OK"; else echo "❌ Failed"; fi)"
echo "🔌 API Proxy: $(if curl -fsS -k https://localhost/health &>/dev/null 2>/dev/null; then echo "✅ HTTPS OK"; elif curl -fsS http://localhost/health &>/dev/null 2>/dev/null; then echo "⚠️  HTTP OK"; else echo "❌ Failed"; fi)"

echo ""
echo "🎯 Access URLs:"
echo "  Backend API: http://127.0.0.1:5001"
echo "  Frontend (HTTPS): https://localhost"
echo "  Frontend (HTTP): http://localhost"
echo "  Health Check: https://localhost/health"

echo ""
echo "🔧 If issues persist, check:"
echo "  - Backend logs: journalctl -u pi-monitor-backend.service -f"
echo "  - Nginx logs: tail -f /var/log/nginx/error.log"
echo "  - SSL certificates: ls -la $CERTS_DIR/"
echo "  - Service status: systemctl status pi-monitor-backend.service"

echo ""
echo "✅ Deployment fix completed!"
