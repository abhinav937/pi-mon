#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Debug: Show network info
echo "🔍 Network debugging info:"
echo "  - Container name: pi-monitor-backend"
echo "  - Current container: $(hostname)"

# Try to get backend IP address
echo "🔍 Discovering backend IP address..."
BACKEND_IP=""

# Method 1: Try to get IP from Docker network
if command -v getent >/dev/null 2>&1; then
    BACKEND_IP=$(getent hosts pi-monitor-backend | awk '{ print $1 }')
    echo "  - Method 1 (getent): $BACKEND_IP"
fi

# Method 2: Try to get IP from nslookup
if [ -z "$BACKEND_IP" ] && command -v nslookup >/dev/null 2>&1; then
    BACKEND_IP=$(nslookup pi-monitor-backend 2>/dev/null | grep 'Address:' | tail -1 | awk '{print $2}')
    echo "  - Method 2 (nslookup): $BACKEND_IP"
fi

# Method 3: Try to get IP from ping
if [ -z "$BACKEND_IP" ] && command -v ping >/dev/null 2>&1; then
    BACKEND_IP=$(ping -c 1 pi-monitor-backend 2>/dev/null | grep PING | sed 's/.*(\([^)]*\)).*/\1/')
    echo "  - Method 3 (ping): $BACKEND_IP"
fi

# Method 4: Use localhost if all else fails (assuming host networking or port mapping)
if [ -z "$BACKEND_IP" ]; then
    echo "⚠️  Could not resolve backend hostname, trying localhost..."
    BACKEND_IP="localhost"
fi

echo "🎯 Using backend at: $BACKEND_IP:5001"

# Update nginx configuration with the discovered backend IP
echo "🔧 Updating nginx configuration..."
sed -i "s/server localhost:5001;/server $BACKEND_IP:5001;/" /etc/nginx/nginx.conf
echo "✅ Nginx config updated with backend IP: $BACKEND_IP"

# Wait for backend to be ready
until curl -f http://$BACKEND_IP:5001/health > /dev/null 2>&1; do
  echo "⏳ Backend not ready, waiting..."
  echo "🔍 Testing connection to $BACKEND_IP:5001..."
  curl -v http://$BACKEND_IP:5001/health || echo "Connection failed"
  sleep 3
done

echo "✅ Backend is ready!"
echo "🚀 Starting nginx..."

# Start nginx
exec nginx -g "daemon off;"
