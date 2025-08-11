#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Wait for backend to be ready (using explicit network alias)
until curl -f http://backend:5001/health > /dev/null 2>&1; do
  echo "⏳ Backend not ready, waiting..."
  sleep 3
done

echo "✅ Backend is ready!"
echo "🚀 Starting nginx..."

# Start nginx
exec nginx -g "daemon off;"
