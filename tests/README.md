# Pi Monitor - WebAuthn Test Suite

This directory contains comprehensive tests for the WebAuthn (passkey) implementation in Pi Monitor.

## 🚀 Quick Start

### Windows
```cmd
cd tests
quick_test.bat
```

### Linux/macOS
```bash
cd tests
chmod +x *.sh
./quick_test.sh
```

## 📋 Test Files

- **`test_webauthn_simple.py`** - Basic functionality tests (no mocking)
- **`test_webauthn.py`** - Full test suite with comprehensive mocking
- **`run_webauthn_tests.py`** - Test runner with different test options
- **`setup_venv.bat/.sh`** - Virtual environment setup scripts
- **`quick_test.bat/.sh`** - One-command test execution

## 🧪 Running Tests

### 1. Setup Environment (First Time)
```bash
# Windows
setup_venv.bat

# Linux/macOS
./setup_venv.sh
```

### 2. Run Simple Tests
```bash
# Activate virtual environment first
..\backend\venv\Scripts\activate.bat  # Windows
source ../backend/venv/bin/activate    # Linux/macOS

# Run tests
python test_webauthn_simple.py
```

### 3. Run Full Test Suite
```bash
python run_webauthn_tests.py
```

### 4. Run Specific Tests
```bash
# Unit tests only
python run_webauthn_tests.py --unit

# Server tests only
python run_webauthn_tests.py --server

# Integration tests only
python run_webauthn_tests.py --integration

# Browser tests only
python run_webauthn_tests.py --browser
```

## 🔍 What Gets Tested

### Core Functionality
- ✅ WebAuthn manager initialization
- ✅ Configuration loading
- ✅ Database connectivity
- ✅ JWT token generation/verification
- ✅ Base64 conversions

### Registration Flow
- ✅ User creation
- ✅ Registration options generation
- ✅ Credential verification
- ✅ Database storage

### Authentication Flow
- ✅ Authentication options generation
- ✅ Credential verification
- ✅ Session management
- ✅ Challenge handling

### Error Handling
- ✅ Missing challenges
- ✅ Invalid credentials
- ✅ Expired tokens
- ✅ Database failures

## 🐛 Troubleshooting

### Virtual Environment Issues
```bash
# Remove and recreate
rmdir /s /q ..\backend\venv  # Windows
rm -rf ../backend/venv        # Linux/macOS

# Then run setup again
setup_venv.bat  # or setup_venv.sh
```

### Dependency Issues
```bash
# Activate venv first, then:
pip install --upgrade pip
pip install webauthn>=1.11.0 cbor2>=5.4.6 pyjwt>=2.8.0
```

### Import Errors
- Ensure you're running from the `tests/` directory
- Check that the virtual environment is activated
- Verify all dependencies are installed

## 📊 Test Results

Tests will show:
- ✅ **PASS** - Functionality working correctly
- ❌ **FAIL** - Issues found that need fixing
- ⚠️ **ERROR** - Exceptions or crashes

## 🔧 Manual Testing

After running automated tests, you can manually test:

1. **Start Backend Server**
   ```bash
   cd ../backend
   python server.py
   ```

2. **Start Frontend**
   ```bash
   cd ../frontend
   npm start
   ```

3. **Test in Browser**
   - Go to `http://localhost:3000`
   - Try passkey registration
   - Try passkey authentication
   - Check browser console for errors

## 📝 Test Configuration

See `test_config.json` for test environment configuration and test scenarios.

## 🎯 Next Steps

1. Run the test suite locally
2. Fix any issues found
3. Test manually in browser
4. Deploy to Raspberry Pi
5. Run tests on Pi to verify functionality
