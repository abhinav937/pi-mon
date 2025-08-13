#!/usr/bin/env bash
# Debug script to identify backend EXEC error

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🐛 Backend Debug Script${NC}"
echo "=========================="

PI_MON_DIR="/home/abhinav/pi-mon"
VENV_DIR="$PI_MON_DIR/.venv"
BACKEND_DIR="$PI_MON_DIR/backend"

# Check if running as root
if [[ "$EUID" -ne 0 ]]; then
  echo -e "${RED}❌ This script must be run with sudo${NC}"
  exit 1
fi

echo -e "\n${BLUE}1. File existence check...${NC}"
ls -la "$BACKEND_DIR/start_service.py"
ls -la "$VENV_DIR/bin/python"

echo -e "\n${BLUE}2. File permissions...${NC}"
ls -la "$BACKEND_DIR/"
ls -la "$VENV_DIR/bin/"

echo -e "\n${BLUE}3. Testing Python directly...${NC}"
echo "Testing: $VENV_DIR/bin/python --version"
"$VENV_DIR/bin/python" --version

echo -e "\n${BLUE}4. Testing Python with absolute path...${NC}"
echo "Testing: $VENV_DIR/bin/python $BACKEND_DIR/start_service.py"
timeout 5s "$VENV_DIR/bin/python" "$BACKEND_DIR/start_service.py" || echo "Command completed (expected timeout)"

echo -e "\n${BLUE}5. Testing imports step by step...${NC}"
echo "Testing basic Python:"
"$VENV_DIR/bin/python" -c "print('Python is working')"

echo "Testing sys import:"
"$VENV_DIR/bin/python" -c "import sys; print('sys imported'); print('Python path:', sys.path)"

echo "Testing os import:"
"$VENV_DIR/bin/python" -c "import os; print('os imported'); print('Current dir:', os.getcwd())"

echo "Testing pathlib import:"
"$VENV_DIR/bin/python" -c "import pathlib; print('pathlib imported')"

echo -e "\n${BLUE}6. Testing start_service.py imports...${NC}"
cd "$BACKEND_DIR"
echo "Current directory: $(pwd)"

echo "Testing start_service.py line by line:"
"$VENV_DIR/bin/python" -c "
import sys
print('1. sys imported')
sys.path.append('$(pwd)')
print('2. Added current dir to path')
print('3. Python path:', sys.path)
import start_service
print('4. start_service imported successfully')
"

echo -e "\n${BLUE}7. Checking for syntax errors...${NC}"
"$VENV_DIR/bin/python" -m py_compile start_service.py && echo "✅ No syntax errors" || echo "❌ Syntax errors found"

echo -e "\n${BLUE}8. Testing with shebang...${NC}"
echo "Testing if start_service.py has proper shebang:"
head -1 start_service.py

echo -e "\n${BLUE}9. Testing environment...${NC}"
echo "Environment variables:"
env | grep -E "(PYTHON|PATH|HOME)" | head -10

echo -e "\n${BLUE}10. Testing as abhinav user...${NC}"
sudo -u abhinav "$VENV_DIR/bin/python" "$BACKEND_DIR/start_service.py" &
PID=$!
sleep 3
if kill -0 $PID 2>/dev/null; then
    echo "✅ Script runs as abhinav user"
    kill $PID
else
    echo "❌ Script failed as abhinav user"
fi

echo -e "\n${GREEN}🎯 Debug complete!${NC}"
echo "Check the output above for any error messages."
