#!/usr/bin/env python3
"""
Pi Monitor - Service Startup Script
Simple script to start the backend service
"""

import sys
import os
import signal
import time

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n🛑 Received shutdown signal, stopping server...")
    sys.exit(0)

def main():
    """Main startup function"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("🚀 Starting Pi Monitor Backend Service...")
        print("=" * 50)
        
        # Test imports first
        print("🧪 Testing server components...")
        from config.config import config
        print("✅ Configuration loaded")
        
        from services.server import PiMonitorServer
        print("✅ Server module loaded")
        
        # Create and start server
        port = config.get_port('backend')
        print(f"📍 Starting server on port {port}")
        print(f"🌐 Production URL: {config.get_production_urls().get('api_base')}")
        
        server = PiMonitorServer(port=port)
        
        print("✅ Server created successfully")
        print("🚀 Starting HTTP server...")
        print(f"🔗 Health check: http://0.0.0.0:{port}/health")
        print(f"🌐 Production health: {config.get_production_urls().get('api_base')}:{port}/health")
        print("=" * 50)
        
        # Start the server
        server.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print(f"📝 Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
