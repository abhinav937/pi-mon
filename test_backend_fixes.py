#!/usr/bin/env python3
"""
Test script to verify backend fixes
"""

import requests
import json
import time

def test_backend():
    base_url = "http://localhost:5001"
    
    print("Testing Pi Monitor Backend...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Uptime: {data.get('uptime', 'N/A')}")
            print(f"   Status: {data.get('status', 'N/A')}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Test 2: Authentication
    try:
        auth_data = {"username": "abhinav", "password": "kavachi"}
        response = requests.post(f"{base_url}/api/auth/token", json=auth_data)
        print(f"✅ Authentication: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print(f"   Token received: {token[:20]}...")
        else:
            print(f"   Auth failed: {response.text}")
            return
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Test 3: System stats (with uptime)
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{base_url}/api/system", headers=headers)
        print(f"✅ System stats: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Uptime: {data.get('uptime', 'N/A')}")
            print(f"   CPU: {data.get('cpu_percent', 'N/A')}%")
            print(f"   Memory: {data.get('memory_percent', 'N/A')}%")
            print(f"   Temperature: {data.get('temperature', 'N/A')}°C")
    except Exception as e:
        print(f"❌ System stats failed: {e}")
    
    # Test 4: Enhanced system stats
    try:
        response = requests.get(f"{base_url}/api/system/enhanced", headers=headers)
        print(f"✅ Enhanced stats: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if 'system' in data:
                print(f"   Enhanced uptime: {data['system'].get('uptime', 'N/A')}")
                print(f"   Boot time: {data['system'].get('boot_time', 'N/A')}")
    except Exception as e:
        print(f"❌ Enhanced stats failed: {e}")
    
    # Test 5: Services
    try:
        response = requests.get(f"{base_url}/api/services", headers=headers)
        print(f"✅ Services: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total services: {data.get('total_services', 'N/A')}")
            if 'services' in data:
                for service in data['services'][:3]:  # Show first 3
                    print(f"   - {service.get('name', 'N/A')}: {service.get('status', 'N/A')}")
    except Exception as e:
        print(f"❌ Services failed: {e}")
    
    # Test 6: Power status
    try:
        response = requests.get(f"{base_url}/api/power", headers=headers)
        print(f"✅ Power status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Power state: {data.get('power_state', 'N/A')}")
            print(f"   Uptime: {data.get('uptime', 'N/A')}")
            print(f"   Available actions: {data.get('available_actions', [])}")
    except Exception as e:
        print(f"❌ Power status failed: {e}")
    
    # Test 7: Logs
    try:
        response = requests.get(f"{base_url}/api/logs", headers=headers)
        print(f"✅ Logs: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Total logs: {data.get('total_logs', 'N/A')}")
            print(f"   Log directory: {data.get('log_directory', 'N/A')}")
            if 'logs' in data and data['logs']:
                first_log = data['logs'][0]
                print(f"   First log: {first_log.get('name', 'N/A')} ({first_log.get('size', 'N/A')})")
    except Exception as e:
        print(f"❌ Logs failed: {e}")
    
    # Test 8: Network info
    try:
        response = requests.get(f"{base_url}/api/network", headers=headers)
        print(f"✅ Network: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Interfaces: {len(data.get('interfaces', {}))}")
            if 'interfaces' in data:
                for iface, info in list(data['interfaces'].items())[:2]:  # Show first 2
                    print(f"   - {iface}: {len(info.get('addresses', []))} addresses")
    except Exception as e:
        print(f"❌ Network failed: {e}")
    
    print("\n🎯 Backend testing complete!")

if __name__ == "__main__":
    test_backend()
