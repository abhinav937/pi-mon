#!/usr/bin/env python3
"""
Pi Monitor - Server Test Script
Simple script to test if the server can start and run
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported"""
    try:
        print("🧪 Testing imports...")
        
        from config import config
        print("✅ Config imported successfully")
        
        from server import PiMonitorServer
        print("✅ Server imported successfully")
        
        from auth import AuthManager
        print("✅ Auth imported successfully")
        
        from metrics import MetricsCollector
        print("✅ Metrics imported successfully")
        
        from database import MetricsDatabase
        print("✅ Database imported successfully")
        
        from system_monitor import SystemMonitor
        print("✅ SystemMonitor imported successfully")
        
        from service_manager import ServiceManager
        print("✅ ServiceManager imported successfully")
        
        from power_manager import PowerManager
        print("✅ PowerManager imported successfully")
        
        from log_manager import LogManager
        print("✅ LogManager imported successfully")
        
        print("✅ All imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading"""
    try:
        print("\n🧪 Testing configuration...")
        
        from config import config
        
        print(f"✅ Config file: {config.config_file}")
        print(f"✅ Backend port: {config.get_port('backend')}")
        print(f"✅ Production API: {config.get_production_urls().get('api_base')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_server_creation():
    """Test if server can be created"""
    try:
        print("\n🧪 Testing server creation...")
        
        from server import PiMonitorServer
        
        server = PiMonitorServer(port=5001)
        print("✅ Server created successfully")
        print(f"✅ Server port: {server.port}")
        
        return True
        
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Pi Monitor - Server Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_config,
        test_server_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All tests passed! Server should work correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
