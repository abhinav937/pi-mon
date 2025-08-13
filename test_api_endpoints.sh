#!/bin/bash

# Test script to verify all API endpoints work through nginx proxy
# This script tests the endpoints without specifying the port number

BASE_URL="http://65.36.123.68"
echo "Testing API endpoints through nginx proxy at $BASE_URL"
echo "=================================================="

# Test health endpoint
echo "Testing /health endpoint..."
curl -s -o /dev/null -w "Health: %{http_code}\n" "$BASE_URL/health"

# Test system endpoints
echo "Testing /api/system endpoint..."
curl -s -o /dev/null -w "System: %{http_code}\n" "$BASE_URL/api/system"

echo "Testing /api/system/enhanced endpoint..."
curl -s -o /dev/null -w "System Enhanced: %{http_code}\n" "$BASE_URL/api/system/enhanced"

echo "Testing /api/system/info endpoint..."
curl -s -o /dev/null -w "System Info: %{http_code}\n" "$BASE_URL/api/system/info"

# Test metrics endpoints
echo "Testing /api/metrics endpoint..."
curl -s -o /dev/null -w "Metrics: %{http_code}\n" "$BASE_URL/api/metrics"

# Test services endpoints
echo "Testing /api/services endpoint..."
curl -s -o /dev/null -w "Services: %{http_code}\n" "$BASE_URL/api/services"

# Test power endpoints
echo "Testing /api/power endpoint..."
curl -s -o /dev/null -w "Power: %{http_code}\n" "$BASE_URL/api/power"

# Test network endpoints
echo "Testing /api/network endpoint..."
curl -s -o /dev/null -w "Network: %{http_code}\n" "$BASE_URL/api/network"

# Test logs endpoints
echo "Testing /api/logs endpoint..."
curl -s -o /dev/null -w "Logs: %{http_code}\n" "$BASE_URL/api/logs"

echo "=================================================="
echo "All endpoints tested. Check the HTTP status codes above."
echo "200 = Success, 404 = Not Found, 500 = Server Error"
