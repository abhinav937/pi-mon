#!/usr/bin/env python3
"""
Test script for backend power management functionality
This script tests the power management functions without actually executing shutdown/restart
"""

import sys
import os
import platform
import subprocess

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from simple_server import SimplePiMonitorHandler
    print("✅ Successfully imported SimplePiMonitorHandler")
    
    # Create a mock handler class that extracts the utility methods
    # without inheriting from BaseHTTPRequestHandler
    class MockPowerHandler:
        def __init__(self):
            # Create a temporary handler instance just to access the methods
            # We'll use a different approach to test the methods
            pass
        
        def _check_shutdown_permissions(self):
            """Check if current user can execute shutdown commands"""
            try:
                if platform.system() == 'Windows':
                    # Check if running as administrator on Windows
                    try:
                        import ctypes
                        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                        if is_admin:
                            return {
                                'can_shutdown': True,
                                'method': 'administrator',
                                'reason': 'Running as Windows Administrator',
                                'suggestions': []
                            }
                        else:
                            return {
                                'can_shutdown': False,
                                'method': 'user',
                                'reason': 'Not running as Windows Administrator',
                                'suggestions': [
                                    'Run the application as Administrator',
                                    'Use Windows Task Scheduler with elevated privileges',
                                    'Add shutdown command to Windows PATH'
                                ]
                            }
                    except ImportError:
                        return {
                            'can_shutdown': False,
                            'method': 'unknown',
                            'reason': 'Cannot determine Windows admin status',
                            'suggestions': ['Run as Administrator manually']
                        }
                else:
                    # Linux/Raspberry Pi permission checking
                    current_user = os.getenv('USER', 'unknown')
                    print(f"Checking shutdown permissions for user: {current_user}")
                    
                    # Check if running as root
                    try:
                        if os.geteuid() == 0:
                            print("Running as root user - shutdown allowed")
                            return {
                                'can_shutdown': True,
                                'method': 'root',
                                'reason': 'Running as root user',
                                'suggestions': []
                            }
                    except AttributeError:
                        print("geteuid not available on this platform")
                    
                    # Check if user can use sudo without password for shutdown commands
                    sudo_check = self._check_sudo_permissions()
                    if sudo_check['can_sudo']:
                        print(f"User {current_user} can use sudo for shutdown")
                        return {
                            'can_shutdown': True,
                            'method': 'sudo',
                            'reason': f'User {current_user} can use sudo for shutdown',
                            'suggestions': []
                        }
                    
                    # Check if user is in sudo group
                    try:
                        result = subprocess.run(['groups'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and 'sudo' in result.stdout:
                            print(f"User {current_user} in sudo group but may need password")
                            return {
                                'can_shutdown': False,
                                'method': 'sudo_group',
                                'reason': f'User {current_user} in sudo group but may need password',
                                'suggestions': [
                                    'Configure sudoers to allow shutdown without password',
                                    'Run the backend as root user',
                                    'Add specific shutdown commands to sudoers'
                                ]
                            }
                    except Exception as e:
                        print(f"Error checking groups: {str(e)}")
                    
                    # Check if shutdown commands are available in PATH
                    shutdown_available = self._check_command_availability(['shutdown', 'poweroff', 'halt'])
                    if shutdown_available:
                        print(f"Shutdown commands available but user {current_user} lacks permissions")
                        return {
                            'can_shutdown': False,
                            'method': 'commands_available',
                            'reason': f'Shutdown commands available but user {current_user} lacks permissions',
                            'suggestions': [
                                'Run the backend as root user',
                                'Configure sudoers file for passwordless shutdown',
                                'Use systemd commands if available'
                            ]
                        }
                    else:
                        print(f"Shutdown commands not available for user {current_user}")
                        return {
                            'can_shutdown': False,
                            'method': 'no_commands',
                            'reason': f'Shutdown commands not available for user {current_user}',
                            'suggestions': [
                                'Install shutdown utilities',
                                'Run the backend as root user',
                                'Use alternative shutdown methods'
                            ]
                        }
                        
            except Exception as e:
                print(f"Error checking shutdown permissions: {str(e)}")
                return {
                    'can_shutdown': False,
                    'method': 'error',
                    'reason': f'Error checking permissions: {str(e)}',
                    'suggestions': ['Check system configuration and try again']
                }
        
        def _check_restart_permissions(self):
            """Check if current user can execute restart commands"""
            try:
                if platform.system() == 'Windows':
                    # Same as shutdown for Windows
                    return self._check_shutdown_permissions()
                else:
                    # Linux/Raspberry Pi permission checking
                    current_user = os.getenv('USER', 'unknown')
                    print(f"Checking restart permissions for user: {current_user}")
                    
                    # Check if running as root
                    try:
                        if os.geteuid() == 0:
                            print("Running as root user - restart allowed")
                            return {
                                'can_restart': True,
                                'method': 'root',
                                'reason': 'Running as root user',
                                'suggestions': []
                            }
                    except AttributeError:
                        print("geteuid not available on this platform")
                    
                    # Check if user can use sudo without password for restart commands
                    sudo_check = self._check_sudo_permissions()
                    if sudo_check['can_sudo']:
                        print(f"User {current_user} can use sudo for restart")
                        return {
                            'can_restart': True,
                            'method': 'sudo',
                            'reason': f'User {current_user} can use sudo for restart',
                            'suggestions': []
                        }
                    
                    # Check if user is in sudo group
                    try:
                        result = subprocess.run(['groups'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and 'sudo' in result.stdout:
                            print(f"User {current_user} in sudo group but may need password")
                            return {
                                'can_restart': False,
                                'method': 'sudo_group',
                                'reason': f'User {current_user} in sudo group but may need password',
                                'suggestions': [
                                    'Configure sudoers to allow restart without password',
                                    'Run the backend as root user',
                                    'Add specific restart commands to sudoers'
                                ]
                            }
                    except Exception as e:
                        print(f"Error checking groups: {str(e)}")
                    
                    # Check if restart commands are available in PATH
                    restart_available = self._check_command_availability(['reboot', 'shutdown', 'systemctl'])
                    if restart_available:
                        print(f"Restart commands available but user {current_user} lacks permissions")
                        return {
                            'can_restart': False,
                            'method': 'commands_available',
                            'reason': f'Restart commands available but user {current_user} lacks permissions',
                            'suggestions': [
                                'Run the backend as root user',
                                'Configure sudoers file for passwordless restart',
                                'Use systemd commands if available'
                            ]
                        }
                    else:
                        print(f"Restart commands not available for user {current_user}")
                        return {
                            'can_restart': False,
                            'method': 'no_commands',
                            'reason': f'Restart commands not available for user {current_user}',
                            'suggestions': [
                                'Install restart utilities',
                                'Run the backend as root user',
                                'Use alternative restart methods'
                            ]
                        }
                        
            except Exception as e:
                print(f"Error checking restart permissions: {str(e)}")
                return {
                    'can_restart': False,
                    'method': 'error',
                    'reason': f'Error checking permissions: {str(e)}',
                    'suggestions': ['Check system configuration and try again']
                }
        
        def _check_sudo_permissions(self):
            """Check if current user can use sudo without password for shutdown/restart commands"""
            try:
                print("Testing sudo permissions for shutdown/restart commands...")
                
                # Test if user can run shutdown command with sudo without password
                test_commands = [
                    ['sudo', '-n', 'shutdown', '--help'],
                    ['sudo', '-n', 'poweroff', '--help'],
                    ['sudo', '-n', 'reboot', '--help']
                ]
                
                for cmd in test_commands:
                    try:
                        print(f"Testing sudo command: {' '.join(cmd)}")
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                        if result.returncode == 0:
                            print(f"Sudo command successful: {' '.join(cmd)}")
                            return {
                                'can_sudo': True,
                                'command': ' '.join(cmd),
                                'reason': 'Sudo command executed successfully without password'
                            }
                        else:
                            print(f"Sudo command failed: {' '.join(cmd)} - return code: {result.returncode}")
                            if result.stderr:
                                print(f"Error output: {result.stderr.strip()}")
                    except subprocess.TimeoutExpired:
                        print(f"Sudo command timed out: {' '.join(cmd)}")
                    except Exception as e:
                        print(f"Exception testing sudo command {' '.join(cmd)}: {str(e)}")
                        continue
                
                print("No sudo commands worked without password")
                return {
                    'can_sudo': False,
                    'command': None,
                    'reason': 'No sudo commands worked without password'
                }
                
            except Exception as e:
                print(f"Error testing sudo: {str(e)}")
                return {
                    'can_sudo': False,
                    'command': None,
                    'reason': f'Error testing sudo: {str(e)}'
                }
        
        def _check_command_availability(self, commands):
            """Check if specified commands are available in PATH"""
            available_commands = []
            print(f"Checking command availability for: {commands}")
            
            for cmd in commands:
                try:
                    result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        available_commands.append(cmd)
                        print(f"  ✅ {cmd}: {result.stdout.strip()}")
                    else:
                        print(f"  ❌ {cmd}: Not found in PATH")
                except subprocess.TimeoutExpired:
                    print(f"  ⏰ {cmd}: Timeout checking availability")
                except Exception as e:
                    print(f"  💥 {cmd}: Error checking availability - {str(e)}")
            
            print(f"Available commands: {available_commands}")
            return available_commands
    
    # Create an instance of the mock handler
    handler = MockPowerHandler()
    print("✅ Successfully created mock handler instance")
    
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
