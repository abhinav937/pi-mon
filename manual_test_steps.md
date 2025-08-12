# Pi Monitor Backend Manual Testing Guide

This guide will help you test your backend functionality step by step on your Pi, outside of Docker.

## Prerequisites
- SSH into your Pi or use terminal directly on Pi
- Navigate to your project directory: `cd /path/to/pi-mon`

## Step 1: Check System Status
```bash
# Check if you're on a Raspberry Pi
uname -a

# Check current user and permissions
whoami
id

# Check available disk space
df -h

# Check available memory
free -h

# Check system load
cat /proc/loadavg
```

## Step 2: Test Python Environment
```bash
# Check Python version
python3 --version

# Check pip version
pip3 --version

# Test basic Python functionality
python3 -c "print('Python is working')"

# Test required packages
python3 -c "import psutil; print('psutil version:', psutil.__version__)"
python3 -c "import subprocess; print('subprocess available')"
python3 -c "import json; print('json available')"
```

## Step 3: Test System Commands
```bash
# Test basic system monitoring
uptime
cat /proc/cpuinfo | head -5
cat /proc/meminfo | head -5
cat /proc/loadavg

# Test Raspberry Pi specific commands
vcgencmd measure_temp
vcgencmd measure_clock arm
vcgencmd get_throttled

# Test network commands
ip a
cat /proc/net/dev
ip route

# Test service commands
systemctl list-units --type=service --state=running | head -10
```

## Step 4: Test File Access
```bash
# Check if you can read system files
ls -la /proc/loadavg
ls -la /proc/meminfo
ls -la /proc/cpuinfo

# Check project file permissions
ls -la backend/
ls -la backend/simple_server.py

# Test if you can create files
touch test_file.tmp
ls -la test_file.tmp
rm test_file.tmp
```

## Step 5: Test Python Script
```bash
# Test script syntax
python3 -m py_compile backend/simple_server.py

# Test imports
python3 -c "
import sys
sys.path.append('backend')
try:
    import simple_server
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
"

# Test basic functionality
python3 -c "
import sys
sys.path.append('backend')
import simple_server

# Test if we can create instances
print('✅ Backend components can be imported')
"
```

## Step 6: Test Network and Ports
```bash
# Check if port 5001 is available
netstat -tuln | grep :5001

# Test localhost connectivity
ping -c 1 localhost

# Test external connectivity
ping -c 1 8.8.8.8

# Test if you can bind to the port
timeout 2 bash -c "</dev/tcp/localhost/5001" 2>/dev/null && echo "Port in use" || echo "Port available"
```

## Step 7: Test Performance
```bash
# Test command execution speed
time for i in {1..10}; do cat /proc/loadavg >/dev/null; done

# Test Python performance
python3 -c "
import time
import psutil

start_time = time.time()
for i in range(100):
    cpu_percent = psutil.cpu_percent(interval=0.001)
    memory = psutil.virtual_memory()
end_time = time.time()

print(f'100 psutil calls took: {end_time - start_time:.3f}s')
"
```

## Step 8: Test Error Handling
```bash
# Test with invalid commands
python3 -c "
import subprocess
try:
    result = subprocess.run(['invalid_command_xyz'], capture_output=True, text=True, timeout=5)
    print('✅ Invalid command handled gracefully')
except Exception as e:
    print(f'❌ Error: {e}')
"

# Test with missing files
python3 -c "
import os
if not os.path.exists('/nonexistent/file'):
    print('✅ Non-existent file check works')
else:
    print('❌ Non-existent file check failed')
"
```

## Step 9: Start Backend Manually
```bash
# Start the backend server
cd backend
python3 simple_server.py

# In another terminal, test the endpoints
curl http://localhost:5001/
curl http://localhost:5001/health
curl http://localhost:5001/api/system
```

## Step 10: Test Authentication
```bash
# Test authentication endpoint
curl -X POST http://localhost:5001/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "abhinav", "password": "kavachi"}'

# Use the returned token for authenticated requests
TOKEN="your_token_here"
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/system
```

## Troubleshooting Common Issues

### Issue: Permission Denied
```bash
# Check file permissions
ls -la backend/simple_server.py

# Fix permissions if needed
chmod 644 backend/simple_server.py

# Check if running as correct user
whoami
```

### Issue: Port Already in Use
```bash
# Find what's using the port
sudo netstat -tulpn | grep :5001

# Kill the process if needed
sudo kill -9 <PID>
```

### Issue: Missing Dependencies
```bash
# Install required packages
sudo apt update
sudo apt install python3-pip python3-psutil

# Or install via pip
pip3 install psutil
```

### Issue: Python Import Errors
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Add current directory to path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

## Expected Results

✅ **All tests should pass** if your backend is working correctly:
- Python and packages available
- System commands executable
- File permissions correct
- Network connectivity working
- Port 5001 available
- Script syntax valid
- Imports successful

❌ **If tests fail**, check:
- Python installation
- Package installation
- File permissions
- Network configuration
- Port conflicts
- Script syntax errors

## Next Steps

1. **If all tests pass**: Your backend is ready to run
2. **If some tests fail**: Fix the issues identified
3. **Run the full test script**: `./test_backend_functions.sh`
4. **Start the backend**: `python3 backend/simple_server.py`
5. **Test from frontend**: Access your web interface

## Quick Commands Summary

```bash
# Run quick test
./quick_test.sh

# Run full test
./test_backend_functions.sh

# Start backend
python3 backend/simple_server.py

# Test endpoints
curl http://localhost:5001/health
```
