#!/bin/bash

# Quick Pi Monitor Backend Test
# Run this on your Pi to quickly test basic functionality

echo "🔍 Quick Pi Monitor Backend Test"
echo "=================================="
echo

# Test 1: Python availability
echo "1. Testing Python..."
if command -v python3 >/dev/null 2>&1; then
    echo "   ✅ Python3 found: $(python3 --version)"
else
    echo "   ❌ Python3 not found"
    exit 1
fi

# Test 2: Required packages
echo "2. Testing Python packages..."
python3 -c "import psutil" 2>/dev/null && echo "   ✅ psutil available" || echo "   ❌ psutil missing"
python3 -c "import subprocess" 2>/dev/null && echo "   ✅ subprocess available" || echo "   ❌ subprocess missing"
python3 -c "import json" 2>/dev/null && echo "   ✅ json available" || echo "   ❌ json missing"

# Test 3: System commands
echo "3. Testing system commands..."
cat /proc/loadavg >/dev/null 2>&1 && echo "   ✅ /proc/loadavg readable" || echo "   ❌ /proc/loadavg not readable"
free -h >/dev/null 2>&1 && echo "   ✅ free command works" || echo "   ❌ free command failed"
df -h >/dev/null 2>&1 && echo "   ✅ df command works" || echo "   ❌ df command failed"

# Test 4: Raspberry Pi specific
echo "4. Testing Raspberry Pi commands..."
if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp >/dev/null 2>&1 && echo "   ✅ vcgencmd temperature works" || echo "   ❌ vcgencmd temperature failed"
    vcgencmd measure_clock arm >/dev/null 2>&1 && echo "   ✅ vcgencmd clock works" || echo "   ❌ vcgencmd clock failed"
else
    echo "   ⚠️  vcgencmd not available (not a Pi or not in PATH)"
fi

# Test 5: Network
echo "5. Testing network..."
ping -c 1 localhost >/dev/null 2>&1 && echo "   ✅ localhost ping works" || echo "   ❌ localhost ping failed"
ping -c 1 8.8.8.8 >/dev/null 2>&1 && echo "   ✅ external network works" || echo "   ❌ external network failed"

# Test 6: Port availability
echo "6. Testing port 5001..."
if netstat -tuln 2>/dev/null | grep -q ":5001 "; then
    echo "   ⚠️  Port 5001 is already in use"
else
    echo "   ✅ Port 5001 is available"
fi

# Test 7: Python script
echo "7. Testing Python script..."
if [ -f "backend/simple_server.py" ]; then
    python3 -m py_compile backend/simple_server.py 2>/dev/null && echo "   ✅ Script syntax OK" || echo "   ❌ Script has syntax errors"
else
    echo "   ❌ Script not found at backend/simple_server.py"
fi

echo
echo "=================================="
echo "Quick test complete!"
echo
echo "If all tests passed, try starting the backend:"
echo "  python3 backend/simple_server.py"
echo
echo "If some tests failed, run the full test script:"
echo "  ./test_backend_functions.sh"
