#!/bin/bash
# Pi Monitor - Remote API Testing
# Tests all endpoints from any machine

set -e

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

# Function to run a test
run_test() {
    local test_name="$1"
    local url="$2"
    local method="${3:-GET}"
    local data="${4:-}"
    local expected_status="${5:-200}"
    
    echo -e "${YELLOW}Testing: $test_name${NC}"
    echo "  URL: $url"
    echo "  Method: $method"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        echo "  Data: $data"
    fi
    
    # Run the test
    if [ "$method" = "POST" ]; then
        response=$(curl -s -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "000")
    else
        response=$(curl -s -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    fi
    
    # Extract status code (last 3 characters)
    status_code="${response: -3}"
    # Extract response body (everything except last 3 characters)
    response_body="${response%???}"
    
    echo "  Status: $status_code"
    
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "  ${GREEN}✅ PASS${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ FAIL (Expected: $expected_status, Got: $status_code)${NC}"
        echo "  Response: $response_body"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# 1. Basic Connectivity
echo -e "${BLUE}1. Testing Basic Connectivity${NC}"
if ping -c 1 -W 2 "$PI_IP" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Pi is reachable${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Pi is not reachable${NC}"
    ((TESTS_FAILED++))
fi
echo ""

# 2. Backend Health Check
echo -e "${BLUE}2. Testing Backend Health${NC}"
run_test "Health Check" "http://$PI_IP:$BACKEND_PORT/health"

# 3. Backend Root Endpoint
echo -e "${BLUE}3. Testing Backend Root${NC}"
run_test "Root Endpoint" "http://$PI_IP:$BACKEND_PORT/"

# 4. Backend System Stats
echo -e "${BLUE}4. Testing System Monitoring${NC}"
run_test "System Stats" "http://$PI_IP:$BACKEND_PORT/api/system"

# 5. Backend Services Status
echo -e "${BLUE}5. Testing Service Management${NC}"
run_test "Services Status" "http://$PI_IP:$BACKEND_PORT/api/services"

# 6. Backend Power Management
echo -e "${BLUE}6. Testing Power Management${NC}"
run_test "Power Status" "http://$PI_IP:$BACKEND_PORT/api/power"

# 7. Backend Authentication
echo -e "${BLUE}7. Testing Authentication${NC}"
run_test "Auth Token Request" "http://$PI_IP:$BACKEND_PORT/api/auth/token" "POST" '{"username":"admin","password":"admin"}'

# 8. Frontend Basic Access
echo -e "${BLUE}8. Testing Frontend${NC}"
run_test "Frontend Access" "http://$PI_IP:$FRONTEND_PORT/"

# 9. Error Handling Tests
echo -e "${BLUE}9. Testing Error Handling${NC}"
run_test "Invalid Endpoint" "http://$PI_IP:$BACKEND_PORT/invalid" "GET" "" "404"
run_test "Invalid Method" "http://$PI_IP:$BACKEND_PORT/health" "POST" '{"test":"data"}' "405"

# 10. Performance Tests
echo -e "${BLUE}10. Testing Performance${NC}"
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
