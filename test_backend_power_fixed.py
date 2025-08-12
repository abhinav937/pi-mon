#!/usr/bin/env python3
"""
Test script for backend power management functionality
This script tests the power management functions without actually executing shutdown/restart
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from simple_server import SimplePiMonitorHandler
    print("✅ Successfully imported SimplePiMonitorHandler")
    
    # Create an instance of the handler
    handler = SimplePiMonitorHandler(None, None, None)
    print("✅ Successfully created handler instance")
    
    # Test permission checking
    print("\n🔍 Testing shutdown permissions...")
    shutdown_perms = handler._check_shutdown_permissions()
    print(f"Shutdown permissions: {shutdown_perms}")
    
    print("\n🔍 Testing restart permissions...")
    restart_perms = handler._check_restart_permissions()
    print(f"Restart permissions: {restart_perms}")
    
    print("\n🔍 Testing sudo permissions...")
    sudo_perms = handler._check_sudo_permissions()
    print(f"Sudo permissions: {sudo_perms}")
    
    print("\n🔍 Testing command availability...")
    commands = ['shutdown', 'poweroff', 'halt', 'reboot', 'systemctl']
    available = handler._check_command_availability(commands)
    print(f"Available commands: {available}")
    
    print("\n✅ All tests completed successfully!")
    print("\n📋 Summary:")
    print(f"  - Can shutdown: {shutdown_perms.get('can_shutdown', False)}")
    print(f"  - Can restart: {restart_perms.get('can_restart', False)}")
    print(f"  - Can use sudo: {sudo_perms.get('can_sudo', False)}")
    print(f"  - Commands available: {len(available)}/{len(commands)}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root directory")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
