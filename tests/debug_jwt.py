#!/usr/bin/env python3
"""
Debug JWT Token Issues
"""

import os
import sys
import jwt
import hashlib
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_jwt_directly():
    """Test JWT generation and verification directly"""
    print("🧪 Testing JWT directly...")
    
    # Test secret
    secret = "test-secret-123"
    
    # Generate token
    payload = {
        'user_id': 'test-user-123',
        'exp': datetime.utcnow() + timedelta(hours=1),
        'iat': datetime.utcnow(),
        'iss': 'pi-monitor'
    }
    
    token = jwt.encode(payload, secret, algorithm='HS256')
    print(f"✅ Token generated: {token[:50]}...")
    
    # Verify token
    try:
        decoded = jwt.decode(token, secret, algorithms=['HS256'])
        print(f"✅ Token verified: {decoded}")
        return True
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        return False

def test_webauthn_manager_jwt():
    """Test JWT through WebAuthn manager"""
    print("\n🧪 Testing JWT through WebAuthn manager...")
    
    try:
        from webauthn_manager import WebAuthnManager
        
        # Set test environment
        os.environ['WEBAUTHN_RP_ID'] = 'localhost'
        os.environ['WEBAUTHN_ORIGIN'] = 'http://localhost'
        os.environ['JWT_SECRET'] = 'test-secret-123'
        
        manager = WebAuthnManager()
        
        # Generate token
        user_id = "test-user-123"
        token = manager.generate_jwt_token(user_id, expires_hours=1)
        print(f"✅ Token generated: {token[:50]}...")
        
        # Try to verify token
        payload = manager.verify_jwt_token(token)
        if payload:
            print(f"✅ Token verified: {payload}")
            return True
        else:
            print("❌ Token verification returned None")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_session_creation():
    """Test if we can create a session"""
    print("\n🧪 Testing session creation...")
    
    try:
        from webauthn_manager import WebAuthnManager
        from auth_database import AuthDatabase
        
        # Set test environment
        os.environ['WEBAUTHN_RP_ID'] = 'localhost'
        os.environ['WEBAUTHN_ORIGIN'] = 'http://localhost'
        os.environ['JWT_SECRET'] = 'test-secret-123'
        
        manager = WebAuthnManager()
        db = AuthDatabase()
        
        # Generate token
        user_id = "test-user-123"
        token = manager.generate_jwt_token(user_id, expires_hours=1)
        
        # Create session manually
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        session_id = db.create_session(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent="Test Script",
            ip_address="127.0.0.1"
        )
        
        if session_id:
            print(f"✅ Session created: {session_id}")
            
            # Now try to verify the token
            payload = manager.verify_jwt_token(token)
            if payload:
                print(f"✅ Token verified after session creation: {payload}")
                return True
            else:
                print("❌ Token still not verified after session creation")
                return False
        else:
            print("❌ Failed to create session")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all JWT tests"""
    print("🔍 JWT Debug Tests")
    print("=" * 40)
    
    tests = [
        ("Direct JWT", test_jwt_directly),
        ("WebAuthn Manager JWT", test_webauthn_manager_jwt),
        ("Session Creation", test_session_creation)
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
    print("\n" + "="*40)
    print("📊 JWT Debug Results")
    print("="*40)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All JWT tests passed!")
    else:
        print("⚠️  Some JWT tests failed. Check the output above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
