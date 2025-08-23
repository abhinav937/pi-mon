#!/bin/bash
# Quick WebAuthn Test Script
# Automatically sets up environment and runs tests

set -e

echo "🚀 Quick WebAuthn Test for Pi Monitor"

# Check if we're in the right directory
if [ ! -f "../backend/webauthn_manager.py" ]; then
    echo "❌ Please run this script from the tests/ directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../backend/venv" ]; then
    echo "📦 Virtual environment not found. Setting up..."
    ./setup_venv.sh
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source ../backend/venv/bin/activate

# Run simple tests first
echo "🧪 Running simple tests..."
python3 test_webauthn_simple.py

# If simple tests pass, run full test suite
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Simple tests passed! Running full test suite..."
    python3 run_webauthn_tests.py
else
    echo "❌ Simple tests failed. Check the output above."
    exit 1
fi
