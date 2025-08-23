#!/bin/bash
# Pi Monitor - WebAuthn Test Environment Setup
# Sets up virtual environment and installs dependencies for testing

set -e  # Exit on any error

echo "🚀 Setting up Pi Monitor WebAuthn test environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "../backend/webauthn_manager.py" ]; then
    print_error "Please run this script from the tests/ directory"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
print_status "Python version: $PYTHON_VERSION"

# Extract major and minor version numbers
MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)

# Check if Python version is 3.8 or higher
if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 8 ]); then
    print_error "Python 3.8+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

print_success "Python version $PYTHON_VERSION is compatible"

# Check if virtual environment already exists
if [ -d "../backend/venv" ]; then
    print_warning "Virtual environment already exists at ../backend/venv"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing existing virtual environment..."
        rm -rf ../backend/venv
    else
        print_status "Using existing virtual environment"
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "../backend/venv" ]; then
    print_status "Creating virtual environment..."
    cd ../backend
    python3 -m venv venv
    cd ../tests
    print_success "Virtual environment created at ../backend/venv"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source ../backend/venv/bin/activate

# Verify virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

print_success "Virtual environment activated: $VIRTUAL_ENV"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install required dependencies
print_status "Installing WebAuthn dependencies..."
pip install webauthn>=1.11.0 cbor2>=5.4.6 pyjwt>=2.8.0

# Install additional testing dependencies
print_status "Installing testing dependencies..."
pip install pytest pytest-cov pytest-mock

# Verify installations
print_status "Verifying installations..."
python3 -c "
import webauthn
import cbor2
import jwt
print(f'✅ WebAuthn: {webauthn.__version__}')
print(f'✅ CBOR2: {cbor2.__version__}')
print(f'✅ PyJWT: {jwt.__version__}')
"

print_success "All dependencies installed successfully!"

# Create activation script for easy use
cat > activate_test_env.sh << 'EOF'
#!/bin/bash
# Quick activation script for testing environment
echo "🚀 Activating Pi Monitor test environment..."
source ../backend/venv/bin/activate
echo "✅ Test environment activated!"
echo "   Run tests with: python3 run_webauthn_tests.py"
echo "   Deactivate with: deactivate"
EOF

chmod +x activate_test_env.sh

print_success "Test environment setup complete!"
echo
echo "📋 Next steps:"
echo "1. Activate the environment: source activate_test_env.sh"
echo "2. Run tests: python3 run_webauthn_tests.py"
echo "3. Or run specific tests:"
echo "   - Unit tests: python3 run_webauthn_tests.py --unit"
echo "   - Server tests: python3 run_webauthn_tests.py --server"
echo "   - All tests: python3 run_webauthn_tests.py"
echo
echo "🔧 To deactivate: deactivate"
echo "🔧 To remove environment: rm -rf ../backend/venv"
