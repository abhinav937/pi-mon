#!/bin/bash

# Comprehensive test script to check both port 80 (nginx proxy) and port 5001 (direct backend)
# This will help diagnose why the nginx proxy isn't working

BASE_URL="65.36.123.68"
echo "Testing API endpoints on both ports to diagnose nginx proxy issue"
echo "================================================================"

echo ""
echo "1. Testing DIRECT BACKEND ACCESS (Port 5001):"
echo "---------------------------------------------"

# Test health endpoint on port 5001
echo "Testing /health endpoint on port 5001..."
curl -s -w "Health (5001): %{http_code} - %{time_total}s\n" "http://$BASE_URL:5001/health"

# Test system endpoint on port 5001
echo "Testing /api/system/enhanced on port 5001..."
curl -s -w "System Enhanced (5001): %{http_code} - %{time_total}s\n" "http://$BASE_URL:5001/api/system/enhanced"

echo ""
echo "2. Testing NGINX PROXY (Port 80):"
echo "----------------------------------"

# Test health endpoint on port 80 (nginx proxy)
echo "Testing /health endpoint on port 80 (nginx proxy)..."
curl -s -w "Health (80): %{http_code} - %{time_total}s\n" "http://$BASE_URL/health"

# Test system endpoint on port 80 (nginx proxy)
echo "Testing /api/system/enhanced on port 80 (nginx proxy)..."
curl -s -w "System Enhanced (80): %{http_code} - %{time_total}s\n" "http://$BASE_URL/api/system/enhanced"

echo ""
echo "3. Testing NGINX PROXY with explicit port 80:"
echo "----------------------------------------------"

# Test health endpoint on explicit port 80
echo "Testing /health endpoint on explicit port 80..."
curl -s -w "Health (80 explicit): %{http_code} - %{time_total}s\n" "http://$BASE_URL:80/health"

# Test system endpoint on explicit port 80
echo "Testing /api/system/enhanced on explicit port 80..."
curl -s -w "System Enhanced (80 explicit): %{http_code} - %{time_total}s\n" "http://$BASE_URL:80/api/system/enhanced"

echo ""
echo "4. Testing Connection Details:"
echo "------------------------------"

# Test if port 80 is listening
echo "Testing if port 80 is listening..."
nc -z -w5 $BASE_URL 80
if [ $? -eq 0 ]; then
    echo "✅ Port 80 is open and listening"
else
    echo "❌ Port 80 is not accessible"
fi

# Test if port 5001 is listening
echo "Testing if port 5001 is listening..."
nc -z -w5 $BASE_URL 5001
if [ $? -eq 0 ]; then
    echo "✅ Port 5001 is open and listening"
else
    echo "❌ Port 5001 is not accessible"
fi

echo ""
echo "5. Testing with verbose curl for port 80:"
echo "------------------------------------------"

# Test with verbose output to see what's happening
echo "Testing /health on port 80 with verbose output..."
curl -v "http://$BASE_URL/health" 2>&1 | head -20

echo ""
echo "================================================================"
echo "Analysis:"
echo "- If port 5001 works but port 80 doesn't: nginx proxy issue"
echo "- If both ports fail: backend or network issue"
echo "- If port 80 is not listening: nginx not running"
echo ""
echo "Next steps:"
echo "1. Check if nginx is running: sudo systemctl status nginx"
echo "2. Check nginx error logs: sudo tail -f /var/log/nginx/error.log"
echo "3. Test nginx config: sudo nginx -t"
echo "4. Reload nginx: sudo systemctl reload nginx"
