#!/usr/bin/env python3
"""
Test script for power permissions and shutdown/restart functionality
Run this to check if your system can execute shutdown/restart commands
"""

import os
import platform
import subprocess
import sys

def check_windows_admin():
    """Check if running as Windows Administrator"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except ImportError:
        return False

def check_linux_permissions():
    """Check Linux/Raspberry Pi permissions"""
    print("=== Linux/Raspberry Pi Permission Check ===")
    
    # Check current user
    current_user = os.getenv('USER', 'unknown')
    print(f"Current user: {current_user}")
    
    # Check if running as root
    if os.geteuid() == 0:
        print("✅ Running as root user - full permissions")
        return True
    else:
        print("❌ Not running as root user")
    
    # Check sudo group membership
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            groups = result.stdout.strip().split()
            if 'sudo' in groups:
                print("✅ User is in sudo group")
            else:
                print("❌ User is NOT in sudo group")
        else:
            print("❌ Could not check user groups")
    except Exception as e:
        print(f"❌ Error checking groups: {e}")
    
    # Check command availability
    commands_to_check = ['shutdown', 'poweroff', 'halt', 'reboot', 'systemctl']
    available_commands = []
    
    for cmd in commands_to_check:
        try:
            result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                available_commands.append(cmd)
                print(f"✅ {cmd} command available")
            else:
                print(f"❌ {cmd} command NOT available")
        except Exception as e:
            print(f"❌ Error checking {cmd}: {e}")
    
    # Test sudo without password
    print("\n=== Testing Sudo Permissions ===")
    test_commands = [
        ['sudo', '-n', 'shutdown', '--help'],
        ['sudo', '-n', 'poweroff', '--help'],
        ['sudo', '-n', 'reboot', '--help'],
        ['sudo', '-n', 'systemctl', '--help']
    ]
    
    sudo_works = False
    for cmd in test_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ Sudo command works: {' '.join(cmd)}")
                sudo_works = True
                break
            else:
                print(f"❌ Sudo command failed: {' '.join(cmd)}")
        except Exception as e:
            print(f"❌ Error testing sudo: {e}")
    
    if sudo_works:
        print("✅ User can use sudo without password for some commands")
        return True
    else:
        print("❌ User cannot use sudo without password")
        return False

def check_windows_permissions():
    """Check Windows permissions"""
    print("=== Windows Permission Check ===")
    
    is_admin = check_windows_admin()
    if is_admin:
        print("✅ Running as Windows Administrator")
        return True
    else:
        print("❌ NOT running as Windows Administrator")
        print("💡 To fix: Right-click and 'Run as Administrator'")
        return False

def test_shutdown_commands():
    """Test shutdown commands (dry run)"""
    print("\n=== Testing Shutdown Commands (Dry Run) ===")
    
    if platform.system() == 'Windows':
        # Test Windows shutdown command
        try:
            result = subprocess.run(['shutdown', '/?'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Windows shutdown command available")
                return True
            else:
                print("❌ Windows shutdown command failed")
                return False
        except Exception as e:
            print(f"❌ Error testing Windows shutdown: {e}")
            return False
    else:
        # Test Linux shutdown commands
        test_commands = [
            ['shutdown', '--help'],
            ['poweroff', '--help'],
            ['reboot', '--help'],
            ['systemctl', '--help']
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✅ Command available: {cmd[0]}")
                    return True
                else:
                    print(f"❌ Command failed: {cmd[0]}")
            except Exception as e:
                print(f"❌ Error testing {cmd[0]}: {e}")
        
        return False

def main():
    """Main test function"""
    print("🔍 Power Permission Test Script")
    print("=" * 50)
    
    system = platform.system()
    print(f"Operating System: {system}")
    print(f"Platform: {platform.platform()}")
    
    if system == 'Windows':
        can_shutdown = check_windows_permissions()
    else:
        can_shutdown = check_linux_permissions()
    
    print(f"\n=== Summary ===")
    if can_shutdown:
        print("✅ System CAN execute shutdown/restart commands")
    else:
        print("❌ System CANNOT execute shutdown/restart commands")
    
    # Test command availability
    commands_available = test_shutdown_commands()
    
    print(f"\n=== Recommendations ===")
    if system == 'Windows':
        if not can_shutdown:
            print("1. Run the application as Administrator")
            print("2. Use Windows Task Scheduler with elevated privileges")
            print("3. Add shutdown command to Windows PATH")
    else:
        if not can_shutdown:
            print("1. Run the backend as root user: sudo python3 simple_server.py")
            print("2. Configure sudoers to allow shutdown without password:")
            print("   - Run: sudo visudo")
            print("   - Add line: username ALL=(ALL) NOPASSWD: /sbin/shutdown, /sbin/reboot, /sbin/poweroff")
            print("3. Use systemd commands if available: systemctl poweroff, systemctl reboot")
    
    if not commands_available:
        print("4. Install shutdown utilities if commands are missing")
    
    print(f"\n=== Next Steps ===")
    print("1. Fix permissions based on recommendations above")
    print("2. Restart the backend server")
    print("3. Test shutdown/restart from the web interface")
    print("4. Check the backend logs for detailed error messages")

if __name__ == '__main__':
    main()
