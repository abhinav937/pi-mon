#!/usr/bin/env python3
"""
Pi Monitor - Simple WebAuthn Test
Basic functionality testing without complex mocking
"""

import os
import sys
import json
import base64
import hashlib
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_imports():
    """Test if we can import the required modules"""
    print("🧪 Testing imports...")
    
    try:
        from webauthn_manager import WebAuthnManager
        print("✅ WebAuthnManager imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import WebAuthnManager: {e}")
        return False

def test_webauthn_library():
    """Test if WebAuthn library is available"""
    print("\n🧪 Testing WebAuthn library...")
    
    try:
        import webauthn
        print(f"✅ WebAuthn library available: {webauthn.__version__}")
        
        # Test basic functions
        from webauthn import generate_registration_options, generate_authentication_options
        print("✅ Core WebAuthn functions available")
        return True
    except ImportError as e:
        print(f"❌ WebAuthn library not available: {e}")
        print("   Install with: pip install webauthn>=1.11.0")
        return False

def test_dependencies():
    """Test if all dependencies are available"""
    print("\n🧪 Testing dependencies...")
    
    dependencies = [
        ('cbor2', 'CBOR2 library'),
        ('jwt', 'PyJWT library'),
        ('sqlite3', 'SQLite3 (built-in)'),
        ('hashlib', 'Hashlib (built-in)'),
        ('base64', 'Base64 (built-in)')
    ]
    
    all_available = True
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            print(f"✅ {description} available")
        except ImportError:
            print(f"❌ {description} not available")
            all_available = False
    
    return all_available

def test_config_loading():
    """Test configuration loading"""
    print("\n🧪 Testing configuration...")
    
    try:
        from config import config
        print("✅ Config loaded successfully")
        
        # Test some config values
        domain = config.get('deployment_defaults.domain')
        if domain:
            print(f"   Domain: {domain}")
        
        api_base = config.get('urls.production.api_base')
        if api_base:
            print(f"   API Base: {api_base}")
        
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_database_connection():
    """Test database connectivity"""
    print("\n🧪 Testing database...")
    
    try:
        from auth_database import AuthDatabase
        
        # Try to create a database instance
        db = AuthDatabase()
        print("✅ Database instance created successfully")
        
        # Test table initialization
        db.init_auth_tables()
        print("✅ Database tables initialized")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_webauthn_manager_creation():
    """Test WebAuthn manager creation"""
    print("\n🧪 Testing WebAuthn manager creation...")
    
    try:
        # Set test environment variables
        os.environ['WEBAUTHN_RP_ID'] = 'localhost'
        os.environ['WEBAUTHN_ORIGIN'] = 'http://localhost'
        os.environ['JWT_SECRET'] = 'test-secret-123'
        
        from webauthn_manager import WebAuthnManager
        
        manager = WebAuthnManager()
        print("✅ WebAuthn manager created successfully")
        print(f"   RP ID: {manager.rp_id}")
        print(f"   Origin: {manager.origin}")
        print(f"   RP Name: {manager.rp_name}")
        
        return True
    except Exception as e:
        print(f"❌ WebAuthn manager creation failed: {e}")
        return False

def test_basic_functionality():
    """Test basic WebAuthn functionality"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        from webauthn_manager import WebAuthnManager
        
        manager = WebAuthnManager()
        
        # Test JWT token generation
        user_id = "test-user-123"
        token = manager.generate_jwt_token(user_id, expires_hours=1)
        print("✅ JWT token generated successfully")
        
        # Test token verification
        payload = manager.verify_jwt_token(token)
        if payload and payload.get('user_id') == user_id:
            print("✅ JWT token verification successful")
        else:
            print("❌ JWT token verification failed")
            return False
        
        # Test base64 conversions
        test_data = b"Hello, WebAuthn!"
        base64url = manager._base64_to_base64url(test_data)
        decoded = manager._base64url_to_base64(base64url)
        if base64.b64decode(decoded) == test_data:
            print("✅ Base64 conversions working correctly")
        else:
            print("❌ Base64 conversions failed")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Pi Monitor - Simple WebAuthn Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("WebAuthn Library", test_webauthn_library),
        ("Dependencies", test_dependencies),
        ("Configuration", test_config_loading),
        ("Database", test_database_connection),
        ("WebAuthn Manager", test_webauthn_manager_creation),
        ("Basic Functionality", test_basic_functionality)
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
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! WebAuthn implementation is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
