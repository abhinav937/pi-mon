#!/bin/bash
# Pi Monitor - Remote API Test Script
# Test the API from any machine (Windows, Mac, Linux, Pi)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration - Change these for your setup
DEFAULT_PI_IP="192.168.0.201"
DEFAULT_BACKEND_PORT="5001"
DEFAULT_FRONTEND_PORT="80"

# Get Pi IP from user or use default
echo -e "${BLUE}🥧 Pi Monitor - Remote API Testing${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}Enter your Pi's IP address (or press Enter for default):${NC}"
read -p "Pi IP [${DEFAULT_PI_IP}]: " PI_IP
PI_IP=${PI_IP:-$DEFAULT_PI_IP}

echo -e "${YELLOW}Enter backend port (or press Enter for default):${NC}"
read -p "Backend Port [${DEFAULT_BACKEND_PORT}]: " BACKEND_PORT
BACKEND_PORT=${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}

echo -e "${YELLOW}Enter frontend port (or press Enter for default):${NC}"
read -p "Frontend Port [${DEFAULT_FRONTEND_PORT}]: " FRONTEND_PORT
FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}

# Set URLs
BACKEND_URL="http://${PI_IP}:${BACKEND_PORT}"
FRONTEND_URL="http://${PI_IP}:${FRONTEND_PORT}"

echo ""
echo -e "${CYAN}Testing against:${NC}"
echo "  Pi IP: ${PI_IP}"
echo "  Backend: ${BACKEND_URL}"
echo "  Frontend: ${FRONTEND_URL}"
echo ""

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_endpoint() {
    local description="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_status="$5"
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "  URL: $url"
    
    # Build curl command
    local curl_cmd="curl -s -w 'HTTP_STATUS:%{http_code}'"
    
    if [ "$method" = "POST" ]; then
        curl_cmd="$curl_cmd -X POST"
        if [ -n "$data" ]; then
            curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
        fi
    fi
    
    curl_cmd="$curl_cmd '$url'"
    
    # Execute and capture response
    local response=$(eval $curl_cmd 2>/dev/null)
    local http_status=$(echo "$response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*//')
    
    echo "  Status: $http_status"
    
    # Check if status matches expected
    if [ "$http_status" = "$expected_status" ]; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ FAIL - Expected $expected_status, got $http_status${NC}"
        echo "  Response: $body"
        ((TESTS_FAILED++))
    fi
    
    echo ""
}

# Test function with auth
test_endpoint_with_auth() {
    local description="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_status="$5"
    local token="$6"
    
    echo -e "${YELLOW}Testing: $description${NC}"
    echo "  URL: $url"
    
    # Build curl command
    local curl_cmd="curl -s -w 'HTTP_STATUS:%{http_code}'"
    
    if [ "$method" = "POST" ]; then
        curl_cmd="$curl_cmd -X POST"
        if [ -n "$data" ]; then
            curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
        fi
    fi
    
    if [ -n "$token" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $token'"
    fi
    
    curl_cmd="$curl_cmd '$url'"
    
    # Execute and capture response
    local response=$(eval $curl_cmd 2>/dev/null)
    local http_status=$(echo "$response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
    local body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*//')
    
    echo "  Status: $http_status"
    
    # Check if status matches expected
    if [ "$http_status" = "$expected_status" ]; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ FAIL - Expected $expected_status, got $http_status${NC}"
        echo "  Response: $body"
        ((TESTS_FAILED++))
    fi
    
    echo ""
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ Error: curl is not installed${NC}"
    echo "Please install curl to run this test script."
    echo ""
    echo "Installation commands:"
    echo "  Ubuntu/Debian: sudo apt-get install curl"
    echo "  CentOS/RHEL: sudo yum install curl"
    echo "  macOS: brew install curl"
    echo "  Windows: Download from https://curl.se/windows/"
    exit 1
fi

echo -e "${BLUE}🔍 Starting API Tests...${NC}"
echo ""

# Test 1: Basic connectivity to Pi
echo -e "${BLUE}1. Testing Basic Connectivity${NC}"
if ping -c 1 -W 2 "$PI_IP" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Pi is reachable${NC}"
else
    echo -e "${RED}❌ Pi is not reachable${NC}"
    echo "  Check if:"
    echo "    - Pi is powered on"
    echo "    - Pi is connected to network"
    echo "    - IP address is correct"
    echo "    - Firewall allows ping"
    echo ""
    echo "  You can still test the API if the Pi blocks ping but allows HTTP"
fi
echo ""

# Test 2: Backend health check
echo -e "${BLUE}2. Testing Backend Health${NC}"
test_endpoint "Health Check" "GET" "${BACKEND_URL}/health" "" "200"

# Test 3: Backend root endpoint
echo -e "${BLUE}3. Testing Backend Root${NC}"
test_endpoint "Root Endpoint" "GET" "${BACKEND_URL}/" "" "200"

# Test 4: Authentication
echo -e "${BLUE}4. Testing Authentication${NC}"
test_endpoint "Get Auth Token" "POST" "${BACKEND_URL}/api/auth/token" "" "200"

# Get the token for authenticated tests
echo -e "${YELLOW}Getting authentication token...${NC}"
AUTH_RESPONSE=$(curl -s -X POST "${BACKEND_URL}/api/auth/token")
AUTH_TOKEN=$(echo "$AUTH_RESPONSE" | grep -o '"access_token":"[^"]*"' | sed 's/"access_token":"//' | sed 's/".*//')

if [ -n "$AUTH_TOKEN" ]; then
    echo -e "${GREEN}✅ Token received: ${AUTH_TOKEN:0:30}...${NC}"
    echo ""
else
    echo -e "${RED}❌ Failed to get token${NC}"
    echo "Response: $AUTH_RESPONSE"
    echo ""
    echo "Continuing with unauthenticated tests..."
    AUTH_TOKEN=""
fi

# Test 5: System stats (requires auth)
echo -e "${BLUE}5. Testing System Endpoints${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    test_endpoint_with_auth "Get System Stats" "GET" "${BACKEND_URL}/api/system" "" "200" "$AUTH_TOKEN"
else
    test_endpoint_with_auth "Get System Stats (No Auth)" "GET" "${BACKEND_URL}/api/system" "" "401" ""
fi

# Test 6: Services (requires auth)
echo -e "${BLUE}6. Testing Service Endpoints${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    test_endpoint_with_auth "Get Services" "GET" "${BACKEND_URL}/api/services" "" "200" "$AUTH_TOKEN"
    test_endpoint_with_auth "Service Status Check" "POST" "${BACKEND_URL}/api/services" '{"service_name":"ssh","action":"status"}' "200" "$AUTH_TOKEN"
else
    test_endpoint_with_auth "Get Services (No Auth)" "GET" "${BACKEND_URL}/api/services" "" "401" ""
fi

# Test 7: Power management (requires auth)
echo -e "${BLUE}7. Testing Power Management${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    test_endpoint_with_auth "Power Status Check" "POST" "${BACKEND_URL}/api/power" '{"action":"restart","delay":0}' "200" "$AUTH_TOKEN"
else
    test_endpoint_with_auth "Power Status Check (No Auth)" "POST" "${BACKEND_URL}/api/power" '{"action":"restart","delay":0}' "401" ""
fi

# Test 8: Frontend accessibility
echo -e "${BLUE}8. Testing Frontend${NC}"
test_endpoint "Frontend Access" "GET" "${FRONTEND_URL}" "" "200"

# Test 9: Invalid endpoints
echo -e "${BLUE}9. Testing Error Handling${NC}"
test_endpoint "Invalid Endpoint" "GET" "${BACKEND_URL}/invalid" "" "404"

# Test 10: CORS preflight
echo -e "${BLUE}10. Testing CORS${NC}"
test_endpoint "CORS Preflight" "OPTIONS" "${BACKEND_URL}/api/system" "" "200"

# Summary
echo -e "${BLUE}📊 Test Summary${NC}"
echo "================"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo -e "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All tests passed! Your Pi Monitor is working perfectly.${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  Some tests failed. Check the output above for details.${NC}"
fi

echo ""
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo "  Backend API: ${BACKEND_URL}"
echo "  Frontend: ${FRONTEND_URL}"
echo "  Health Check: ${BACKEND_URL}/health"

echo ""
echo -e "${BLUE}💡 Manual Testing Commands:${NC}"
echo "  # Test health"
echo "  curl ${BACKEND_URL}/health"
echo ""
echo "  # Get auth token"
echo "  curl -X POST ${BACKEND_URL}/api/auth/token"
echo ""
echo "  # Test with token (replace TOKEN_HERE)"
echo "  curl -H 'Authorization: Bearer TOKEN_HERE' ${BACKEND_URL}/api/system"

echo ""
echo -e "${CYAN}🔧 Troubleshooting:${NC}"
echo "  - If Pi is not reachable: Check network and IP address"
echo "  - If backend fails: Check if Docker containers are running"
echo "  - If auth fails: Check backend logs"
echo "  - If frontend fails: Check nginx configuration"
