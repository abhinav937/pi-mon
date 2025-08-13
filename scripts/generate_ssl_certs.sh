#!/bin/bash
# Generate SSL certificates for Pi Monitor
# This script creates self-signed certificates for development/testing

set -e

echo "🔒 Generating SSL certificates for Pi Monitor..."

# Create certs directory
mkdir -p ../backend/certs

# Generate private key
echo "📝 Generating private key..."
openssl genrsa -out ../backend/certs/server.key 4096

# Generate certificate signing request
echo "📝 Generating certificate signing request..."
openssl req -new -key ../backend/certs/server.key -out ../backend/certs/server.csr -subj "/C=US/ST=State/L=City/O=PiMonitor/CN=localhost"

# Generate self-signed certificate
echo "📝 Generating self-signed certificate..."
openssl x509 -req -in ../backend/certs/server.csr -signkey ../backend/certs/server.key -out ../backend/certs/server.crt -days 365

# Set proper permissions
echo "🔐 Setting proper permissions..."
chmod 600 ../backend/certs/server.key
chmod 644 ../backend/certs/server.crt

# Clean up CSR file
rm ../backend/certs/server.csr

echo "✅ SSL certificates generated successfully!"
echo "📍 Certificate: ../backend/certs/server.crt"
echo "🔑 Private Key: ../backend/certs/server.key"
echo ""
echo "⚠️  Note: These are self-signed certificates for development/testing only."
echo "   For production, use certificates from a trusted Certificate Authority."
echo ""
echo "🚀 You can now run the secure server with:"
echo "   cd ../backend && python secure_server.py"
