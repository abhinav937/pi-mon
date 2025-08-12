#!/usr/bin/env python3
"""
Test Backend Power Management Logic
This script simulates the exact logic from simple_server.py to debug power management
"""

import platform
import subprocess
import os
import ctypes
import json

def check_windows_admin():
    """Check if running as Windows Administrator"""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        return is_admin
    except:
        return False

def check_sudo_permissions():
    """Check if current user can use sudo without password for shutdown/restart commands"""
    try:
        # Test if user can run shutdown command with sudo without password
        test_commands = [
            ['sudo', '-n', 'shutdown', '--help'],
            ['sudo', '-n', 'poweroff', '--help'],
            ['sudo', '-n', 'reboot', '--help']
        ]
        
        for cmd in test_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return {
                        'can_sudo': True,
                        'command': ' '.join(cmd),
                        'reason': 'Sudo command executed successfully without password'
                    }
            except:
                continue
        
        return {
            'can_sudo': False,
            'command': None,
            'reason': 'No sudo commands worked without password'
        }
        
    except Exception as e:
        return {
            'can_sudo': False,
            'command': None,
            'reason': f'Error testing sudo: {str(e)}'
        }

def check_command_availability(commands):
    """Check if specified commands are available in PATH"""
    available_commands = []
    for cmd in commands:
        try:
            if platform.system() == 'Windows':
                # On Windows, check if command exists
                result = subprocess.run(['where', cmd], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    available_commands.append(cmd)
            else:
                result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    available_commands.append(cmd)
        except:
            pass
    return available_commands

def check_shutdown_permissions():
    """Check if current user can execute shutdown commands"""
    try:
        if platform.system() == 'Windows':
            # Check if running as administrator on Windows
            try:
                is_admin = check_windows_admin()
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
            
            # Check if running as root
            if os.geteuid() == 0:
                return {
                    'can_shutdown': True,
                    'method': 'root',
                    'reason': 'Running as root user',
                    'suggestions': []
                }
            
            # Check if user can use sudo without password for shutdown commands
            sudo_check = check_sudo_permissions()
            if sudo_check['can_sudo']:
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
            except:
                pass
            
            # Check if shutdown commands are available in PATH
            shutdown_available = check_command_availability(['shutdown', 'poweroff', 'halt'])
            if shutdown_available:
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
        return {
            'can_shutdown': False,
            'method': 'error',
            'reason': f'Error checking permissions: {str(e)}',
            'suggestions': ['Check system configuration and try again']
        }

def check_restart_permissions():
    """Check if current user can execute restart commands"""
    try:
        if platform.system() == 'Windows':
            # Same as shutdown for Windows
            return check_shutdown_permissions()
        else:
            # Linux/Raspberry Pi permission checking
            current_user = os.getenv('USER', 'unknown')
            
            # Check if running as root
            if os.geteuid() == 0:
                return {
                    'can_restart': True,
                    'method': 'root',
                    'reason': 'Running as root user',
                    'suggestions': []
                }
            
            # Check if user can use sudo without password for restart commands
            sudo_check = check_sudo_permissions()
            if sudo_check['can_sudo']:
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
            except:
                pass
            
            # Check if restart commands are available in PATH
            restart_available = check_command_availability(['reboot', 'shutdown', 'systemctl'])
            if restart_available:
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
        return {
            'can_restart': False,
            'method': 'error',
            'reason': f'Error checking permissions: {str(e)}',
            'suggestions': ['Check system configuration and try again']
        }

def execute_shutdown():
    """Execute shutdown command with proper permissions and fallbacks"""
    try:
        if platform.system() == 'Windows':
            # Windows shutdown
            shutdown_cmd = 'shutdown /s /t 5'
            print(f"Executing Windows command: {shutdown_cmd}")
            result = subprocess.run(shutdown_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'Windows shutdown initiated successfully',
                    'command_used': shutdown_cmd
                }
            else:
                return {
                    'success': False,
                    'error': f'Windows shutdown failed: {result.stderr}',
                    'command_used': shutdown_cmd
                }
        else:
            # Linux/Raspberry Pi shutdown with multiple fallback methods
            shutdown_commands = [
                # Try systemd first (most modern)
                ['systemctl', 'poweroff'],
                # Try sudo shutdown
                ['sudo', 'shutdown', '-h', 'now'],
                # Try sudo poweroff
                ['sudo', 'poweroff'],
                # Try sudo halt
                ['sudo', 'halt'],
                # Try direct shutdown (if user has permission)
                ['shutdown', '-h', 'now'],
                # Try direct poweroff
                ['poweroff'],
                # Try direct halt
                ['halt']
            ]
            
            for cmd in shutdown_commands:
                try:
                    print(f"Trying command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': f'Shutdown initiated successfully with: {" ".join(cmd)}',
                            'command_used': ' '.join(cmd)
                        }
                    else:
                        # Log the failure for debugging
                        print(f"Shutdown command failed: {' '.join(cmd)} - {result.stderr}")
                        continue
                except subprocess.TimeoutExpired:
                    # Command timed out, might still be working
                    return {
                        'success': True,
                        'message': f'Shutdown command timed out but may be working: {" ".join(cmd)}',
                        'command_used': ' '.join(cmd)
                    }
                except Exception as e:
                    print(f"Error executing shutdown command {' '.join(cmd)}: {str(e)}")
                    continue
            
            # If all commands failed
            return {
                'success': False,
                'error': 'All shutdown commands failed',
                'command_used': 'multiple_attempts'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Shutdown execution error: {str(e)}',
            'command_used': 'error'
        }

def execute_restart():
    """Execute restart command with proper permissions and fallbacks"""
    try:
        if platform.system() == 'Windows':
            # Windows restart
            restart_cmd = 'shutdown /r /t 5'
            print(f"Executing Windows command: {restart_cmd}")
            result = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': 'Windows restart initiated successfully',
                    'command_used': restart_cmd
                }
            else:
                return {
                    'success': False,
                    'error': f'Windows restart failed: {result.stderr}',
                    'command_used': restart_cmd
                }
        else:
            # Linux/Raspberry Pi restart with multiple fallback methods
            restart_commands = [
                # Try systemd first (most modern)
                ['systemctl', 'reboot'],
                # Try sudo reboot
                ['sudo', 'reboot'],
                # Try sudo shutdown -r
                ['sudo', 'shutdown', '-r', 'now'],
                # Try direct reboot (if user has permission)
                ['reboot'],
                # Try direct shutdown -r
                ['shutdown', '-r', 'now']
            ]
            
            for cmd in restart_commands:
                try:
                    print(f"Trying command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': f'Restart initiated successfully with: {" ".join(cmd)}',
                            'command_used': ' '.join(cmd)
                        }
                    else:
                        # Log the failure for debugging
                        print(f"Restart command failed: {' '.join(cmd)} - {result.stderr}")
                        continue
                except subprocess.TimeoutExpired:
                    # Command timed out, might still be working
                    return {
                        'success': True,
                        'message': f'Restart command timed out but may be working: {" ".join(cmd)}',
                        'command_used': ' '.join(cmd)
                    }
                except Exception as e:
                    print(f"Error executing restart command {' '.join(cmd)}: {str(e)}")
                    continue
            
            # If all commands failed
            return {
                'success': False,
                'error': 'All restart commands failed',
                'command_used': 'multiple_attempts'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Restart execution error: {str(e)}',
            'command_used': 'error'
        }

def simulate_backend_response(action):
    """Simulate the exact backend response logic"""
    print(f"\n{'='*60}")
    print(f"🔍 Simulating Backend Response for: {action.upper()}")
    print(f"{'='*60}")
    
    try:
        if action == 'shutdown':
            # Check permissions first
            permission_check = check_shutdown_permissions()
            print(f"Permission Check Result: {json.dumps(permission_check, indent=2)}")
            
            if not permission_check['can_shutdown']:
                response = {
                    "success": False, 
                    "message": f"Permission denied: {permission_check['reason']}",
                    "action": "shutdown",
                    "permission_details": permission_check,
                    "suggestions": permission_check['suggestions']
                }
            else:
                # Execute shutdown with proper command
                shutdown_result = execute_shutdown()
                print(f"Shutdown Execution Result: {json.dumps(shutdown_result, indent=2)}")
                
                if shutdown_result['success']:
                    response = {
                        "success": True,
                        "message": shutdown_result['message'],
                        "action": "shutdown",
                        "command_used": shutdown_result['command_used'],
                        "permission_method": permission_check['method'],
                        "platform": platform.system()
                    }
                else:
                    response = {
                        "success": False,
                        "message": f"Shutdown failed: {shutdown_result['error']}",
                        "action": "shutdown",
                        "permission_details": permission_check,
                        "suggestions": permission_check['suggestions']
                    }
                    
        elif action == 'restart':
            # Check permissions first
            permission_check = check_restart_permissions()
            print(f"Permission Check Result: {json.dumps(permission_check, indent=2)}")
            
            if not permission_check['can_restart']:
                response = {
                    "success": False, 
                    "message": f"Permission denied: {permission_check['reason']}",
                    "action": "restart",
                    "permission_details": permission_check,
                    "suggestions": permission_check['suggestions']
                }
            else:
                # Execute restart with proper command
                restart_result = execute_restart()
                print(f"Restart Execution Result: {json.dumps(restart_result, indent=2)}")
                
                if restart_result['success']:
                    response = {
                        "success": True,
                        "message": restart_result['message'],
                        "action": "restart",
                        "command_used": restart_result['command_used'],
                        "permission_method": permission_check['method'],
                        "platform": platform.system()
                    }
                else:
                    response = {
                        "success": False,
                        "message": f"Restart failed: {restart_result['error']}",
                        "action": "restart",
                        "permission_details": permission_check,
                        "suggestions": permission_check['suggestions']
                    }
        else:
            response = {"error": f"Unknown action: {action}"}
            
    except Exception as e:
        response = {"success": False, "message": f"{action.capitalize()} failed: {str(e)}"}
    
    print(f"\n📤 Final Backend Response:")
    print(f"{json.dumps(response, indent=2)}")
    
    return response

def main():
    """Main test function"""
    print("=" * 60)
    print("🔍 Backend Power Management Logic Test")
    print("=" * 60)
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print()
    
    # Check admin status first
    is_admin = check_windows_admin()
    print(f"🔑 Administrator Status: {'✅ Yes' if is_admin else '❌ No'}")
    
    if not is_admin:
        print("\n⚠️  IMPORTANT: You are NOT running as Administrator")
        print("   This explains why power management is failing!")
        print("   The backend will return 'success: false' due to permissions")
        print()
    
    # Test shutdown logic
    simulate_backend_response('shutdown')
    
    # Test restart logic
    simulate_backend_response('restart')
    
    print("\n" + "=" * 60)
    print("📋 Analysis:")
    print("=" * 60)
    
    if is_admin:
        print("✅ You are running as Administrator")
        print("   If power management still fails, the issue is elsewhere")
    else:
        print("❌ You are NOT running as Administrator")
        print("   This is why power management fails!")
        print("   The backend correctly detects permission issues")
        print("   But returns 'success: false' in the response")
    
    print("\n💡 To fix this:")
    print("   1. Run Command Prompt as Administrator")
    print("   2. Navigate to your project directory")
    print("   3. Run: python backend/simple_server.py")
    print("   4. Test power management from the frontend")
    print("\n🔍 The frontend shows 'HTTP Response Success' because:")
    print("   - The HTTP request/response cycle works")
    print("   - But the backend returns 'success: false' in the JSON body")
    print("   - This is correct behavior when permissions are insufficient")

if __name__ == "__main__":
    main()
