#!/bin/bash
# Pi Monitor - Remote API Testing
# Tests all endpoints from any machine

# Remove set -e to prevent early exit
# set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🥧 Pi Monitor - Remote API Testing${NC}"
echo "=========================================="

# Configuration - change these as needed
PI_IP="192.168.0.201"
BACKEND_PORT="5001"
FRONTEND_PORT="80"

echo -e "${YELLOW}Testing against:${NC}"
echo "  Pi IP: $PI_IP"
echo "  Backend: http://$PI_IP:$BACKEND_PORT"
echo "  Frontend: http://$PI_IP:$FRONTEND_PORT"
echo ""

echo -e "${BLUE}🔍 Starting Comprehensive API Tests...${NC}"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Global variable to store auth token
AUTH_TOKEN=""

# Function to run a test
run_test() {
    local test_name="$1"
    local url="$2"
    local method="${3:-GET}"
    local data="${4:-}"
    local expected_status="${5:-200}"
    local use_auth="${6:-false}"
    
    echo -e "${YELLOW}Testing: $test_name${NC}"
    echo "  URL: $url"
    echo "  Method: $method"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        echo "  Data: $data"
    fi
    
    if [ "$use_auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
        echo "  Auth: Bearer token"
    fi
    
    # Run the test and capture both response body and status code
    if [ "$method" = "POST" ]; then
        if [ "$use_auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
            response_body=$(curl -s -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $AUTH_TOKEN" -d "$data" "$url" 2>/dev/null || echo "")
            status_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $AUTH_TOKEN" -d "$data" "$url" 2>/dev/null || echo "000")
        else
            response_body=$(curl -s -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "")
            status_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "000")
        fi
    else
        if [ "$use_auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
            response_body=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "")
            status_code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "000")
        else
            response_body=$(curl -s "$url" 2>/dev/null || echo "")
            status_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
        fi
    fi
    
    # Clean up status code - ensure it's a 3-digit number
    status_code=$(echo "$status_code" | grep -o '[0-9][0-9][0-9]' | head -1 || echo "000")
    
    echo "  Status: $status_code"
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ FAIL (Expected: $expected_status, Got: $status_code)${NC}"
        if [ -n "$response_body" ]; then
            echo "  Response: $response_body"
        fi
        ((TESTS_FAILED++))
    fi
    echo ""
}

# 1. Basic Connectivity
echo -e "${BLUE}1. Testing Basic Connectivity${NC}"
echo -e "${YELLOW}Testing network connectivity via HTTP instead of ping...${NC}"
if curl -s --connect-timeout 5 "http://$PI_IP:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Pi is reachable via HTTP${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Pi is not reachable via HTTP${NC}"
    echo -e "${YELLOW}Continuing with tests anyway...${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# 2. Backend Health Check
echo -e "${BLUE}2. Testing Backend Health${NC}"
run_test "Health Check" "http://$PI_IP:$BACKEND_PORT/health"

# 3. Backend Root Endpoint
echo -e "${BLUE}3. Testing Backend Root${NC}"
run_test "Root Endpoint" "http://$PI_IP:$BACKEND_PORT/"

# 4. Backend Authentication (Get Token)
echo -e "${BLUE}4. Testing Authentication${NC}"
echo -e "${YELLOW}Getting authentication token...${NC}"
auth_response=$(curl -s -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin"}' "http://$PI_IP:$BACKEND_PORT/api/auth/token" 2>/dev/null || echo "{}")

# Extract token from response using a cross-platform approach
if echo "$auth_response" | grep -q "access_token"; then
    # Use a cross-platform token extraction method
    AUTH_TOKEN=$(echo "$auth_response" | sed 's/.*"access_token":"\([^"]*\)".*/\1/')
    if [ -n "$AUTH_TOKEN" ] && [ "$AUTH_TOKEN" != "$auth_response" ]; then
        echo -e "${GREEN}✅ Token received: ${AUTH_TOKEN:0:30}...${NC}"
        run_test "Auth Token Request" "http://$PI_IP:$BACKEND_PORT/api/auth/token" "POST" '{"username":"admin","password":"admin"}'
    else
        echo -e "${RED}❌ Failed to extract token${NC}"
        echo "DEBUG: Token extraction failed, AUTH_TOKEN='$AUTH_TOKEN'"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "Response: $auth_response"
    ((TESTS_FAILED++))
fi
echo ""

# 5. Backend System Stats (with auth)
echo -e "${BLUE}5. Testing System Monitoring${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "System Stats" "http://$PI_IP:$BACKEND_PORT/api/system" "GET" "" "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 6. Backend Services Status (with auth)
echo -e "${BLUE}6. Testing Service Management${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Services Status" "http://$PI_IP:$BACKEND_PORT/api/services" "GET" "" "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 7. Backend Power Management (with auth)
echo -e "${BLUE}7. Testing Power Management${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Power Status" "http://$PI_IP:$BACKEND_PORT/api/power" "GET" "" "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 8. Test Service Actions (with auth)
echo -e "${BLUE}8. Testing Service Actions${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Service Status Check" "http://$PI_IP:$BACKEND_PORT/api/services" "POST" '{"service_name":"ssh","action":"status"}' "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 9. Test Power Actions (with auth)
echo -e "${BLUE}9. Testing Power Actions${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Power Action Check" "http://$PI_IP:$BACKEND_PORT/api/power" "POST" '{"action":"restart","delay":0}' "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 10. Frontend Basic Access
echo -e "${BLUE}10. Testing Frontend${NC}"
run_test "Frontend Access" "http://$PI_IP:$FRONTEND_PORT/"

# 11. Error Handling Tests
echo -e "${BLUE}11. Testing Error Handling${NC}"
run_test "Invalid Endpoint" "http://$PI_IP:$BACKEND_PORT/invalid" "GET" "" "404"
run_test "Invalid Method" "http://$PI_IP:$BACKEND_PORT/health" "POST" '{"test":"data"}' "404"

# 12. Authentication Error Tests
echo -e "${BLUE}12. Testing Authentication Errors${NC}"
run_test "System Stats (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/system" "GET" "" "401"
run_test "Services (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/services" "GET" "" "401"
run_test "Power (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/power" "GET" "" "401"

# 13. CORS Tests
echo -e "${BLUE}13. Testing CORS${NC}"
run_test "CORS Preflight" "http://$PI_IP:$BACKEND_PORT/api/system" "OPTIONS" "" "200"

# 14. Performance Tests
echo -e "${BLUE}14. Testing Performance${NC}"
echo -e "${YELLOW}Testing: Response Time${NC}"
start_time=$(date +%s%N)
curl -s "http://$PI_IP:$BACKEND_PORT/health" > /dev/null
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))
echo "  Response Time: ${response_time}ms"
if [ $response_time -lt 1000 ]; then
    echo -e "  ${GREEN}✅ PASS (Fast response)${NC}"
    ((TESTS_PASSED++))
else
    echo -e "  ${YELLOW}⚠️  SLOW (Response time: ${response_time}ms)${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# Summary
echo -e "${BLUE}📊 Test Summary${NC}"
echo "====================================="
echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
total_tests=$((TESTS_PASSED + TESTS_FAILED))
echo "Total Tests: $total_tests"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Your Pi Monitor is working perfectly!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Check the output above for details.${NC}"
    exit 1
fi
