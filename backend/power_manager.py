#!/usr/bin/env python3
"""
Pi Monitor - Power Management
Handles system power operations like shutdown, restart, and sleep
"""

import json
import os
import platform
import subprocess
import time
import logging

logger = logging.getLogger(__name__)

class PowerManager:
    """Manages system power operations"""
    
    def __init__(self):
        pass
    
    def get_power_status(self):
        """Get current power status with permission info"""
        try:
            import psutil
            
            # Get current power status with permission info
            shutdown_perms = self._check_shutdown_permissions()
            restart_perms = self._check_restart_permissions()
            
            # Get current uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
            
            return {
                "success": True,
                "action": "status",
                "power_state": "on",
                "current_uptime": uptime_formatted,
                "uptime_seconds": int(uptime_seconds),
                "last_boot": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
                "available_actions": ["restart", "shutdown", "reboot"],
                "permissions": {
                    "shutdown": shutdown_perms,
                    "restart": restart_perms
                },
                "platform": platform.system()
            }
            
        except Exception as e:
            logger.error(f"Failed to get power status: {e}")
            return {"success": False, "message": f"Failed to get power status: {str(e)}"}
    
    def handle_power_action(self, request_handler):
        """Handle power management actions"""
        try:
            content_length = int(request_handler.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = request_handler.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                action = data.get('action', '')
                delay = data.get('delay', 0)
                
                # Get current system info
                import psutil
                uptime_seconds = time.time() - psutil.boot_time()
                uptime_hours = int(uptime_seconds // 3600)
                uptime_minutes = int((uptime_seconds % 3600) // 60)
                uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
                
                if action == 'shutdown':
                    shutdown_result = self._execute_shutdown()
                    if shutdown_result['success']:
                        return {
                            "success": True, 
                            "message": shutdown_result['message'],
                            "action": "shutdown",
                            "command_used": shutdown_result['command_used'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    else:
                        return {
                            "success": False, 
                            "message": f"Shutdown failed: {shutdown_result.get('error', 'Unknown error')}",
                            "action": "shutdown",
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    
                elif action == 'restart':
                    restart_result = self._execute_restart()
                    if restart_result['success']:
                        return {
                            "success": True, 
                            "message": restart_result['message'],
                            "action": "restart",
                            "command_used": restart_result['command_used'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    else:
                        return {
                            "success": False, 
                            "message": f"Restart failed: {restart_result.get('error', 'Unknown error')}",
                            "action": "restart",
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    
                elif action == 'status':
                    # Return current power status with permission info
                    shutdown_perms = self._check_shutdown_permissions()
                    restart_perms = self._check_restart_permissions()
                    
                    return {
                        "success": True,
                        "action": "status",
                        "power_state": "on",
                        "current_uptime": uptime_formatted,
                        "uptime_seconds": int(uptime_seconds),
                        "last_boot": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
                        "available_actions": ["restart", "shutdown", "reboot"],
                        "permissions": {
                            "shutdown": shutdown_perms,
                            "restart": restart_perms
                        },
                        "platform": platform.system()
                    }
                else:
                    return {"success": False, "message": f"Unknown action: {action}"}
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            logger.error(f"Power action failed: {e}")
            return {"success": False, "message": f"Power action failed: {str(e)}"}
    
    def shutdown(self):
        """Execute shutdown command"""
        try:
            shutdown_result = self._execute_shutdown()
            if shutdown_result['success']:
                return {
                    "success": True,
                    "message": shutdown_result['message'],
                    "action": "shutdown",
                    "command_used": shutdown_result['command_used'],
                    "platform": platform.system()
                }
            else:
                return {
                    "success": False,
                    "message": f"Shutdown failed: {shutdown_result.get('error', 'Unknown error')}",
                    "action": "shutdown"
                }
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            return {"success": False, "message": f"Shutdown failed: {str(e)}"}
    
    def restart(self):
        """Execute restart command"""
        try:
            restart_result = self._execute_restart()
            if restart_result['success']:
                return {
                    "success": True,
                    "message": restart_result['message'],
                    "action": "restart",
                    "command_used": restart_result['command_used'],
                    "platform": platform.system()
                }
            else:
                return {
                    "success": False,
                    "message": f"Restart failed: {restart_result.get('error', 'Unknown error')}",
                    "action": "restart"
                }
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            return {"success": False, "message": f"Restart failed: {str(e)}"}
    
    def sleep(self):
        """Execute sleep command"""
        try:
            # Try to put system to sleep (cross-platform)
            if platform.system() == 'Windows':
                os.system('powercfg /hibernate off')  # Disable hibernate first
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')  # Sleep
            else:
                os.system('systemctl suspend')
            
            return {
                "success": True,
                "message": "Sleep command sent",
                "action": "sleep",
                "platform": platform.system()
            }
        except Exception as e:
            logger.error(f"Sleep failed: {e}")
            return {"success": False, "message": f"Sleep failed: {str(e)}"}
    
    def _execute_shutdown(self):
        """Execute shutdown command with proper permissions and fallbacks"""
        try:
            if platform.system() == 'Windows':
                # Windows shutdown
                shutdown_cmd = 'shutdown /s /t 5'
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
                cmd = ['sudo', 'shutdown', '-h', 'now']
                try:
                    subprocess.run(cmd, timeout=15)
                    logger.info(f"Shutdown command executed: {' '.join(cmd)}")
                    return {
                        'success': True,
                        'message': 'Shutdown initiated',
                        'command_used': ' '.join(cmd)
                    }
                except subprocess.TimeoutExpired:
                    logger.info(f"Shutdown command timed out (expected): {' '.join(cmd)}")
                    return {
                        'success': True,
                        'message': 'Shutdown initiated (timeout expected)',
                        'command_used': ' '.join(cmd)
                    }
                except Exception as e:
                    logger.error(f"Shutdown failed: {str(e)}")
                    return {
                        'success': False,
                        'error': str(e),
                        'command_used': ' '.join(cmd)
                    }
        except Exception as e:
            logger.error(f"Shutdown execution error: {str(e)}")
            return {
                'success': False,
                'error': f'Shutdown execution error: {str(e)}',
                'command_used': 'error'
            }
    
    def _execute_restart(self):
        """Execute restart command using simple, reliable methods"""
        try:
            logger.info("🔄 Attempting system restart...")
            cmd = ['sudo', 'reboot']
            try:
                subprocess.run(cmd, timeout=15)
                logger.info(f"Restart command executed: {' '.join(cmd)}")
                return {
                    'success': True,
                    'message': 'Restart initiated',
                    'command_used': ' '.join(cmd)
                }
            except subprocess.TimeoutExpired:
                logger.info(f"Restart command timed out (expected): {' '.join(cmd)}")
                return {
                    'success': True,
                    'message': 'Restart initiated (timeout expected)',
                    'command_used': ' '.join(cmd)
                }
            except Exception as e:
                logger.error(f"Restart failed: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'command_used': ' '.join(cmd)
                }
        except Exception as e:
            logger.error(f"Restart execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'command_used': 'error'
            }
    
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
                                'Use Windows Task Scheduler with elevated privileges'
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
                logger.info(f"Checking shutdown permissions for user: {current_user}")
                
                # Check if running as root
                try:
                    if os.geteuid() == 0:
                        logger.info("Running as root user - shutdown allowed")
                        return {
                            'can_shutdown': True,
                            'method': 'root',
                            'reason': 'Running as root user',
                            'suggestions': []
                        }
                except AttributeError:
                    logger.info("geteuid not available on this platform")
                
                # Check if user can use sudo without password for shutdown commands
                sudo_check = self._check_sudo_permissions()
                if sudo_check['can_sudo']:
                    logger.info(f"User {current_user} can use sudo for shutdown")
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
                        logger.info(f"User {current_user} in sudo group but may need password")
                        return {
                            'can_shutdown': False,
                            'method': 'sudo_group',
                            'reason': f'User {current_user} in sudo group but may need password',
                            'suggestions': [
                                'Configure sudoers to allow shutdown without password',
                                'Run the backend as root user'
                            ]
                        }
                except Exception as e:
                    logger.error(f"Error checking groups: {str(e)}")
                
                return {
                    'can_shutdown': False,
                    'method': 'user',
                    'reason': f'User {current_user} lacks shutdown permissions',
                    'suggestions': [
                        'Run the backend as root user',
                        'Configure sudoers file for passwordless shutdown'
                    ]
                }
                    
        except Exception as e:
            logger.error(f"Error checking shutdown permissions: {str(e)}")
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
                logger.info(f"Checking restart permissions for user: {current_user}")
                
                # Check if running as root
                try:
                    if os.geteuid() == 0:
                        logger.info("Running as root user - restart allowed")
                        return {
                            'can_restart': True,
                            'method': 'root',
                            'reason': 'Running as root user',
                            'suggestions': []
                        }
                except AttributeError:
                    logger.info("geteuid not available on this platform")
                
                # Check if user can use sudo without password for restart commands
                sudo_check = self._check_sudo_permissions()
                if sudo_check['can_sudo']:
                    logger.info(f"User {current_user} can use sudo for restart")
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
                        logger.info(f"User {current_user} in sudo group but may need password")
                        return {
                            'can_restart': False,
                            'method': 'sudo_group',
                            'reason': f'User {current_user} in sudo group but may need password',
                            'suggestions': [
                                'Configure sudoers to allow restart without password',
                                'Run the backend as root user'
                            ]
                        }
                except Exception as e:
                    logger.error(f"Error checking groups: {str(e)}")
                
                return {
                    'can_restart': False,
                    'method': 'user',
                    'reason': f'User {current_user} lacks restart permissions',
                    'suggestions': [
                        'Run the backend as root user',
                        'Configure sudoers file for passwordless restart'
                    ]
                }
                    
        except Exception as e:
            logger.error(f"Error checking restart permissions: {str(e)}")
            return {
                'can_restart': False,
                'method': 'error',
                'reason': f'Error checking permissions: {str(e)}',
                'suggestions': ['Check system configuration and try again']
            }
    
    def _check_sudo_permissions(self):
        """Check if current user can use sudo without password for shutdown/restart commands"""
        try:
            logger.info("Testing sudo permissions for shutdown/restart commands...")
            
            # Test if user can run shutdown command with sudo without password
            test_commands = [
                ['sudo', '-n', 'shutdown', '--help'],
                ['sudo', '-n', 'poweroff', '--help'],
                ['sudo', '-n', 'reboot', '--help']
            ]
            
            for cmd in test_commands:
                try:
                    logger.info(f"Testing sudo command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info(f"Sudo command successful: {' '.join(cmd)}")
                        return {
                            'can_sudo': True,
                            'command': ' '.join(cmd),
                            'reason': 'Sudo command executed successfully without password'
                        }
                    else:
                        logger.info(f"Sudo command failed: {' '.join(cmd)} - return code: {result.returncode}")
                        if result.stderr:
                            logger.info(f"Error output: {result.stderr.strip()}")
                except subprocess.TimeoutExpired:
                    logger.info(f"Sudo command timed out: {' '.join(cmd)}")
                except Exception as e:
                    logger.info(f"Exception testing sudo command {' '.join(cmd)}: {str(e)}")
                    continue
            
            logger.info("No sudo commands worked without password")
            return {
                'can_sudo': False,
                'command': None,
                'reason': 'No sudo commands worked without password'
            }
            
        except Exception as e:
            logger.error(f"Error testing sudo: {str(e)}")
            return {
                'can_sudo': False,
                'command': None,
                'reason': f'Error testing sudo: {str(e)}'
            }
