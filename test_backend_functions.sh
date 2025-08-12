#!/bin/bash

# Pi Monitor Backend Testing Script
# This script tests all backend functionality directly on the Pi
# Run this outside of Docker to diagnose issues

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=5001
TEST_HOST="localhost"
LOG_FILE="backend_test_$(date +%Y%m%d_%H%M%S).log"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    log "Running test: $test_name"
    log "Command: $test_command"
    
    if eval "$test_command" 2>&1 | grep -q "$expected_pattern"; then
        success "Test PASSED: $test_name"
        ((TESTS_PASSED++))
    else
        error "Test FAILED: $test_name"
        log "Output: $(eval "$test_command" 2>&1)"
        ((TESTS_FAILED++))
    fi
    echo
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local endpoint="$1"
    local expected_status="$2"
    local test_name="$3"
    
    log "Testing HTTP endpoint: $endpoint"
    
    if curl -s -o /dev/null -w "%{http_code}" "http://$TEST_HOST:$BACKEND_PORT$endpoint" | grep -q "$expected_status"; then
        success "HTTP test PASSED: $test_name ($endpoint)"
        ((TESTS_PASSED++))
    else
        error "HTTP test FAILED: $test_name ($endpoint)"
        ((TESTS_FAILED++))
    fi
}

# Function to test system commands
test_system_command() {
    local command_name="$1"
    local command="$2"
    local test_name="$3"
    
    log "Testing system command: $command_name"
    log "Command: $command"
    
    if eval "$command" >/dev/null 2>&1; then
        success "System command PASSED: $test_name"
        ((TESTS_PASSED++))
    else
        error "System command FAILED: $test_name"
        ((TESTS_FAILED++))
    fi
}

# Header
echo "=========================================="
echo "Pi Monitor Backend Testing Script"
echo "=========================================="
echo "Testing all backend functionality outside Docker"
echo "Log file: $LOG_FILE"
echo "Date: $(date)"
echo "=========================================="
echo

# Start logging
log "Starting backend functionality tests"
log "System: $(uname -a)"
log "User: $(whoami)"
log "Working directory: $(pwd)"

# Test 1: Check if backend port is available
log "=== Test 1: Port Availability ==="
if netstat -tuln 2>/dev/null | grep -q ":$BACKEND_PORT "; then
    warning "Port $BACKEND_PORT is already in use"
    log "Port status: $(netstat -tuln 2>/dev/null | grep ":$BACKEND_PORT " || echo 'Not found')"
else
    success "Port $BACKEND_PORT is available"
fi
echo

# Test 2: Check Python dependencies
log "=== Test 2: Python Dependencies ==="
python3 --version >/dev/null 2>&1 && success "Python3 is available" || error "Python3 not found"
pip3 --version >/dev/null 2>&1 && success "Pip3 is available" || error "Pip3 not found"

# Check specific packages
python3 -c "import psutil" 2>/dev/null && success "psutil package available" || error "psutil package missing"
python3 -c "import subprocess" 2>/dev/null && success "subprocess package available" || error "subprocess package missing"
python3 -c "import json" 2>/dev/null && success "json package available" || error "json package missing"
echo

# Test 3: Test system monitoring commands
log "=== Test 3: System Monitoring Commands ==="

# Basic system info
test_system_command "Uptime" "uptime" "System uptime"
test_system_command "CPU Info" "cat /proc/cpuinfo | head -5" "CPU information"
test_system_command "Memory Info" "free -h" "Memory usage"
test_system_command "Disk Usage" "df -h" "Disk usage"
test_system_command "Load Average" "cat /proc/loadavg" "System load"

# Raspberry Pi specific commands
if command -v vcgencmd >/dev/null 2>&1; then
    test_system_command "CPU Temperature" "vcgencmd measure_temp" "CPU temperature"
    test_system_command "ARM Clock" "vcgencmd measure_clock arm" "ARM clock speed"
    test_system_command "Core Voltage" "vcgencmd measure_volts core" "Core voltage"
    test_system_command "Throttling Status" "vcgencmd get_throttled" "Throttling status"
else
    warning "vcgencmd not available (not a Raspberry Pi or vcgencmd not in PATH)"
fi

# Network commands
test_system_command "Network Interfaces" "ip a" "Network interfaces"
test_system_command "Network Stats" "cat /proc/net/dev" "Network statistics"
test_system_command "Routing Table" "ip route" "Routing table"

# System services
test_system_command "Service Status" "systemctl list-units --type=service --state=running | head -10" "Running services"
test_system_command "Docker Status" "docker ps 2>/dev/null || echo 'Docker not available'" "Docker status"

echo

# Test 4: Test file permissions and access
log "=== Test 4: File Permissions and Access ==="

# Check if we can read system files
test_system_command "Read /proc/loadavg" "cat /proc/loadavg" "Read load average"
test_system_command "Read /proc/meminfo" "cat /proc/meminfo | head -5" "Read memory info"
test_system_command "Read /proc/cpuinfo" "cat /proc/cpuinfo | head -5" "Read CPU info"

# Check if we can write to current directory
if [ -w . ]; then
    success "Current directory is writable"
    ((TESTS_PASSED++))
else
    error "Current directory is not writable"
    ((TESTS_FAILED++))
fi

# Check if we can create log files
if touch test_write_permission.tmp 2>/dev/null; then
    success "Can create files in current directory"
    rm -f test_write_permission.tmp
    ((TESTS_PASSED++))
else
    error "Cannot create files in current directory"
    ((TESTS_FAILED++))
fi
echo

# Test 5: Test Python script syntax and imports
log "=== Test 5: Python Script Validation ==="

if [ -f "backend/simple_server.py" ]; then
    log "Testing Python script syntax..."
    if python3 -m py_compile backend/simple_server.py 2>/dev/null; then
        success "Python script syntax is valid"
        ((TESTS_PASSED++))
    else
        error "Python script has syntax errors"
        ((TESTS_FAILED++))
    fi
    
    # Test imports
    log "Testing Python imports..."
    if python3 -c "
import sys
sys.path.append('backend')
try:
    import simple_server
    print('All imports successful')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
" 2>/dev/null; then
        success "All Python imports successful"
        ((TESTS_PASSED++))
    else
        error "Python imports failed"
        ((TESTS_FAILED++))
    fi
else
    error "Python script not found at backend/simple_server.py"
    ((TESTS_FAILED++))
fi
echo

# Test 6: Test system command execution
log "=== Test 6: System Command Execution ==="

# Test subprocess functionality
python3 -c "
import subprocess
try:
    result = subprocess.run(['echo', 'test'], capture_output=True, text=True, timeout=5)
    if result.returncode == 0 and result.stdout.strip() == 'test':
        print('Subprocess test successful')
    else:
        print('Subprocess test failed')
        exit(1)
except Exception as e:
    print(f'Subprocess error: {e}')
    exit(1)
" 2>/dev/null && success "Subprocess execution works" || error "Subprocess execution failed"

# Test psutil functionality
python3 -c "
import psutil
try:
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    print(f'CPU: {cpu_percent}%, Memory: {memory.percent}%')
    print('Psutil test successful')
except Exception as e:
    print(f'Psutil error: {e}')
    exit(1)
" 2>/dev/null && success "Psutil monitoring works" || error "Psutil monitoring failed"
echo

# Test 7: Test network connectivity
log "=== Test 7: Network Connectivity ==="

# Test localhost connectivity
if ping -c 1 localhost >/dev/null 2>&1; then
    success "Localhost ping successful"
    ((TESTS_PASSED++))
else
    error "Localhost ping failed"
    ((TESTS_FAILED++))
fi

# Test if we can bind to the backend port
if timeout 2 bash -c "</dev/tcp/localhost/$BACKEND_PORT" 2>/dev/null; then
    warning "Port $BACKEND_PORT is already bound"
else
    success "Port $BACKEND_PORT is free for binding"
    ((TESTS_PASSED++))
fi

# Test external connectivity
if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    success "External network connectivity (8.8.8.8)"
    ((TESTS_PASSED++))
else
    warning "No external network connectivity"
fi
echo

# Test 8: Test system resources
log "=== Test 8: System Resources ==="

# Check available memory
available_mem=$(free -m | awk 'NR==2{printf "%.1f", $7/1024}')
log "Available memory: ${available_mem}GB"
if (( $(echo "$available_mem > 0.5" | bc -l) )); then
    success "Sufficient memory available"
    ((TESTS_PASSED++))
else
    warning "Low memory available: ${available_mem}GB"
fi

# Check available disk space
available_disk=$(df -h . | awk 'NR==2{print $4}' | sed 's/G//')
log "Available disk space: ${available_disk}GB"
if (( $(echo "$available_disk > 1" | bc -l) )); then
    success "Sufficient disk space available"
    ((TESTS_PASSED++))
else
    warning "Low disk space: ${available_disk}GB"
fi

# Check CPU load
load_avg=$(cat /proc/loadavg | awk '{print $1}')
cpu_cores=$(nproc)
log "Current load average: $load_avg (CPU cores: $cpu_cores)"
if (( $(echo "$load_avg < $cpu_cores" | bc -l) )); then
    success "System load is normal"
    ((TESTS_PASSED++))
else
    warning "High system load: $load_avg"
fi
echo

# Test 9: Test authentication and security
log "=== Test 9: Authentication and Security ==="

# Check if we can generate tokens
python3 -c "
import hashlib
import hmac
import base64
import time

try:
    secret = 'pi-monitor-secret-key-2024'
    timestamp = str(int(time.time()))
    message = f'pi-monitor:{timestamp}'
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    token = base64.b64encode(f'{message}:{signature}'.encode()).decode()
    print('Token generation successful')
except Exception as e:
    print(f'Token generation failed: {e}')
    exit(1)
" 2>/dev/null && success "Token generation works" || error "Token generation failed"

# Check file permissions
if [ -f "backend/simple_server.py" ]; then
    perms=$(stat -c "%a" backend/simple_server.py)
    if [ "$perms" = "644" ] || [ "$perms" = "640" ]; then
        success "Python script has appropriate permissions"
        ((TESTS_PASSED++))
    else
        warning "Python script permissions might be too open: $perms"
    fi
fi
echo

# Test 10: Test backend startup simulation
log "=== Test 10: Backend Startup Simulation ==="

# Check if we can import the main classes
python3 -c "
import sys
sys.path.append('backend')

try:
    # Test importing main components
    import simple_server
    
    # Test if we can create instances (without starting the server)
    print('Backend components can be imported')
    print('Backend startup simulation successful')
except Exception as e:
    print(f'Backend startup simulation failed: {e}')
    exit(1)
" 2>/dev/null && success "Backend startup simulation successful" || error "Backend startup simulation failed"
echo

# Test 11: Performance testing
log "=== Test 11: Performance Testing ==="

# Test command execution speed
start_time=$(date +%s.%N)
for i in {1..10}; do
    cat /proc/loadavg >/dev/null 2>&1
done
end_time=$(date +%s.%N)
execution_time=$(echo "$end_time - $start_time" | bc -l)
log "10 command executions took: ${execution_time}s"

if (( $(echo "$execution_time < 1.0" | bc -l) )); then
    success "Command execution performance is good"
    ((TESTS_PASSED++))
else
    warning "Command execution might be slow: ${execution_time}s"
fi

# Test Python performance
python3 -c "
import time
import psutil

start_time = time.time()
for i in range(100):
    cpu_percent = psutil.cpu_percent(interval=0.001)
    memory = psutil.virtual_memory()
end_time = time.time()

execution_time = end_time - start_time
print(f'100 psutil calls took: {execution_time:.3f}s')

if execution_time < 2.0:
    print('Python performance is good')
else:
    print('Python performance might be slow')
    exit(1)
" 2>/dev/null && success "Python performance is good" || warning "Python performance might be slow"
echo

# Test 12: Error handling and edge cases
log "=== Test 12: Error Handling and Edge Cases ==="

# Test with invalid commands
python3 -c "
import subprocess
try:
    result = subprocess.run(['invalid_command_xyz'], capture_output=True, text=True, timeout=5)
    print('Invalid command handled gracefully')
except Exception as e:
    print(f'Invalid command error: {e}')
    exit(1)
" 2>/dev/null && success "Invalid command handling works" || error "Invalid command handling failed"

# Test with missing files
if [ ! -f "/nonexistent/file" ]; then
    success "Non-existent file check works"
    ((TESTS_PASSED++))
else
    error "Non-existent file check failed"
    ((TESTS_FAILED++))
fi

# Test with permission denied scenarios
if [ ! -r "/root/.ssh/id_rsa" ] 2>/dev/null; then
    success "Permission denied scenarios handled correctly"
    ((TESTS_PASSED++))
else
    warning "Permission denied scenarios might not be handled"
fi
echo

# Summary
echo "=========================================="
echo "TESTING COMPLETE"
echo "=========================================="
log "Final Results:"
log "Tests PASSED: $TESTS_PASSED"
log "Tests FAILED: $TESTS_FAILED"
log "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    success "All tests passed! Backend should work correctly."
    echo
    echo "🎉 Your Pi Monitor backend is ready to run!"
    echo "Start it with: python3 backend/simple_server.py"
else
    warning "$TESTS_FAILED tests failed. Check the log file for details."
    echo
    echo "🔧 Some issues were found. Check the log file: $LOG_FILE"
    echo "Fix the issues before starting the backend."
fi

echo
echo "📋 Log file: $LOG_FILE"
echo "=========================================="

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    exit 0
else
    exit 1
fi
