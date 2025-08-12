#!/usr/bin/env python3
"""
Test script for Pi Monitor API Key Authentication
"""

import requests
import json
import os

# Configuration
BACKEND_URL = "http://localhost:5001"
API_KEY = os.environ.get('PI_MONITOR_API_KEY', 'pi-monitor-api-key-2024')

def test_public_endpoints():
    """Test endpoints that don't require authentication"""
    print("🔓 Testing Public Endpoints...")
    
    endpoints = [
        "/",
        "/health"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}")
            print(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:100]}...")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")

def test_api_key_validation():
    """Test API key validation endpoint"""
    print("\n🔑 Testing API Key Validation...")
    
    try:
        # Test with valid API key
        response = requests.post(f"{BACKEND_URL}/api/auth/token", 
                               json={"api_key": API_KEY})
        print(f"✅ Valid API Key: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
        
        # Test with invalid API key
        response = requests.post(f"{BACKEND_URL}/api/auth/token", 
                               json={"api_key": "invalid-key"})
        print(f"✅ Invalid API Key: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
    except Exception as e:
        print(f"❌ API Key Validation: Error - {e}")

def test_protected_endpoints():
    """Test endpoints that require authentication"""
    print("\n🔒 Testing Protected Endpoints...")
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    endpoints = [
        "/api/system",
        "/api/system/enhanced",
        "/api/power"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}", headers=headers)
            print(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response keys: {list(data.keys())}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")

def test_unauthorized_access():
    """Test protected endpoints without authentication"""
    print("\n🚫 Testing Unauthorized Access...")
    
    endpoints = [
        "/api/system",
        "/api/system/enhanced",
        "/api/power"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{BACKEND_URL}{endpoint}")
            print(f"✅ {endpoint} (no auth): {response.status_code}")
            if response.status_code == 401:
                print(f"   Correctly rejected unauthorized access")
        except Exception as e:
            print(f"❌ {endpoint} (no auth): Error - {e}")

def main():
    """Run all tests"""
    print("🧪 Pi Monitor API Key Authentication Test")
    print("=" * 50)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"API Key: {API_KEY[:10]}..." if len(API_KEY) > 10 else f"API Key: {API_KEY}")
    print()
    
    try:
        test_public_endpoints()
        test_api_key_validation()
        test_protected_endpoints()
        test_unauthorized_access()
        
        print("\n🎉 All tests completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")

if __name__ == "__main__":
    main()
