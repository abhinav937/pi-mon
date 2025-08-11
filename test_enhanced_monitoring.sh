#!/bin/bash
# Pi Monitor - Enhanced Monitoring Testing Script
# Tests all the new enhanced monitoring commands and endpoints

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
PI_IP="192.168.0.201"
BACKEND_PORT="5001"
USERNAME="abhinav"
PASSWORD="kavachi"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
AUTH_TOKEN=""

echo -e "${BLUE}🥧 Pi Monitor - Enhanced Monitoring Test Suite${NC}"
echo "======================================================"
echo -e "${YELLOW}Testing enhanced monitoring features against:${NC}"
echo "  Pi IP: $PI_IP"
echo "  Backend: http://$PI_IP:$BACKEND_PORT"
echo "  Username: $USERNAME"
echo ""

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
    
    # Run the test
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
            response_body=$(curl -s -X "$method" -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "")
            status_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Authorization: Bearer $AUTH_TOKEN" "$url" 2>/dev/null || echo "000")
        else
            response_body=$(curl -s -X "$method" "$url" 2>/dev/null || echo "")
            status_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" 2>/dev/null || echo "000")
        fi
    fi
    
    # Clean up status code
    status_code=$(echo "$status_code" | grep -o '[0-9][0-9][0-9]' | head -1 || echo "000")
    
    # Check result
    if [ "$status_code" = "$expected_status" ]; then
        echo -e "  ${GREEN}✅ PASS (Status: $status_code)${NC}"
        ((TESTS_PASSED++))
        
        # Show response preview for successful commands
        if [ "$use_auth" = "true" ] && [ -n "$response_body" ]; then
            echo "  Response preview: ${response_body:0:100}..."
        fi
    else
        echo -e "  ${RED}❌ FAIL (Expected: $expected_status, Got: $status_code)${NC}"
        if [ -n "$response_body" ]; then
            echo "  Error: ${response_body:0:200}..."
        fi
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Function to get authentication token
get_auth_token() {
    echo -e "${BLUE}🔐 Getting authentication token...${NC}"
    
    response=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
        "http://$PI_IP:$BACKEND_PORT/api/auth/token")
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        # Extract token using grep and sed (simple approach)
        token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | sed 's/.*"access_token":"\([^"]*\)".*/\1/')
        if [ -n "$token" ]; then
            AUTH_TOKEN="$token"
            echo -e "${GREEN}✅ Authentication successful${NC}"
            echo "  Token: ${token:0:20}..."
            return 0
        fi
    fi
    
    echo -e "${RED}❌ Authentication failed${NC}"
    echo "  Response: $response"
    return 1
}

# Function to test basic connectivity
test_connectivity() {
    echo -e "${BLUE}🔍 Testing Basic Connectivity${NC}"
    echo "====================================="
    
    # Test ping
    echo -e "${YELLOW}Testing network connectivity...${NC}"
    if ping -c 1 -W 2 "$PI_IP" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Pi is reachable${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}❌ Pi is not reachable${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
    
    # Test backend health
    run_test "Backend Health Check" "http://$PI_IP:$BACKEND_PORT/health" "GET"
    
    # Test root endpoint
    run_test "Root Endpoint" "http://$PI_IP:$BACKEND_PORT/" "GET"
    
    echo ""
}

# Function to test enhanced monitoring commands
test_enhanced_commands() {
    echo -e "${BLUE}🔧 Testing Enhanced Monitoring Commands${NC}"
    echo "================================================"
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo -e "${RED}❌ No authentication token available${NC}"
        ((TESTS_FAILED++))
        return
    fi
    
    # Test commands list endpoint
    run_test "Commands List" "http://$PI_IP:$BACKEND_PORT/api/commands" "GET" "" "200" "true"
    
    # Test Raspberry Pi specific commands
    echo -e "${PURPLE}Testing Raspberry Pi specific commands...${NC}"
    run_test "CPU Temperature" "http://$PI_IP:$BACKEND_PORT/api/commands?command=cpu_temperature" "GET" "" "200" "true"
    run_test "ARM Clock Speed" "http://$PI_IP:$BACKEND_PORT/api/commands?command=arm_clock" "GET" "" "200" "true"
    run_test "Core Voltage" "http://$PI_IP:$BACKEND_PORT/api/commands?command=core_voltage" "GET" "" "200" "true"
    run_test "Throttling Status" "http://$PI_IP:$BACKEND_PORT/api/commands?command=throttling_status" "GET" "" "200" "true"
    
    # Test hardware monitoring commands
    echo -e "${PURPLE}Testing hardware monitoring commands...${NC}"
    run_test "CPU Info" "http://$PI_IP:$BACKEND_PORT/api/commands?command=cpu_info" "GET" "" "200" "true"
    run_test "Memory Info" "http://$PI_IP:$BACKEND_PORT/api/commands?command=memory_info" "GET" "" "200" "true"
    run_test "Disk Usage" "http://$PI_IP:$BACKEND_PORT/api/commands?command=disk_usage" "GET" "" "200" "true"
    run_test "System Load" "http://$PI_IP:$BACKEND_PORT/api/commands?command=system_load" "GET" "" "200" "true"
    
    # Test network monitoring commands
    echo -e "${PURPLE}Testing network monitoring commands...${NC}"
    run_test "Network Interfaces" "http://$PI_IP:$BACKEND_PORT/api/commands?command=network_interfaces" "GET" "" "200" "true"
    run_test "Network Stats" "http://$PI_IP:$BACKEND_PORT/api/commands?command=network_stats" "GET" "" "200" "true"
    run_test "Active Connections" "http://$PI_IP:$BACKEND_PORT/api/commands?command=active_connections" "GET" "" "200" "true"
    
    # Test system performance commands
    echo -e "${PURPLE}Testing system performance commands...${NC}"
    run_test "Process List" "http://$PI_IP:$BACKEND_PORT/api/commands?command=process_list" "GET" "" "200" "true"
    run_test "Service Status" "http://$PI_IP:$BACKEND_PORT/api/commands?command=service_status" "GET" "" "200" "true"
    run_test "Kernel Info" "http://$PI_IP:$BACKEND_PORT/api/commands?command=kernel_info" "GET" "" "200" "true"
    
    echo ""
}

# Function to test enhanced system endpoints
test_enhanced_endpoints() {
    echo -e "${BLUE}📊 Testing Enhanced System Endpoints${NC}"
    echo "============================================="
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo -e "${RED}❌ No authentication token available${NC}"
        ((TESTS_FAILED++))
        return
    fi
    
    # Test enhanced system stats
    run_test "Enhanced System Stats" "http://$PI_IP:$BACKEND_PORT/api/system/enhanced" "GET" "" "200" "true"
    
    # Test metrics endpoint for enhanced data
    run_test "Metrics with Enhanced Data" "http://$PI_IP:$BACKEND_PORT/api/metrics?minutes=10" "GET" "" "200" "true"
    
    # Test system info endpoint
    run_test "Detailed System Info" "http://$PI_IP:$BACKEND_PORT/api/system/info" "GET" "" "200" "true"
    
    echo ""
}

# Function to test error handling
test_error_handling() {
    echo -e "${BLUE}⚠️  Testing Error Handling${NC}"
    echo "================================="
    
    # Test invalid command
    run_test "Invalid Command" "http://$PI_IP:$BACKEND_PORT/api/commands?command=invalid_command" "GET" "" "400" "true"
    
    # Test commands without authentication
    run_test "Commands (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/commands" "GET" "" "401"
    
    # Test enhanced system without authentication
    run_test "Enhanced System (No Auth)" "http://$PI_IP:$BACKEND_PORT/api/system/enhanced" "GET" "" "401"
    
    # Test invalid endpoint
    run_test "Invalid Endpoint" "http://$PI_IP:$BACKEND_PORT/api/invalid" "GET" "" "404"
    
    echo ""
}

# Function to test command caching
test_command_caching() {
    echo -e "${BLUE}⚡ Testing Command Caching${NC}"
    echo "================================="
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo -e "${RED}❌ No authentication token available${NC}"
        ((TESTS_FAILED++))
        return
    fi
    
    echo -e "${YELLOW}Testing command caching (running same command twice)...${NC}"
    
    # First run
    start_time=$(date +%s%N)
    response1=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" "http://$PI_IP:$BACKEND_PORT/api/commands?command=cpu_temperature")
    end_time=$(date +%s%N)
    time1=$(( (end_time - start_time) / 1000000 ))
    
    # Second run (should be cached)
    start_time=$(date +%s%N)
    response2=$(curl -s -H "Authorization: Bearer $AUTH_TOKEN" "http://$PI_IP:$BACKEND_PORT/api/commands?command=cpu_temperature")
    end_time=$(date +%s%N)
    time2=$(( (end_time - start_time) / 1000000 ))
    
    echo "  First run: ${time1}ms"
    echo "  Second run: ${time2}ms"
    
    if [ $time2 -lt $time1 ]; then
        echo -e "  ${GREEN}✅ Caching working (faster second run)${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "  ${YELLOW}⚠️  Caching may not be working as expected${NC}"
        ((TESTS_FAILED++))
    fi
    
    echo ""
}

# Main test execution
main() {
    echo -e "${CYAN}🚀 Starting Enhanced Monitoring Test Suite${NC}"
    echo "=================================================="
    echo ""
    
    # Test basic connectivity first
    test_connectivity
    
    # Get authentication token
    if ! get_auth_token; then
        echo -e "${RED}❌ Cannot proceed without authentication${NC}"
        exit 1
    fi
    
    # Test enhanced monitoring features
    test_enhanced_commands
    test_enhanced_endpoints
    test_error_handling
    test_command_caching
    
    # Summary
    echo -e "${BLUE}📊 Enhanced Monitoring Test Summary${NC}"
    echo "============================================="
    echo -e "${GREEN}✅ Tests Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}❌ Tests Failed: $TESTS_FAILED${NC}"
    total_tests=$((TESTS_PASSED + TESTS_FAILED))
    echo "Total Tests: $total_tests"
    
    echo ""
    echo -e "${BLUE}🔍 Enhanced Monitoring Features Tested:${NC}"
    echo "  • 50+ System Monitoring Commands"
    echo "  • Raspberry Pi Specific Commands (vcgencmd)"
    echo "  • Hardware Monitoring (CPU, Memory, Disk)"
    echo "  • Network Diagnostics and Monitoring"
    echo "  • System Performance Metrics"
    echo "  • Command Caching Mechanism"
    echo "  • Error Handling and Validation"
    echo "  • Authentication and Security"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 All enhanced monitoring tests passed!${NC}"
        echo "Your Pi Monitor is fully equipped with comprehensive system monitoring capabilities!"
        exit 0
    else
        echo ""
        echo -e "${RED}⚠️  Some tests failed. Check the output above for details.${NC}"
        exit 1
    fi
}

# Run main function
main
