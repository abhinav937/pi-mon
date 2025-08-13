#!/bin/bash
# Deploy Secure Pi Monitor with SSL
# This script sets up the secure HTTPS server with SSL certificates

set -e

echo "🔒 Deploying Secure Pi Monitor..."

# Configuration
PI_MON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PI_MON_DIR/backend"
CERTS_DIR="$BACKEND_DIR/certs"

# Check if running as root or with sudo
if [[ "$EUID" -ne 0 ]]; then
    echo "❌ This script must be run with sudo"
    exit 1
fi

# Check if pi-mon directory exists
if [ ! -d "$PI_MON_DIR" ]; then
    echo "❌ Pi-mon directory not found: $PI_MON_DIR"
    exit 1
fi

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Backend directory not found: $BACKEND_DIR"
    exit 1
fi

echo "📍 Pi-mon directory: $PI_MON_DIR"
echo "📍 Backend directory: $BACKEND_DIR"

# 1. Generate SSL certificates if they don't exist
echo "🔒 Setting up SSL certificates..."
if [ ! -f "$CERTS_DIR/server.crt" ] || [ ! -f "$CERTS_DIR/server.key" ]; then
    echo "📝 Generating SSL certificates..."
    
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
    
    echo "✅ SSL certificates generated successfully"
else
    echo "✅ SSL certificates already exist"
fi

# 2. Install Python dependencies
echo "🐍 Installing Python dependencies..."
if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    cd "$BACKEND_DIR"
    
    # Check if virtual environment exists
    if [ -d ".venv" ]; then
        echo "🔄 Using existing virtual environment"
        source .venv/bin/activate
    else
        echo "📦 Creating virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
    fi
    
    echo "📦 Installing requirements..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Dependencies installed"
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# 3. Create security configuration
echo "⚙️ Setting up security configuration..."
SECURITY_CONFIG="$BACKEND_DIR/security_config.json"

if [ ! -f "$SECURITY_CONFIG" ]; then
    echo "📝 Creating security configuration..."
    cat > "$SECURITY_CONFIG" <<EOF
{
  "ssl": {
    "enabled": true,
    "cert_file": "certs/server.crt",
    "key_file": "certs/server.key",
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
    echo "✅ Security configuration created"
else
    echo "✅ Security configuration already exists"
fi

# 4. Test the secure server
echo "🧪 Testing secure server..."
cd "$BACKEND_DIR"

# Check if secure_server.py exists
if [ ! -f "secure_server.py" ]; then
    echo "❌ secure_server.py not found"
    exit 1
fi

# Test Python imports
echo "🔍 Testing Python imports..."
python3 -c "
try:
    import ssl
    import security_config
    import security_middleware
    print('✅ All security modules imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# 5. Show deployment summary
echo ""
echo "🎉 Secure Pi Monitor deployment complete!"
echo ""
echo "📁 Files created/updated:"
echo "  📄 SSL Certificate: $CERTS_DIR/server.crt"
echo "  🔑 Private Key: $CERTS_DIR/server.key"
echo "  ⚙️  Security Config: $SECURITY_CONFIG"
echo ""
echo "🚀 To run the secure server:"
echo "  cd $BACKEND_DIR"
echo "  python3 secure_server.py"
echo ""
echo "🔒 Security features enabled:"
echo "  ✅ HTTPS/SSL encryption"
echo "  ✅ Security headers"
echo "  ✅ Rate limiting"
echo "  ✅ Threat detection"
echo "  ✅ Input validation"
echo ""
echo "⚠️  Note: This uses self-signed certificates for development/testing."
echo "   For production, use certificates from a trusted Certificate Authority."
echo ""
echo "🌐 The server will be accessible at:"
echo "  https://localhost:5001 (or your configured port)"
echo ""
echo "📚 For more information, see: SECURITY_README.md"
