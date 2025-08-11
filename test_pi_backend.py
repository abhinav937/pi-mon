#!/usr/bin/env python3
"""
Simple test script for Pi Monitor Backend
Tests basic functionality without complex dependencies
"""

import requests
import json
import time
from datetime import datetime

# Configuration - change this to your Pi's IP address
BASE_URL = "http://192.168.0.201:5001"  # Pi's IP address
USERNAME = "abhinav"
PASSWORD = "kavachi"

def test_endpoint(url, name, method="GET", data=None, headers=None):
    """Test a single endpoint"""
    print(f"🔍 Testing {name}...")
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ {name}: OK")
            return True
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False

def test_health():
    """Test health endpoint"""
    return test_endpoint(f"{BASE_URL}/health", "Health Check")

def test_root():
    """Test root endpoint"""
    return test_endpoint(f"{BASE_URL}/", "Root Endpoint")

def test_auth():
    """Test authentication"""
    data = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(f"{BASE_URL}/api/auth/token", json=data, timeout=10)
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data.get('access_token')
        if token:
            print("✅ Authentication: OK")
            return token
        else:
            print("❌ Authentication: No token received")
            return None
    else:
        print(f"❌ Authentication: HTTP {response.status_code}")
        return None

def test_protected_endpoints(token):
    """Test protected endpoints with token"""
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        ("/api/system", "System Stats"),
        ("/api/system/enhanced", "Enhanced System Stats"),
        ("/api/metrics", "Metrics"),
        ("/api/services", "Services"),
        ("/api/power", "Power Status"),
        ("/api/status", "Quick Status")
    ]
    
    results = []
    for endpoint, name in endpoints:
        result = test_endpoint(f"{BASE_URL}{endpoint}", name, headers=headers)
        results.append(result)
    
    return results

def main():
    """Run all tests"""
    print("🥧 Pi Monitor Backend Test")
    print("=" * 40)
    print(f"📍 Testing server at: {BASE_URL}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 40)
    
    # Test basic endpoints
    health_ok = test_health()
    root_ok = test_root()
    
    if not health_ok or not root_ok:
        print("\n❌ Basic endpoints failed. Make sure the server is running!")
        print("💡 Try: docker logs pi-monitor-backend")
        return
    
    # Test authentication
    token = test_auth()
    if not token:
        print("\n❌ Authentication failed!")
        return
    
    # Test protected endpoints
    print("\n🔒 Testing protected endpoints...")
    protected_results = test_protected_endpoints(token)
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Test Results Summary")
    print("=" * 40)
    print(f"✅ Health: {'PASS' if health_ok else 'FAIL'}")
    print(f"✅ Root: {'PASS' if root_ok else 'FAIL'}")
    print(f"✅ Auth: {'PASS' if token else 'FAIL'}")
    
    passed = sum(protected_results)
    total = len(protected_results)
    print(f"✅ Protected Endpoints: {passed}/{total} passed")
    
    print(f"\n🎯 Overall: Basic endpoints working, {passed}/{total} protected endpoints working")
    
    if passed == total:
        print("🎉 All tests passed! The Pi backend is working correctly.")
    else:
        print("⚠️  Some protected endpoints failed. Check the server logs.")

if __name__ == "__main__":
    main()
