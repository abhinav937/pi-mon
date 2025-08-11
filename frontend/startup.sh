#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Debug: Show network info
echo "🔍 Network debugging info:"
echo "  - Using host networking"
echo "  - Current container: $(hostname)"

# Since we're using host networking, backend should be available at localhost:5001
echo "🔍 Testing backend connection..."
BACKEND_IP="localhost"
BACKEND_PORT="5001"

echo "🎯 Using backend at: $BACKEND_IP:$BACKEND_PORT"

# Update nginx configuration with the backend address
echo "🔧 Updating nginx configuration..."
sed -i "s/server localhost:5001;/server $BACKEND_IP:$BACKEND_PORT;/" /etc/nginx/nginx.conf
echo "✅ Nginx config updated with backend: $BACKEND_IP:$BACKEND_PORT"

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
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
