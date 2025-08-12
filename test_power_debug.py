#!/usr/bin/env python3
"""
Debug script to test power management commands
This will help identify why shutdown/restart commands are failing
"""

import subprocess
import os
import platform
import sys

def test_command_execution():
    """Test various power management commands"""
    print("🔍 Testing Power Management Commands")
    print("=" * 50)
    
    # Check current user and permissions
    print(f"👤 Current User: {os.getenv('USER', 'unknown')}")
    print(f"👤 User Name: {os.getenv('USERNAME', 'unknown')}")
    
    # Platform-specific user ID checking
    if platform.system() == 'Windows':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            print(f"🆔 Windows Admin: {'Yes' if is_admin else 'No'}")
        except ImportError:
            print(f"🆔 Windows Admin: Cannot determine")
    else:
        try:
            print(f"🆔 Effective User ID: {os.geteuid()}")
            print(f"🆔 Real User ID: {os.getuid()}")
        except AttributeError:
            print(f"🆔 User ID: Not available on this platform")
    
    print(f"💻 Platform: {platform.system()}")
    print(f"🐧 Platform Details: {platform.platform()}")
    print()
    
    # Test basic command availability
    print("📋 Testing Command Availability:")
    if platform.system() == 'Windows':
        commands_to_test = [
            'shutdown', 'powercfg', 'rundll32', 'sc'
        ]
    else:
        commands_to_test = [
            'shutdown', 'poweroff', 'halt', 'reboot', 'systemctl'
        ]
    
    for cmd in commands_to_test:
        try:
            if platform.system() == 'Windows':
                # On Windows, check if command exists in PATH
                result = subprocess.run(['where', cmd], capture_output=True, text=True, timeout=5, shell=True)
            else:
                result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(f"  ✅ {cmd}: {result.stdout.strip()}")
            else:
                print(f"  ❌ {cmd}: Not found in PATH")
        except Exception as e:
            print(f"  ❌ {cmd}: Error checking - {str(e)}")
    
    print()
    
    # Test command execution (with --help to avoid actual shutdown)
    print("🧪 Testing Command Execution (safe mode):")
    
    if platform.system() == 'Windows':
        test_commands = [
            ['shutdown', '/?'],
            ['powercfg', '/?'],
            ['sc', 'query', 'wuauserv']
        ]
    else:
        test_commands = [
            ['shutdown', '--help'],
            ['poweroff', '--help'],
            ['halt', '--help'],
            ['reboot', '--help'],
            ['systemctl', '--help']
        ]
    
    for cmd in test_commands:
        try:
            print(f"  🔍 Testing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, shell=(platform.system() == 'Windows'))
            if result.returncode == 0:
                print(f"    ✅ Success - Return code: {result.returncode}")
                print(f"    📝 Output length: {len(result.stdout)} chars")
                if result.stdout.strip():
                    print(f"    📄 First line: {result.stdout.strip().split('\\n')[0][:100]}...")
            else:
                print(f"    ❌ Failed - Return code: {result.returncode}")
                print(f"    🚨 Error: {result.stderr.strip()[:100]}...")
        except subprocess.TimeoutExpired:
            print(f"    ⏰ Timeout after 10 seconds")
        except Exception as e:
            print(f"    💥 Exception: {str(e)}")
        print()
    
    # Test systemctl specific commands (Linux only)
    if platform.system() != 'Windows':
        print("🔧 Testing systemctl Commands:")
        systemctl_commands = [
            ['systemctl', 'is-system-running'],
            ['systemctl', 'list-units', '--type=service', '--state=running', '|', 'head', '-5']
        ]
        
        for cmd in systemctl_commands:
            try:
                print(f"  🔍 Testing: {' '.join(cmd)}")
                if '|' in cmd:
                    # Handle pipe commands
                    cmd_str = ' '.join(cmd)
                    result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=10)
                else:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"    ✅ Success - Return code: {result.returncode}")
                    print(f"    📝 Output length: {len(result.stdout)} chars")
                    if result.stdout.strip():
                        print(f"    📄 First line: {result.stdout.strip().split('\\n')[0][:100]}...")
                else:
                    print(f"    ❌ Failed - Return code: {result.returncode}")
                    print(f"    🚨 Error: {result.stderr.strip()[:100]}...")
            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout after 10 seconds")
            except Exception as e:
                print(f"    💥 Exception: {str(e)}")
            print()
    
    # Test environment variables
    print("🌍 Environment Variables:")
    important_vars = ['PATH', 'USER', 'USERNAME', 'HOME', 'SHELL', 'TERM', 'SYSTEMROOT']
    for var in important_vars:
        value = os.getenv(var, 'Not set')
        print(f"  {var}: {value}")
    
    print()
    
    # Test working directory and file permissions
    print("📁 File System Information:")
    print(f"  Current Directory: {os.getcwd()}")
    try:
        dir_contents = os.listdir('.')
        print(f"  Directory Contents: {dir_contents[:10]}...")
    except Exception as e:
        print(f"  Directory Contents: Error - {str(e)}")
    
    # Check if we can write to current directory
    try:
        test_file = 'test_write_permission.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print(f"  ✅ Write Permission: Yes")
    except Exception as e:
        print(f"  ❌ Write Permission: No - {str(e)}")
    
    print()
    
    # Test subprocess environment
    print("🔧 Subprocess Environment Test:")
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(['set'], capture_output=True, text=True, timeout=5, shell=True)
        else:
            result = subprocess.run(['env'], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            env_vars = result.stdout.strip().split('\\n')
            print(f"  📝 Environment variables count: {len(env_vars)}")
            print(f"  📄 First few: {env_vars[:3]}")
        else:
            print(f"  ❌ Failed to get environment: {result.stderr}")
    except Exception as e:
        print(f"  💥 Exception getting environment: {str(e)}")

def test_specific_issue():
    """Test the specific issue from the logs"""
    print("🎯 Testing Specific Issue from Logs")
    print("=" * 50)
    
    if platform.system() == 'Windows':
        print("Testing Windows power management commands:")
        
        windows_commands = [
            ['shutdown', '/s', '/t', '0'],
            ['shutdown', '/r', '/t', '0'],
            ['powercfg', '/hibernate', 'off'],
            ['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0']
        ]
        
        for i, cmd in enumerate(windows_commands, 1):
            print(f"\\n{i}. Testing: {' '.join(cmd)}")
            try:
                # Use safe versions to avoid actual shutdown
                if 'shutdown' in cmd and '/s' in cmd:
                    test_cmd = ['shutdown', '/?']
                elif 'shutdown' in cmd and '/r' in cmd:
                    test_cmd = ['shutdown', '/?']
                elif 'powercfg' in cmd:
                    test_cmd = ['powercfg', '/?']
                elif 'rundll32' in cmd:
                    test_cmd = ['rundll32.exe', '/?']
                else:
                    test_cmd = cmd
                
                print(f"   🔍 Executing: {' '.join(test_cmd)}")
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10, shell=True)
                
                if result.returncode == 0:
                    print(f"   ✅ Success - Return code: {result.returncode}")
                    print(f"   📝 Output: {result.stdout.strip()[:100]}...")
                else:
                    print(f"   ❌ Failed - Return code: {result.returncode}")
                    print(f"   🚨 Error: {result.stderr.strip()[:100]}...")
                    
            except subprocess.TimeoutExpired:
                print(f"   ⏰ Timeout after 10 seconds")
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")
    else:
        # Test the exact commands that are failing on Linux/Raspberry Pi
        print("Testing shutdown commands that failed in logs:")
        
        shutdown_commands = [
            ['systemctl', 'poweroff'],
            ['sudo', 'shutdown', '-h', 'now'],
            ['sudo', 'poweroff'],
            ['sudo', 'halt'],
            ['shutdown', '-h', 'now'],
            ['poweroff'],
            ['halt']
        ]
        
        for i, cmd in enumerate(shutdown_commands, 1):
            print(f"\\n{i}. Testing: {' '.join(cmd)}")
            try:
                # Use --help or similar to avoid actual shutdown
                if 'shutdown' in cmd and '-h' in cmd:
                    test_cmd = ['shutdown', '--help']
                elif 'poweroff' in cmd:
                    test_cmd = ['poweroff', '--help']
                elif 'halt' in cmd:
                    test_cmd = ['halt', '--help']
                elif 'systemctl' in cmd:
                    test_cmd = ['systemctl', '--help']
                else:
                    test_cmd = cmd
                
                print(f"   🔍 Executing: {' '.join(test_cmd)}")
                result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    print(f"   ✅ Success - Return code: {result.returncode}")
                    print(f"   📝 Output: {result.stdout.strip()[:100]}...")
                else:
                    print(f"   ❌ Failed - Return code: {result.returncode}")
                    print(f"   🚨 Error: {result.stderr.strip()[:100]}...")
                    
            except subprocess.TimeoutExpired:
                print(f"   ⏰ Timeout after 10 seconds")
            except Exception as e:
                print(f"   💥 Exception: {str(e)}")

def test_power_management_simulation():
    """Test power management without actually executing commands"""
    print("🎭 Testing Power Management Simulation")
    print("=" * 50)
    
    if platform.system() == 'Windows':
        print("Windows Power Management Commands Available:")
        print("  ✅ shutdown /s /t 0 - Shutdown")
        print("  ✅ shutdown /r /t 0 - Restart")
        print("  ✅ powercfg /hibernate off - Disable hibernate")
        print("  ✅ rundll32.exe powrprof.dll,SetSuspendState 0,1,0 - Sleep")
        print()
        print("Note: These commands require Administrator privileges")
    else:
        print("Linux/Raspberry Pi Power Management Commands Available:")
        print("  ✅ systemctl poweroff - Systemd shutdown")
        print("  ✅ systemctl reboot - Systemd restart")
        print("  ✅ shutdown -h now - Traditional shutdown")
        print("  ✅ shutdown -r now - Traditional restart")
        print("  ✅ poweroff - Direct power off")
        print("  ✅ halt - System halt")
        print("  ✅ reboot - Direct reboot")
        print()
        print("Note: These commands require root privileges or sudo access")

if __name__ == '__main__':
    print("🚀 Power Management Debug Script")
    print("=" * 60)
    
    test_command_execution()
    print("\\n" + "=" * 60)
    test_specific_issue()
    print("\\n" + "=" * 60)
    test_power_management_simulation()
    
    print("\\n✅ Debug script completed!")
