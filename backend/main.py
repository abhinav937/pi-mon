#!/usr/bin/env python3
"""
Pi Monitor - Main Entry Point
Main file that imports and runs the Pi Monitor server
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import PiMonitorServer
from config import config

def main():
    """Main entry point for Pi Monitor"""
    try:
        # Create and run the server
        server = PiMonitorServer()
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Pi Monitor...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
