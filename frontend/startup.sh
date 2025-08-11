#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Debug: Show network info
echo "🔍 Network debugging info:"
echo "  - Container name: pi-monitor-backend"
echo "  - Current container: $(hostname)"

# Try to find backend using common Docker network patterns
echo "🔍 Trying to connect to backend..."

# Try each address until one works (sh-compatible syntax)
BACKEND_IP=""
BACKEND_PORT="5001"

# Try pi-monitor-backend:5001
echo "🔍 Trying: pi-monitor-backend:5001"
if curl -f "http://pi-monitor-backend:5001/health" > /dev/null 2>&1; then
    echo "✅ Backend found at: pi-monitor-backend:5001"
    BACKEND_IP="pi-monitor-backend"
    BACKEND_PORT="5001"
else
    echo "❌ Failed to connect to: pi-monitor-backend:5001"
    
    # Try localhost:5001
    echo "🔍 Trying: localhost:5001"
    if curl -f "http://localhost:5001/health" > /dev/null 2>&1; then
        echo "✅ Backend found at: localhost:5001"
        BACKEND_IP="localhost"
        BACKEND_PORT="5001"
    else
        echo "❌ Failed to connect to: localhost:5001"
        
        # Try 127.0.0.1:5001
        echo "🔍 Trying: 127.0.0.1:5001"
        if curl -f "http://127.0.0.1:5001/health" > /dev/null 2>&1; then
            echo "✅ Backend found at: 127.0.0.1:5001"
            BACKEND_IP="127.0.0.1"
            BACKEND_PORT="5001"
        else
            echo "❌ Failed to connect to: 127.0.0.1:5001"
            
            # Try 172.20.0.2:5001
            echo "🔍 Trying: 172.20.0.2:5001"
            if curl -f "http://172.20.0.2:5001/health" > /dev/null 2>&1; then
                echo "✅ Backend found at: 172.20.0.2:5001"
                BACKEND_IP="172.20.0.2"
                BACKEND_PORT="5001"
            else
                echo "❌ Failed to connect to: 172.20.0.2:5001"
                
                # Try 172.20.0.3:5001
                echo "🔍 Trying: 172.20.0.3:5001"
                if curl -f "http://172.20.0.3:5001/health" > /dev/null 2>&1; then
                    echo "✅ Backend found at: 172.20.0.3:5001"
                    BACKEND_IP="172.20.0.3"
                    BACKEND_PORT="5001"
                else
                    echo "❌ Failed to connect to: 172.20.0.3:5001"
                    
                    # Default to localhost
                    echo "⚠️  No backend found, defaulting to localhost"
                    BACKEND_IP="localhost"
                    BACKEND_PORT="5001"
                fi
            fi
        fi
    fi
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
