#!/usr/bin/env python3
"""
Test Windows Power Management Commands
This script tests the same commands that the backend uses for shutdown/restart
"""

import platform
import subprocess
import os
import ctypes

def check_windows_admin():
    """Check if running as Windows Administrator"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        return is_admin
    except:
        return False

def test_shutdown_command():
    """Test the shutdown command that the backend uses"""
    print("Testing Windows shutdown command...")
    
    # Check if we're running as admin
    is_admin = check_windows_admin()
    print(f"Running as Administrator: {is_admin}")
    
    if not is_admin:
        print("⚠️  WARNING: Not running as Administrator")
        print("   This may cause the shutdown command to fail")
        print("   Try running this script as Administrator")
    
    # Test the exact command the backend uses
    shutdown_cmd = 'shutdown /s /t 5'
    print(f"Testing command: {shutdown_cmd}")
    
    try:
        # Use the same parameters as the backend
        result = subprocess.run(shutdown_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ Shutdown command executed successfully")
            print("   The system should shutdown in 5 seconds...")
            print("   To cancel: shutdown /a")
        else:
            print("❌ Shutdown command failed")
            print(f"   Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out (this might be normal for shutdown)")
    except Exception as e:
        print(f"❌ Error executing command: {str(e)}")

def test_restart_command():
    """Test the restart command that the backend uses"""
    print("\nTesting Windows restart command...")
    
    # Check if we're running as admin
    is_admin = check_windows_admin()
    print(f"Running as Administrator: {is_admin}")
    
    if not is_admin:
        print("⚠️  WARNING: Not running as Administrator")
        print("   This may cause the restart command to fail")
    
    # Test the exact command the backend uses
    restart_cmd = 'shutdown /r /t 5'
    print(f"Testing command: {restart_cmd}")
    
    try:
        # Use the same parameters as the backend
        result = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ Restart command executed successfully")
            print("   The system should restart in 5 seconds...")
            print("   To cancel: shutdown /a")
        else:
            print("❌ Restart command failed")
            print(f"   Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⏰ Command timed out (this might be normal for restart)")
    except Exception as e:
        print(f"❌ Error executing command: {str(e)}")

def test_alternative_commands():
    """Test alternative power management commands"""
    print("\nTesting alternative power management commands...")
    
    alternative_commands = [
        "powercfg /hibernate off",
        "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
        "shutdown /a"  # Cancel any pending shutdown
    ]
    
    for cmd in alternative_commands:
        print(f"\nTesting: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            print(f"  Return code: {result.returncode}")
            if result.stdout:
                print(f"  STDOUT: {result.stdout.strip()}")
            if result.stderr:
                print(f"  STDERR: {result.stderr.strip()}")
        except Exception as e:
            print(f"  Error: {str(e)}")

def main():
    """Main test function"""
    print("=" * 60)
    print("🔍 Windows Power Management Test")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print()
    
    # Check admin status first
    is_admin = check_windows_admin()
    print(f"🔑 Administrator Status: {'✅ Yes' if is_admin else '❌ No'}")
    
    if not is_admin:
        print("\n⚠️  IMPORTANT: You are NOT running as Administrator")
        print("   Many power management commands require admin privileges")
        print("   To fix this:")
        print("   1. Right-click on Command Prompt or PowerShell")
        print("   2. Select 'Run as Administrator'")
        print("   3. Navigate to this directory")
        print("   4. Run: python test_windows_power.py")
        print()
    
    # Test commands
    test_shutdown_command()
    test_restart_command()
    test_alternative_commands()
    
    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("=" * 60)
    
    if is_admin:
        print("✅ You are running as Administrator")
        print("   Power management commands should work")
        print("   If they still fail, check Windows policies")
    else:
        print("❌ You are NOT running as Administrator")
        print("   This is likely why power management fails")
        print("   Run the backend as Administrator")
    
    print("\n💡 To test the backend:")
    print("   1. Run Command Prompt as Administrator")
    print("   2. Navigate to your project directory")
    print("   3. Run: python backend/simple_server.py")
    print("   4. Test power management from the frontend")

if __name__ == "__main__":
    main()


