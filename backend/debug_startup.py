#!/usr/bin/env python3
"""
Debug script to test startup step by step
"""

import sys
import os

def test_imports():
    """Test each import step by step"""
    print("Testing imports step by step...")
    
    try:
        print("1. Testing basic imports...")
        import json
        import time
        import threading
        print("✅ Basic imports successful")
    except Exception as e:
        print(f"❌ Basic imports failed: {e}")
        return False
    
    try:
        print("2. Testing HTTP server imports...")
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from socketserver import ThreadingMixIn
        print("✅ HTTP server imports successful")
    except Exception as e:
        print(f"❌ HTTP server imports failed: {e}")
        return False
    
    try:
        print("3. Testing URL parsing...")
        from urllib.parse import urlparse, parse_qs
        print("✅ URL parsing imports successful")
    except Exception as e:
        print(f"❌ URL parsing imports failed: {e}")
        return False
    
    try:
        print("4. Testing config import...")
        from config import config
        print("✅ Config import successful")
        print(f"   Config file: {config.config_file}")
        print(f"   Backend port: {config.get_port('backend')}")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        print("5. Testing auth import...")
        from auth import AuthManager
        print("✅ Auth import successful")
    except Exception as e:
        print(f"❌ Auth import failed: {e}")
        return False
    
    try:
        print("6. Testing metrics import...")
        from metrics import MetricsCollector
        print("✅ Metrics import successful")
    except Exception as e:
        print(f"❌ Metrics import failed: {e}")
        return False
    
    try:
        print("7. Testing database import...")
        from database import MetricsDatabase
        print("✅ Database import successful")
    except Exception as e:
        print(f"❌ Database import failed: {e}")
        return False
    
    try:
        print("8. Testing system monitor import...")
        from system_monitor import SystemMonitor
        print("✅ System monitor import successful")
    except Exception as e:
        print(f"❌ System monitor import failed: {e}")
        return False
    
    try:
        print("9. Testing service manager import...")
        from service_manager import ServiceManager
        print("✅ Service manager import successful")
    except Exception as e:
        print(f"❌ Service manager import failed: {e}")
        return False
    
    try:
        print("10. Testing power manager import...")
        from power_manager import PowerManager
        print("✅ Power manager import successful")
    except Exception as e:
        print(f"❌ Power manager import failed: {e}")
        return False
    
    try:
        print("11. Testing log manager import...")
        from log_manager import LogManager
        print("✅ Log manager import successful")
    except Exception as e:
        print(f"❌ Log manager import failed: {e}")
        return False
    
    try:
        print("12. Testing utils import...")
        from utils import rate_limit, monitor_performance
        print("✅ Utils import successful")
    except Exception as e:
        print(f"❌ Utils import failed: {e}")
        return False
    
    try:
        print("13. Testing WebAuthn import...")
        from webauthn_manager import WebAuthnManager
        print("✅ WebAuthn import successful")
    except Exception as e:
        print(f"❌ WebAuthn import failed: {e}")
        print("   This is optional, continuing...")
    
    print("✅ All critical imports successful!")
    return True

def test_server_creation():
    """Test server creation"""
    try:
        print("Testing server creation...")
        from server import PiMonitorServer
        
        port = 80
        print(f"Creating server on port {port}...")
        server = PiMonitorServer(port=port)
        print("✅ Server created successfully")
        return True
    except Exception as e:
        print(f"❌ Server creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Pi Monitor Backend - Startup Debug")
    print("=" * 60)
    
    if not test_imports():
        print("❌ Import testing failed")
        sys.exit(1)
    
    if not test_server_creation():
        print("❌ Server creation failed")
        sys.exit(1)
    
    print("✅ All tests passed! The backend should start successfully.")
