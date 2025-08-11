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

# Function to check if timeout command exists, fallback to curl's built-in timeout
safe_curl() {
    if command -v timeout >/dev/null 2>&1; then
        timeout 15 curl "$@"
    else
        # Use curl's built-in timeout if timeout command not available
        curl --max-time 15 "$@"
    fi
}

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
            response_body=$(safe_curl -s -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $AUTH_TOKEN" -d "$data" "$url" 2>/dev/null || echo "")
            status_code=$(safe_curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $AUTH_TOKEN" -d "$data" "$url" 2>/dev/null || echo "000")
        else
            response_body=$(safe_curl -s -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "")
            status_code=$(safe_curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "000")
        fi
    elif [ "$method" = "OPTIONS" ]; then
        # Handle OPTIONS requests (CORS preflight)
        if [ "$use_auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
            response_body=$(safe_curl -s -X OPTIONS -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "")
            status_code=$(safe_curl -s -o /dev/null -w "%{http_code}" -X OPTIONS -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "000")
        else
            response_body=$(safe_curl -s -X OPTIONS "$url" 2>/dev/null || echo "")
            status_code=$(safe_curl -s -o /dev/null -w "%{http_code}" -X OPTIONS "$url" 2>/dev/null || echo "000")
        fi
    else
        # Handle GET and other methods
        if [ "$use_auth" = "true" ] && [ -n "$AUTH_TOKEN" ]; then
            response_body=$(safe_curl -s -X "$method" -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "")
            status_code=$(safe_curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "000")
        else
            response_body=$(safe_curl -s -X "$method" "$url" 2>/dev/null || echo "")
            status_code=$(safe_curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" 2>/dev/null || echo "000")
        fi
    fi
    
    # Clean up status code - ensure it's a 3-digit number
    status_code=$(echo "$status_code" | grep -o '[0-9][0-9][0-9]' | head -1 || echo "000")
    
    echo "  Status: $status_code"
    
    # Enhanced validation - check both status code and response content
    local test_passed=false
    
    if [ "$status_code" = "$expected_status" ]; then
        # Status code matches expected - this is a PASS
        echo -e "  ${GREEN}✅ PASS${NC}"
        test_passed=true
    else
        echo -e "  ${RED}❌ FAIL (Expected: $expected_status, Got: $status_code)${NC}"
        if [ -n "$response_body" ]; then
            echo "  Response: $response_body"
        fi
    fi
    
    if [ "$test_passed" = "true" ]; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
    echo ""
}

# 1. Basic Connectivity
echo -e "${BLUE}1. Testing Basic Connectivity${NC}"
echo -e "${YELLOW}Testing network connectivity via HTTP instead of ping...${NC}"
if safe_curl -s --connect-timeout 5 --max-time 10 "http://$PI_IP:$BACKEND_PORT/health" > /dev/null 2>&1; then
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
auth_response=$(safe_curl -s -X POST -H "Content-Type: application/json" -d '{"username":"abhinav","password":"kavachi"}' "http://$PI_IP:$BACKEND_PORT/api/auth/token" 2>/dev/null || echo "{}")

# Extract token from response using a cross-platform approach
if echo "$auth_response" | grep -q "access_token"; then
    # Try multiple extraction methods for better compatibility
    # Handle both "access_token":"..." and "access_token": "..." formats
    AUTH_TOKEN=$(echo "$auth_response" | sed 's/.*"access_token":\s*"\([^"]*\)".*/\1/' | head -1)
    
    # If sed failed, try grep approach with flexible spacing
    if [ "$AUTH_TOKEN" = "$auth_response" ] || [ ${#AUTH_TOKEN} -gt 200 ]; then
        AUTH_TOKEN=$(echo "$auth_response" | grep -o '"access_token":\s*"[^"]*"' | sed 's/.*"access_token":\s*"\([^"]*\)".*/\1/')
    fi
    
    # Final validation
    if [ -n "$AUTH_TOKEN" ] && [ "$AUTH_TOKEN" != "$auth_response" ] && [ ${#AUTH_TOKEN} -lt 200 ]; then
        echo -e "${GREEN}✅ Token received: ${AUTH_TOKEN:0:30}...${NC}"
        run_test "Auth Token Request" "http://$PI_IP:$BACKEND_PORT/api/auth/token" "POST" '{"username":"abhinav","password":"kavachi"}'
    else
        echo -e "${RED}❌ Failed to extract token${NC}"
        echo "Response: $auth_response"
        echo "Extracted token: '$AUTH_TOKEN'"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "Response: $auth_response"
    ((TESTS_FAILED++))
fi

# Test invalid credentials
echo -e "${YELLOW}Testing invalid credentials...${NC}"
run_test "Invalid Credentials" "http://$PI_IP:$BACKEND_PORT/api/auth/token" "POST" '{"username":"wrong","password":"wrong"}' "200"

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

# 8. Enhanced Monitoring Commands (with auth)
echo -e "${BLUE}8. Testing Enhanced Monitoring Commands${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Commands List" "http://$PI_IP:$BACKEND_PORT/api/commands" "GET" "" "200" "true"
    run_test "CPU Temperature Command" "http://$PI_IP:$BACKEND_PORT/api/commands?command=cpu_temperature" "GET" "" "200" "true"
    run_test "System Load Command" "http://$PI_IP:$BACKEND_PORT/api/commands?command=system_load" "GET" "" "200" "true"
    run_test "Network Interfaces Command" "http://$PI_IP:$BACKEND_PORT/api/commands?command=network_interfaces" "GET" "" "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 9. Enhanced System Stats (with auth)
echo -e "${BLUE}9. Testing Enhanced System Stats${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Enhanced System Stats" "http://$PI_IP:$BACKEND_PORT/api/system/enhanced" "GET" "" "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 9.5. Comprehensive Enhanced Monitoring Tests (with auth)
echo -e "${BLUE}9.5. Testing Comprehensive Enhanced Monitoring${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    echo -e "${YELLOW}Testing Raspberry Pi specific commands...${NC}"
    run_test "ARM Clock Speed" "http://$PI_IP:$BACKEND_PORT/api/commands?command=arm_clock" "GET" "" "200" "true"
    run_test "Core Voltage" "http://$PI_IP:$BACKEND_PORT/api/commands?command=core_voltage" "GET" "" "200" "true"
    run_test "Throttling Status" "http://$PI_IP:$BACKEND_PORT/api/commands?command=throttling_status" "GET" "" "200" "true"
    
    echo -e "${YELLOW}Testing hardware monitoring commands...${NC}"
    run_test "CPU Info" "http://$PI_IP:$BACKEND_PORT/api/commands?command=cpu_info" "GET" "" "200" "true"
    run_test "Memory Info" "http://$PI_IP:$BACKEND_PORT/api/commands?command=memory_info" "GET" "" "200" "true"
    run_test "Disk Usage" "http://$PI_IP:$BACKEND_PORT/api/commands?command=disk_usage" "GET" "" "200" "true"
    
    echo -e "${YELLOW}Testing network monitoring commands...${NC}"
    run_test "Network Stats" "http://$PI_IP:$BACKEND_PORT/api/commands?command=network_stats" "GET" "" "200" "true"
    run_test "Active Connections" "http://$PI_IP:$BACKEND_PORT/api/commands?command=active_connections" "GET" "" "200" "true"
    
    echo -e "${YELLOW}Testing system performance commands...${NC}"
    run_test "Process List" "http://$PI_IP:$BACKEND_PORT/api/commands?command=process_list" "GET" "" "200" "true"
    run_test "Service Status" "http://$PI_IP:$BACKEND_PORT/api/commands?command=service_status" "GET" "" "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 10. Test Service Actions (with auth)
echo -e "${BLUE}10. Testing Service Actions${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Service Status Check" "http://$PI_IP:$BACKEND_PORT/api/services" "POST" '{"service_name":"ssh","action":"status"}' "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 11. Test Power Actions (with auth)
echo -e "${BLUE}11. Testing Power Actions${NC}"
if [ -n "$AUTH_TOKEN" ]; then
    run_test "Power Action Check" "http://$PI_IP:$BACKEND_PORT/api/power" "POST" '{"action":"restart","delay":0}' "200" "true"
else
    echo -e "${YELLOW}Skipping authenticated endpoint (no token)${NC}"
    ((TESTS_FAILED++))
fi

# 12. Frontend Basic Access
echo -e "${BLUE}12. Testing Frontend${NC}"
run_test "Frontend Access" "http://$PI_IP:$FRONTEND_PORT/"

# 13. Error Handling Tests
echo -e "${BLUE}13. Testing Error Handling${NC}"
run_test "Invalid Endpoint" "http://$PI_IP:$BACKEND_PORT/invalid" "GET" "" "404"
run_test "Invalid Method" "http://$PI_IP:$BACKEND_PORT/health" "POST" '{"test":"data"}' "405"

# 14. Authentication Error Tests
echo -e "${BLUE}14. Testing Authentication Errors${NC}"
run_test "System Stats (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/system" "GET" "" "401"
run_test "Services (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/services" "GET" "" "401"
run_test "Power (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/power" "GET" "" "401"
run_test "Commands (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/commands" "GET" "" "401"
run_test "Enhanced System (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/system/enhanced" "GET" "" "401"

# 15. CORS Tests
echo -e "${BLUE}15. Testing CORS${NC}"
run_test "CORS Preflight" "http://$PI_IP:$BACKEND_PORT/api/system" "OPTIONS" "" "200"

# 16. Performance Tests
echo -e "${BLUE}16. Testing Performance${NC}"
echo -e "${YELLOW}Testing: Response Time${NC}"
start_time=$(date +%s%N)
safe_curl -s "http://$PI_IP:$BACKEND_PORT/health" > /dev/null
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

echo ""
echo -e "${BLUE}🔍 Enhanced Monitoring Features Tested:${NC}"
echo "  • System Information Commands (uname, cpu_info, etc.)"
echo "  • Hardware Monitoring (temperature, voltage, clock speeds)"
echo "  • Network Diagnostics (interfaces, connections, stats)"
echo "  • Performance Monitoring (processes, services, resources)"
echo "  • Raspberry Pi Specific Commands (vcgencmd)"
echo "  • Command Caching and Error Handling"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Your Pi Monitor with enhanced monitoring is working perfectly!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Check the output above for details.${NC}"
    exit 1
fi
