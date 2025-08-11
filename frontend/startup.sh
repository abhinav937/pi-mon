#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Debug: Show network info
echo "🔍 Network debugging info:"
echo "  - Container name: pi-monitor-backend"
echo "  - Current container: $(hostname)"

# Try to find backend using common Docker network patterns
echo "🔍 Trying to connect to backend..."

# List of possible backend addresses to try
BACKEND_ADDRESSES=(
    "pi-monitor-backend:5001"
    "localhost:5001"
    "127.0.0.1:5001"
    "172.20.0.2:5001"
    "172.20.0.3:5001"
    "172.20.0.4:5001"
    "172.20.0.5:5001"
)

BACKEND_IP=""
BACKEND_PORT="5001"

# Try each address until one works
for address in "${BACKEND_ADDRESSES[@]}"; do
    echo "🔍 Trying: $address"
    if curl -f "http://$address/health" > /dev/null 2>&1; then
        echo "✅ Backend found at: $address"
        # Extract IP and port
        if [[ $address == *":"* ]]; then
            BACKEND_IP=$(echo $address | cut -d: -f1)
            BACKEND_PORT=$(echo $address | cut -d: -f2)
        else
            BACKEND_IP=$address
        fi
        break
    else
        echo "❌ Failed to connect to: $address"
    fi
done

# If no address worked, default to localhost
if [ -z "$BACKEND_IP" ]; then
    echo "⚠️  No backend found, defaulting to localhost"
    BACKEND_IP="localhost"
    BACKEND_PORT="5001"
fi

echo "🎯 Using backend at: $BACKEND_IP:$BACKEND_PORT"

# Update nginx configuration with the discovered backend IP
echo "🔧 Updating nginx configuration..."
sed -i "s/server localhost:5001;/server $BACKEND_IP:$BACKEND_PORT;/" /etc/nginx/nginx.conf
echo "✅ Nginx config updated with backend: $BACKEND_IP:$BACKEND_PORT"

# Wait for backend to be ready
until curl -f "http://$BACKEND_IP:$BACKEND_PORT/health" > /dev/null 2>&1; do
  echo "⏳ Backend not ready, waiting..."
  echo "🔍 Testing connection to $BACKEND_IP:$BACKEND_PORT..."
  curl -v "http://$BACKEND_IP:$BACKEND_PORT/health" || echo "Connection failed"
  sleep 3
done

echo "✅ Backend is ready!"
echo "🚀 Starting nginx..."

# Start nginx
exec nginx -g "daemon off;"
