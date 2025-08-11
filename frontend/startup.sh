#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Debug: Show network info
echo "🔍 Network debugging info:"
echo "  - Container name: pi-monitor-backend"
echo "  - Target URL: http://pi-monitor-backend:5001/health"
echo "  - Current container: $(hostname)"

# Wait for backend to be ready (using exact container name)
until curl -f http://pi-monitor-backend:5001/health > /dev/null 2>&1; do
  echo "⏳ Backend not ready, waiting..."
  echo "🔍 Testing connection..."
  curl -v http://pi-monitor-backend:5001/health || echo "Connection failed"
  sleep 3
done

echo "✅ Backend is ready!"
echo "🚀 Starting nginx..."

# Start nginx
exec nginx -g "daemon off;"
