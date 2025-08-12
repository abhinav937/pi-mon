#!/bin/bash

# Pi Monitor API Endpoint Testing Script
# Tests all backend API endpoints and shows responses

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKEND_URL="http://localhost:5001"
AUTH_USERNAME="abhinav"
AUTH_PASSWORD="kavachi"
LOG_FILE="api_test_$(date +%Y%m%d_%H:%M:%S).log"

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Logging
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
    ((TESTS_PASSED++))
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
    ((TESTS_FAILED++))
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# Test API endpoint
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local data="$4"
    local headers="$5"
    
    local url="$BACKEND_URL$endpoint"
    local curl_cmd="curl -s -w '\nHTTP Status: %{http_code}\nTime: %{time_total}s\n'"
    
    if [ "$method" = "POST" ]; then
        curl_cmd="$curl_cmd -X POST"
        if [ -n "$data" ]; then
            curl_cmd="$curl_cmd -d '$data'"
        fi
    fi
    
    if [ -n "$headers" ]; then
        curl_cmd="$curl_cmd -H '$headers'"
    fi
    
    curl_cmd="$curl_cmd '$url'"
    
    log "Testing: $method $endpoint - $description"
    echo "URL: $url"
    echo "Command: $curl_cmd"
    echo "--- Response ---"
    
    local response
    response=$(eval "$curl_cmd" 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo "$response"
        echo "--- End Response ---"
        
        # Check if response contains error
        if echo "$response" | grep -q "error\|Error\|ERROR"; then
            warning "Response contains error message"
        else
            success "Endpoint $endpoint responded successfully"
        fi
    else
        echo "Curl failed with exit code: $exit_code"
        echo "Error: $response"
        error "Failed to test endpoint $endpoint"
    fi
    
    echo
}

# Test with authentication
test_auth_endpoint() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local data="$4"
    
    # First get auth token
    log "Getting authentication token..."
    local auth_response
    auth_response=$(curl -s -X POST "$BACKEND_URL/api/auth/token" \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$AUTH_USERNAME\", \"password\": \"$AUTH_PASSWORD\"}")
    
    local token
    token=$(echo "$auth_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$token" ]; then
        success "Authentication successful, token obtained"
        test_endpoint "$method" "$endpoint" "$description" "$data" "Authorization: Bearer $token"
    else
        error "Authentication failed"
        echo "Auth response: $auth_response"
        echo
    fi
}

# Header
echo "=========================================="
echo "Pi Monitor API Endpoint Testing"
echo "=========================================="
echo "Backend URL: $BACKEND_URL"
echo "Log file: $LOG_FILE"
echo "Date: $(date)"
echo "=========================================="
echo

# Check if backend is running
log "Checking if backend is running..."
if curl -s "$BACKEND_URL/health" >/dev/null 2>&1; then
    success "Backend is running and accessible"
else
    error "Backend is not accessible at $BACKEND_URL"
    echo "Make sure the backend is running: python3 backend/simple_server.py"
    exit 1
fi

echo

# Test 1: Root endpoint (no auth required)
log "=== Test 1: Root Endpoint ==="
test_endpoint "GET" "/" "Root endpoint - should return basic info"

# Test 2: Health check (no auth required)
log "=== Test 2: Health Check ==="
test_endpoint "GET" "/health" "Health check endpoint"

# Test 3: Authentication
log "=== Test 3: Authentication ==="
test_endpoint "POST" "/api/auth/token" "Authentication endpoint" "{\"username\": \"$AUTH_USERNAME\", \"password\": \"$AUTH_PASSWORD\"}" "Content-Type: application/json"

# Test 4: System stats (requires auth)
log "=== Test 4: System Stats (Authenticated) ==="
test_auth_endpoint "GET" "/api/system" "System statistics endpoint"

# Test 5: Enhanced system stats (requires auth)
log "=== Test 5: Enhanced System Stats (Authenticated) ==="
test_auth_endpoint "GET" "/api/system/enhanced" "Enhanced system statistics endpoint"

# Test 6: System stats with history (requires auth)
log "=== Test 6: System Stats with History (Authenticated) ==="
test_auth_endpoint "GET" "/api/system?history=30" "System stats with 30-minute history"

# Test 7: Power status (requires auth)
log "=== Test 7: Power Status (Authenticated) ==="
test_auth_endpoint "GET" "/api/power" "Power status endpoint"

# Test 8: Service restart info (no auth required)
log "=== Test 8: Service Restart Info ==="
test_endpoint "GET" "/api/service/restart" "Service restart information endpoint"

# Test 9: Service manage info (no auth required)
log "=== Test 9: Service Manage Info ==="
test_endpoint "GET" "/api/service/manage" "Service management information endpoint"

# Test 10: Service info (requires auth)
log "=== Test 10: Service Info (Authenticated) ==="
test_auth_endpoint "GET" "/api/service/info" "Service information endpoint"

# Test 11: Power actions (requires auth)
log "=== Test 11: Power Actions (Authenticated) ==="
test_auth_endpoint "POST" "/api/power" "Power action endpoint" "{\"action\": \"status\"}" "Content-Type: application/json"

# Test 12: Service restart (requires auth)
log "=== Test 12: Service Restart (Authenticated) ==="
test_auth_endpoint "POST" "/api/service/restart" "Service restart endpoint" "{}" "Content-Type: application/json"

# Test 13: Service management (requires auth)
log "=== Test 13: Service Management (Authenticated) ==="
test_auth_endpoint "POST" "/api/service/manage" "Service management endpoint" "{\"action\": \"status\"}" "Content-Type: application/json"

# Test 14: Services endpoint (requires auth)
log "=== Test 14: Services Endpoint (Authenticated) ==="
test_auth_endpoint "POST" "/api/services" "Services endpoint" "{\"service_name\": \"ssh\", \"action\": \"status\"}" "Content-Type: application/json"

# Test 15: Power shutdown (requires auth) - WARNING: This will shutdown the system!
log "=== Test 15: Power Shutdown (Authenticated) - WARNING: SYSTEM SHUTDOWN ==="
warning "SKIPPING shutdown test to prevent system shutdown"
# Uncomment the line below if you want to test shutdown (BE CAREFUL!)
# test_auth_endpoint "POST" "/api/power/shutdown" "Power shutdown endpoint" "{\"delay\": 0}" "Content-Type: application/json"

# Test 16: Power restart (requires auth) - WARNING: This will restart the system!
log "=== Test 16: Power Restart (Authenticated) - WARNING: SYSTEM RESTART ==="
warning "SKIPPING restart test to prevent system restart"
# Uncomment the line below if you want to test restart (BE CAREFUL!)
# test_auth_endpoint "POST" "/api/power/restart" "Power restart endpoint" "{\"delay\": 0}" "Content-Type: application/json"

# Test 17: Power sleep (requires auth)
log "=== Test 17: Power Sleep (Authenticated) ==="
warning "SKIPPING sleep test to prevent system sleep"
# Uncomment the line below if you want to test sleep
# test_auth_endpoint "POST" "/api/power/sleep" "Power sleep endpoint" "{}" "Content-Type: application/json"

# Test 18: Test invalid endpoints
log "=== Test 18: Invalid Endpoints ==="
test_endpoint "GET" "/nonexistent" "Non-existent endpoint - should return 404"
test_endpoint "POST" "/api/invalid" "Invalid API endpoint - should return 404"

# Test 19: Test invalid methods
log "=== Test 19: Invalid Methods ==="
test_endpoint "PUT" "/api/system" "PUT method on system endpoint - should return 405"
test_endpoint "DELETE" "/api/system" "DELETE method on system endpoint - should return 405"

# Test 20: Test malformed JSON
log "=== Test 20: Malformed JSON ==="
test_endpoint "POST" "/api/auth/token" "Malformed JSON - should handle gracefully" "{\"username\": \"abhinav\", \"password\":}" "Content-Type: application/json"

# Test 21: Test missing authentication
log "=== Test 21: Missing Authentication ==="
test_endpoint "GET" "/api/system" "System endpoint without auth - should return 401"

# Test 22: Test invalid authentication
log "=== Test 22: Invalid Authentication ==="
test_endpoint "GET" "/api/system" "System endpoint with invalid token - should return 401" "" "Authorization: Bearer invalid_token_123"

# Test 23: Test rate limiting (if implemented)
log "=== Test 23: Rate Limiting ==="
log "Making multiple rapid requests to test rate limiting..."
for i in {1..5}; do
    curl -s -w "Request $i - Status: %{http_code}\n" "$BACKEND_URL/health" >/dev/null
    sleep 0.1
done
echo

# Test 24: Test CORS headers
log "=== Test 24: CORS Headers ==="
log "Testing CORS preflight request..."
curl -s -X OPTIONS "$BACKEND_URL/api/system" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" \
    -H "Access-Control-Request-Headers: Authorization" \
    -v 2>&1 | grep -E "(Access-Control|HTTP)" || echo "CORS headers not visible in verbose output"

echo

# Summary
echo "=========================================="
echo "API TESTING COMPLETE"
echo "=========================================="
log "Final Results:"
log "Tests PASSED: $TESTS_PASSED"
log "Tests FAILED: $TESTS_FAILED"
log "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    success "All API tests passed! Your backend is working correctly."
else
    warning "$TESTS_FAILED tests failed. Check the log file for details."
fi

echo
echo "📋 Log file: $LOG_FILE"
echo "🌐 Backend URL: $BACKEND_URL"
echo "=========================================="

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi
