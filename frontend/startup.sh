#!/bin/sh

echo "🚀 Pi Monitor Frontend Starting..."
echo "⏳ Waiting for backend to be available..."

# Debug: Show network info
echo "🔍 Network debugging info:"
echo "  - Container name: pi-monitor-backend"
echo "  - Current container: $(hostname)"

# Show network interfaces and routing
echo "🔍 Network interfaces:"
ip addr show 2>/dev/null || ifconfig 2>/dev/null || echo "No network tools available"

echo "🔍 Routing table:"
ip route show 2>/dev/null || route -n 2>/dev/null || echo "No routing tools available"

echo "🔍 DNS resolution test:"
nslookup pi-monitor-backend 2>/dev/null || echo "nslookup not available"

# Try to find backend using common Docker network patterns
echo "🔍 Trying to connect to backend..."

# Try each address until one works (sh-compatible syntax)
BACKEND_IP=""
BACKEND_PORT="5001"

# Function to test connection with timeout
test_connection() {
    local address=$1
    local timeout=5
    echo "🔍 Testing: $address (timeout: ${timeout}s)"
    
    # Use timeout command if available, otherwise use curl's built-in timeout
    if command -v timeout >/dev/null 2>&1; then
        timeout $timeout curl -f "http://$address/health" > /dev/null 2>&1
    else
        curl -f --connect-timeout $timeout --max-time $timeout "http://$address/health" > /dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ Backend found at: $address"
        return 0
    else
        echo "❌ Failed to connect to: $address"
        return 1
    fi
}

# Try pi-monitor-backend:5001
if test_connection "pi-monitor-backend:5001"; then
    BACKEND_IP="pi-monitor-backend"
    BACKEND_PORT="5001"
else
    # Try localhost:5001
    if test_connection "localhost:5001"; then
        BACKEND_IP="localhost"
        BACKEND_PORT="5001"
    else
        # Try 127.0.0.1:5001
        if test_connection "127.0.0.1:5001"; then
            BACKEND_IP="127.0.0.1"
            BACKEND_PORT="5001"
        else
            # Try 172.20.0.2:5001
            if test_connection "172.20.0.2:5001"; then
                BACKEND_IP="172.20.0.2"
                BACKEND_PORT="5001"
            else
                # Try 172.20.0.3:5001
                if test_connection "172.20.0.3:5001"; then
                    BACKEND_IP="172.20.0.3"
                    BACKEND_PORT="5001"
                else
                    # Try 172.20.0.4:5001
                    if test_connection "172.20.0.4:5001"; then
                        BACKEND_IP="172.20.0.4"
                        BACKEND_PORT="5001"
                    else
                        # Try 172.20.0.5:5001
                        if test_connection "172.20.0.5:5001"; then
                            BACKEND_IP="172.20.0.5"
                            BACKEND_PORT="5001"
                        else
                            # Default to localhost
                            echo "⚠️  No backend found, defaulting to localhost"
                            BACKEND_IP="localhost"
                            BACKEND_PORT="5001"
                        fi
                    fi
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
echo "⏳ Waiting for backend to be ready..."
until test_connection "$BACKEND_IP:$BACKEND_PORT"; do
  echo "⏳ Backend not ready, waiting..."
  sleep 3
done

echo "✅ Backend is ready!"
echo "🚀 Starting nginx..."

# Start nginx
exec nginx -g "daemon off;"
