#!/usr/bin/env python3
"""
Pi Monitor - WebAuthn Test Runner
Easy-to-use script to run WebAuthn tests locally on x86 machines
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import webauthn
        print(f"✅ WebAuthn library: {webauthn.__version__}")
    except ImportError:
        print("❌ WebAuthn library not installed")
        print("   Install with: pip install webauthn>=1.11.0")
        return False
    
    try:
        import cbor2
        print(f"✅ CBOR2 library: {cbor2.__version__}")
    except ImportError:
        print("❌ CBOR2 library not installed")
        print("   Install with: pip install cbor2>=5.4.6")
        return False
    
    try:
        import jwt
        print(f"✅ PyJWT library: {jwt.__version__}")
    except ImportError:
        print("❌ PyJWT library not installed")
        print("   Install with: pip install pyjwt>=2.8.0")
        return False
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "webauthn>=1.11.0", "cbor2>=5.4.6", "pyjwt>=2.8.0"
        ], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def run_unit_tests():
    """Run unit tests"""
    print("\n🧪 Running unit tests...")
    
    test_file = Path(__file__).parent / "test_webauthn.py"
    
    try:
        result = subprocess.run([
            sys.executable, str(test_file)
        ], check=False)
        
        if result.returncode == 0:
            print("✅ Unit tests passed!")
            return True
        else:
            print("❌ Unit tests failed!")
            return False
    except Exception as e:
        print(f"❌ Error running unit tests: {e}")
        return False

def run_integration_tests():
    """Run integration tests"""
    print("\n🔗 Running integration tests...")
    
    # Set environment variable for integration tests
    env = os.environ.copy()
    env['INTEGRATION_TESTS'] = '1'
    
    test_file = Path(__file__).parent / "test_webauthn.py"
    
    try:
        result = subprocess.run([
            sys.executable, str(test_file)
        ], env=env, check=False)
        
        if result.returncode == 0:
            print("✅ Integration tests passed!")
            return True
        else:
            print("❌ Integration tests failed!")
            return False
    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return False

def run_browser_tests():
    """Run browser-based tests"""
    print("\n🌐 Running browser tests...")
    
    # Check if we're in a browser environment
    try:
        import webbrowser
        print("✅ Browser environment detected")
        
        # Open test page
        test_url = "http://localhost:3000"
        print(f"🌐 Opening test page: {test_url}")
        
        try:
            webbrowser.open(test_url)
            print("✅ Test page opened in browser")
            print("   Please test the WebAuthn functionality manually:")
            print("   1. Try to register a new passkey")
            print("   2. Try to authenticate with the passkey")
            print("   3. Check browser console for any errors")
        except Exception as e:
            print(f"❌ Failed to open browser: {e}")
            return False
        
        return True
    except ImportError:
        print("❌ Browser environment not available")
        return False

def run_server_tests():
    """Run server integration tests"""
    print("\n🚀 Running server tests...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    
    try:
        # Test server startup
        print("   Testing server startup...")
        result = subprocess.run([
            sys.executable, "debug_startup.py"
        ], cwd=backend_dir, check=False, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Server startup test passed!")
        else:
            print("❌ Server startup test failed!")
            print(f"   Error: {result.stderr}")
            return False
        
        # Test WebAuthn manager import
        print("   Testing WebAuthn manager...")
        result = subprocess.run([
            sys.executable, "-c", 
            "from webauthn_manager import WebAuthnManager; print('✅ WebAuthn manager imported successfully')"
        ], cwd=backend_dir, check=False, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ WebAuthn manager test passed!")
        else:
            print("❌ WebAuthn manager test failed!")
            print(f"   Error: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error running server tests: {e}")
        return False

def run_all_tests():
    """Run all test suites"""
    print("🚀 Pi Monitor - WebAuthn Test Suite")
    print("=" * 50)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependencies missing. Installing...")
        if not install_dependencies():
            print("❌ Failed to install dependencies. Exiting.")
            return False
    
    print("\n✅ All dependencies available!")
    
    # Run tests
    tests = [
        ("Unit Tests", run_unit_tests),
        ("Server Tests", run_server_tests),
        ("Integration Tests", run_integration_tests),
        ("Browser Tests", run_browser_tests)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests passed! WebAuthn implementation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run WebAuthn tests for Pi Monitor")
    parser.add_argument(
        "--unit", action="store_true", 
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", action="store_true", 
        help="Run only integration tests"
    )
    parser.add_argument(
        "--server", action="store_true", 
        help="Run only server tests"
    )
    parser.add_argument(
        "--browser", action="store_true", 
        help="Run only browser tests"
    )
    parser.add_argument(
        "--install-deps", action="store_true",
        help="Install dependencies and exit"
    )
    
    args = parser.parse_args()
    
    if args.install_deps:
        if install_dependencies():
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies")
            return False
    
    if args.unit:
        return run_unit_tests()
    elif args.integration:
        return run_integration_tests()
    elif args.server:
        return run_server_tests()
    elif args.browser:
        return run_browser_tests()
    else:
        return run_all_tests()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
