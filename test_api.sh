#!/bin/bash

# Pi-Monitor API Test Script
# Tests all backend endpoints to identify issues

# Configuration
SERVER_HOST="192.168.0.201"
SERVER_PORT_5000="5000"
SERVER_PORT_5001="5001"
BASE_URL_5000="http://${SERVER_HOST}:${SERVER_PORT_5000}"
BASE_URL_5001="http://${SERVER_HOST}:${SERVER_PORT_5001}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
echo "Using server: $SERVER_HOST"

echo -e "${BLUE}=== Pi-Monitor Backend API Testing ===${NC}"
echo "Testing both port 5000 and 5001..."
echo

# Simple test function
test_simple() {
    local description=$1
    local curl_cmd=$2
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "Command: $curl_cmd"
    echo "Response:"
    eval $curl_cmd
    echo -e "\n${BLUE}---${NC}\n"
}

# Determine which port is working
echo -e "${BLUE}1. Testing Basic Connectivity${NC}"
if curl -s --connect-timeout 5 "$BASE_URL_5001/health" > /dev/null 2>&1; then
    BASE_URL=$BASE_URL_5001
    WORKING_PORT=5001
    echo -e "${GREEN}Port 5001 is responding - using this for tests${NC}"
elif curl -s --connect-timeout 5 "$BASE_URL_5000/health" > /dev/null 2>&1; then
    BASE_URL=$BASE_URL_5000
    WORKING_PORT=5000
    echo -e "${GREEN}Port 5000 is responding - using this for tests${NC}"
else
    echo -e "${RED}Neither port 5000 nor 5001 is responding!${NC}"
    echo "Make sure the backend server is running."
    exit 1
fi

test_simple "Health Check" "curl -i '$BASE_URL/health'"

# Get authentication token
echo -e "${BLUE}2. Testing Authentication${NC}"
AUTH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/token")
AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/".*//')

if [ ! -z "$AUTH_TOKEN" ]; then
    echo -e "${GREEN}✓ Authentication successful${NC}"
    echo "Token: ${AUTH_TOKEN:0:30}..."
else
    echo -e "${RED}✗ Authentication failed${NC}"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi

test_simple "Authentication Token" "echo 'Token received: ${AUTH_TOKEN:0:50}...'"

# Test system endpoints
echo -e "${BLUE}3. Testing System Endpoints${NC}"
test_simple "Get System Stats" "curl -H 'Authorization: Bearer $AUTH_TOKEN' '$BASE_URL/api/system'"

# Test power endpoints (the problematic ones)
echo -e "${BLUE}4. Testing Power Management Endpoints (THE ISSUE)${NC}"
test_simple "Power Restart (No Delay)" "curl -i -X POST -H 'Authorization: Bearer $AUTH_TOKEN' -H 'Content-Type: application/json' -d '{\"action\":\"restart\",\"delay\":0}' '$BASE_URL/api/power'"

test_simple "Power Shutdown (5s Delay)" "curl -i -X POST -H 'Authorization: Bearer $AUTH_TOKEN' -H 'Content-Type: application/json' -d '{\"action\":\"shutdown\",\"delay\":5}' '$BASE_URL/api/power'"

# Test service endpoints
echo -e "${BLUE}5. Testing Service Management Endpoints${NC}"
test_simple "Get Services List" "curl -H 'Authorization: Bearer $AUTH_TOKEN' '$BASE_URL/api/services'"

test_simple "Service Status Check (SSH)" "curl -i -X POST -H 'Authorization: Bearer $AUTH_TOKEN' -H 'Content-Type: application/json' -d '{\"service_name\":\"ssh\",\"action\":\"status\"}' '$BASE_URL/api/services'"

# Test without authentication (should fail)
echo -e "${BLUE}6. Testing Authentication Requirements${NC}"
test_simple "System Stats Without Auth (Should be 401)" "curl -i '$BASE_URL/api/system'"

echo -e "${GREEN}=== Testing Complete ===${NC}"
echo "Look for HTTP status codes and error messages above to identify issues."
