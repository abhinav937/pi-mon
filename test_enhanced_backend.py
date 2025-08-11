#!/usr/bin/env python3
"""
Test script for enhanced Pi Monitor backend
Tests all the new endpoints and features
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"
USERNAME = "abhinav"
PASSWORD = "kavachi"

def test_health_endpoint():
    """Test the health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   Uptime: {data.get('uptime', 'N/A')}")
            print(f"   Version: {data.get('version', 'N/A')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n🔍 Testing root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint working: {data['message']}")
            print(f"   Version: {data.get('version', 'N/A')}")
            print(f"   Features: {list(data.get('features', {}).keys())}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_authentication():
    """Test authentication endpoint"""
    print("\n🔍 Testing authentication...")
    try:
        response = requests.post(f"{BASE_URL}/api/auth/token", json={
            "username": USERNAME,
            "password": PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print(f"✅ Authentication successful")
            print(f"   Token: {token[:20]}...")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def test_system_endpoint(token):
    """Test the system endpoint with authentication"""
    print("\n🔍 Testing system endpoint...")
    if not token:
        print("❌ No token available")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/system", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System endpoint working")
            print(f"   CPU: {data.get('cpu_percent', 'N/A')}%")
            print(f"   Memory: {data.get('memory_percent', 'N/A')}%")
            print(f"   Disk: {data.get('disk_percent', 'N/A')}%")
            print(f"   Temperature: {data.get('temperature', 'N/A')}°C")
            return True
        else:
            print(f"❌ System endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System endpoint error: {e}")
        return False

def test_metrics_endpoint(token):
    """Test the metrics endpoint"""
    print("\n🔍 Testing metrics endpoint...")
    if not token:
        print("❌ No token available")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/metrics?minutes=30", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Metrics endpoint working")
            print(f"   Collection active: {data.get('collection_status', {}).get('active', 'N/A')}")
            print(f"   Total points: {data.get('collection_status', {}).get('total_points', 'N/A')}")
            print(f"   Metrics count: {len(data.get('metrics', []))}")
            return True
        else:
            print(f"❌ Metrics endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Metrics endpoint error: {e}")
        return False

def test_system_info_endpoint(token):
    """Test the detailed system info endpoint"""
    print("\n🔍 Testing system info endpoint...")
    if not token:
        print("❌ No token available")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/system/info", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ System info endpoint working")
            if 'cpu_info' in data:
                print(f"   CPU Model: {data['cpu_info'].get('model', 'N/A')}")
                print(f"   CPU Freq: {data['cpu_info'].get('current_freq', 'N/A')} MHz")
            if 'memory_info' in data:
                print(f"   Total RAM: {data['memory_info'].get('total', 'N/A')} GB")
            return True
        else:
            print(f"❌ System info endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ System info endpoint error: {e}")
        return False

def test_services_endpoint(token):
    """Test the services endpoint"""
    print("\n🔍 Testing services endpoint...")
    if not token:
        print("❌ No token available")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/services", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Services endpoint working")
            print(f"   Total services: {data.get('total_services', 'N/A')}")
            services = data.get('services', [])
            for service in services[:3]:  # Show first 3 services
                print(f"   - {service.get('name', 'N/A')}: {service.get('status', 'N/A')}")
            return True
        else:
            print(f"❌ Services endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Services endpoint error: {e}")
        return False

def test_power_endpoint(token):
    """Test the power endpoint"""
    print("\n🔍 Testing power endpoint...")
    if not token:
        print("❌ No token available")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/power", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Power endpoint working")
            print(f"   Power state: {data.get('power_state', 'N/A')}")
            print(f"   Uptime: {data.get('current_uptime', 'N/A')}")
            return True
        else:
            print(f"❌ Power endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Power endpoint error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Pi Monitor Enhanced Backend Test Suite")
    print("=" * 50)
    print(f"📍 Testing server at: {BASE_URL}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Test basic endpoints
    health_ok = test_health_endpoint()
    root_ok = test_root_endpoint()
    
    if not health_ok or not root_ok:
        print("\n❌ Basic endpoints failed. Make sure the server is running!")
        return
    
    # Test authentication
    token = test_authentication()
    if not token:
        print("\n❌ Authentication failed. Cannot test protected endpoints!")
        return
    
    # Test protected endpoints
    system_ok = test_system_endpoint(token)
    metrics_ok = test_metrics_endpoint(token)
    info_ok = test_system_info_endpoint(token)
    services_ok = test_services_endpoint(token)
    power_ok = test_power_endpoint(token)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    print(f"✅ Health: {'PASS' if health_ok else 'FAIL'}")
    print(f"✅ Root: {'PASS' if root_ok else 'FAIL'}")
    print(f"✅ Auth: {'PASS' if token else 'FAIL'}")
    print(f"✅ System: {'PASS' if system_ok else 'FAIL'}")
    print(f"✅ Metrics: {'PASS' if metrics_ok else 'FAIL'}")
    print(f"✅ System Info: {'PASS' if info_ok else 'FAIL'}")
    print(f"✅ Services: {'PASS' if services_ok else 'FAIL'}")
    print(f"✅ Power: {'PASS' if power_ok else 'FAIL'}")
    
    passed = sum([health_ok, root_ok, bool(token), system_ok, metrics_ok, info_ok, services_ok, power_ok])
    total = 8
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The enhanced backend is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the server logs for details.")

if __name__ == "__main__":
    main()
