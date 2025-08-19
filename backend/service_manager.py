#!/usr/bin/env python3
"""
Pi Monitor - Service Management
Handles system service control and management
"""

import json
import subprocess
import time
import logging
import platform
import shutil
import re

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages system services"""
    
    def __init__(self):
        # Kept for fallback when full enumeration is unavailable
        self.candidate_services = ['ssh', 'nginx', 'docker', 'pi-monitor']
    
    def get_services_list(self):
        """List services with status for ServiceManagement UI.

        On Linux, attempts to enumerate ALL services via systemd. On Windows, uses 'sc query'.
        Falls back to a small whitelist if enumeration is not available.
        """
        try:
            if platform.system() == 'Linux' and shutil.which('systemctl'):
                return self._list_systemd_services()
            if platform.system() == 'Windows' and shutil.which('sc'):
                return self._list_windows_services()
        except Exception as e:
            logger.warning(f"Service enumeration failed, falling back to candidates: {e}")

        # Fallback to the predefined small set
        services = []
        for svc in self.candidate_services:
            services.append(self._get_single_service_status(svc))
        return services

    def _list_systemd_services(self):
        """Enumerate services using systemctl list-units and list-unit-files."""
        services = []
        # Get active/runtime status and description
        result = subprocess.run(
            ['systemctl', 'list-units', '--type=service', '--all', '--no-legend', '--no-pager', '--plain'],
            capture_output=True, text=True, timeout=15
        )
        lines = result.stdout.splitlines() if result.returncode == 0 else []

        # Also gather enabled/disabled from unit-files
        enabled_map = {}
        try:
            files_out = subprocess.run(
                ['systemctl', 'list-unit-files', '--type=service', '--no-legend', '--no-pager'],
                capture_output=True, text=True, timeout=15
            )
            if files_out.returncode == 0:
                for line in files_out.stdout.splitlines():
                    # Format: UNITFILE <whitespace> STATE [PRESET]
                    parts = re.split(r"\s+", line.strip())
                    if len(parts) >= 2 and parts[0].endswith('.service'):
                        enabled_map[parts[0]] = (parts[1] == 'enabled')
        except Exception:
            pass

        def normalize_status(active_col: str) -> str:
            if active_col in ('active', 'running'):
                return 'running'
            if active_col in ('inactive', 'dead', 'failed'):
                return 'stopped' if active_col != 'failed' else 'failed'
            return active_col or 'unknown'

        for line in lines:
            # Columns: UNIT LOAD ACTIVE SUB DESCRIPTION
            parts = re.split(r"\s+", line.strip(), maxsplit=4)
            if len(parts) < 5:
                continue
            unit, load, active_col, sub, description = parts

            # Include ALL units, including templated and internal ones, as requested
            name = unit.replace('.service', '')
            status = normalize_status(active_col)
            active = (status == 'running')
            enabled = enabled_map.get(unit, False)
            services.append({
                'name': name,
                'status': status,
                'active': active,
                'enabled': enabled,
                'description': description or f'{name} service'
            })

        # Sort by active first then name; return all services
        services.sort(key=lambda s: (not s['active'], s['name']))
        return services

    def _list_windows_services(self):
        """Enumerate services on Windows using 'sc query' output."""
        services = []
        # 'sc query type= service state= all'
        result = subprocess.run(
            ['sc', 'query', 'type=', 'service', 'state=', 'all'],
            capture_output=True, text=True, timeout=20, shell=True
        )
        cur_name = None
        cur_state = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('SERVICE_NAME:'):
                if cur_name is not None:
                    services.append({
                        'name': cur_name,
                        'status': 'running' if cur_state == 'RUNNING' else 'stopped',
                        'active': cur_state == 'RUNNING',
                        'enabled': True,  # Windows enable state not trivial here
                        'description': f'{cur_name} service'
                    })
                cur_name = line.split(':', 1)[1].strip()
                cur_state = None
            elif line.startswith('STATE'):
                # e.g., STATE              : 4  RUNNING
                if 'RUNNING' in line:
                    cur_state = 'RUNNING'
                elif 'STOPPED' in line:
                    cur_state = 'STOPPED'
        if cur_name is not None:
            services.append({
                'name': cur_name,
                'status': 'running' if cur_state == 'RUNNING' else 'stopped',
                'active': cur_state == 'RUNNING',
                'enabled': True,
                'description': f'{cur_name} service'
            })
        return services

    def _get_single_service_status(self, svc_name: str):
        """Return a uniform service dict for a single named service using best-effort checks."""
        status = 'unknown'
        active = False
        enabled = False
        try:
            if shutil.which('systemctl'):
                result = subprocess.run(['systemctl', 'is-active', svc_name], capture_output=True, text=True, timeout=5)
                raw = result.stdout.strip()
                status = raw if result.returncode == 0 else 'stopped'
                active = (raw in ('active', 'running'))
                result2 = subprocess.run(['systemctl', 'is-enabled', svc_name], capture_output=True, text=True, timeout=5)
                enabled = (result2.returncode == 0 and 'enabled' in result2.stdout)
        except Exception:
            pass
        return {
            'name': svc_name,
            'status': 'running' if active else ('stopped' if status == 'stopped' else status or 'unknown'),
            'active': active,
            'enabled': enabled,
            'description': f'{svc_name} service'
        }
    
    def handle_service_action(self, request_handler):
        """Handle service control actions"""
        try:
            content_length = int(request_handler.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = request_handler.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                service_name = data.get('service_name', '')
                action = data.get('action', '')
                
                if action == 'status':
                    return {"success": True, "message": f"Service {service_name} status checked"}
                elif action in ['start', 'stop', 'restart']:
                    try:
                        # Resolve absolute paths to match sudoers rules
                        systemctl_path = shutil.which('systemctl') or 'systemctl'
                        service_path = shutil.which('service') or 'service'
                        sudo_path = shutil.which('sudo')

                        # Try plain systemctl first
                        result = subprocess.run([systemctl_path, action, service_name], capture_output=True, text=True)
                        if result.returncode == 0:
                            return {"success": True, "message": f"Service {service_name} {action} successful"}

                        # If we hit an auth error, try sudo non-interactively (requires sudoers NOPASSWD)
                        stderr = (result.stderr or '').lower()
                        if any(word in stderr for word in ['access denied', 'permission', 'authentication is required', 'not authorized', 'polkit']):
                            if sudo_path:
                                sudo_result = subprocess.run([sudo_path, '-n', systemctl_path, action, service_name], capture_output=True, text=True)
                                if sudo_result.returncode == 0:
                                    return {"success": True, "message": f"Service {service_name} {action} successful (sudo)"}
                                else:
                                    # Try sudo with service command as a fallback
                                    service_cmd = [sudo_path, '-n', service_path, service_name, action]
                                    svc_result = subprocess.run(service_cmd, capture_output=True, text=True)
                                    if svc_result.returncode == 0:
                                        return {"success": True, "message": f"Service {service_name} {action} successful via 'service' (sudo)"}
                                    # Return combined stderr for diagnostics
                                    combined_err = (sudo_result.stderr or '') + '\n' + (svc_result.stderr or '')
                                    return {"success": False, "message": f"Service control failed (sudo): {combined_err.strip()}"}

                        # Fallback to alternatives
                        alt = self._handle_service_action_alternative(service_name, action)
                        # If alternative failed, include original stderr for context
                        if not alt.get('success'):
                            alt_msg = alt.get('message') or alt.get('error') or 'unknown error'
                            return {"success": False, "message": f"Service control failed: {alt_msg}. systemctl stderr: {(result.stderr or '').strip()}"}
                        return alt
                    except FileNotFoundError:
                        return self._handle_service_action_alternative(service_name, action)
                    except Exception as e:
                        return {"success": False, "message": f"Service control failed: {str(e)}"}
                else:
                    return {"success": False, "message": f"Unknown action: {action}"}
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            logger.error(f"Service action failed: {e}")
            return {"success": False, "message": f"Service action failed: {str(e)}"}
    
    def restart_service(self):
        """Safely restart the pi-monitor service"""
        try:
            logger.info("🔄 Attempting safe restart of pi-monitor service...")
            
            # Method 1: Try systemctl first (most reliable)
            try:
                logger.info("  🔧 Trying systemctl restart...")
                result = subprocess.run(['systemctl', 'restart', 'pi-monitor'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("  ✅ systemctl restart successful")
                    return {
                        'success': True,
                        'message': 'Pi-monitor service restarted successfully using systemctl',
                        'method': 'systemctl',
                        'command_used': 'systemctl restart pi-monitor',
                        'safety_level': 'high',
                        'description': 'Service restart only - no system impact'
                    }
                else:
                    logger.info(f"  ❌ systemctl restart failed: {result.stderr}")
            except Exception as e:
                logger.info(f"  ❌ systemctl restart exception: {str(e)}")
            
            # Method 2: Try service command (fallback)
            try:
                logger.info("  🔧 Trying service restart...")
                result = subprocess.run(['service', 'pi-monitor', 'restart'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("  ✅ service restart successful")
                    return {
                        'success': True,
                        'message': 'Pi-monitor service restarted successfully using service command',
                        'method': 'service',
                        'command_used': 'service pi-monitor restart',
                        'safety_level': 'high',
                        'description': 'Service restart only - no system impact'
                    }
                else:
                    logger.info(f"  ❌ service restart failed: {result.stderr}")
            except Exception as e:
                logger.info(f"  ❌ service restart exception: {str(e)}")
            
            # Method 3: Try Docker restart if running in container
            try:
                logger.info("  🔧 Trying Docker restart...")
                result = subprocess.run(['docker', 'restart', 'pi-monitor'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("  ✅ Docker restart successful")
                    return {
                        'success': True,
                        'message': 'Pi-monitor container restarted successfully using Docker',
                        'method': 'docker',
                        'command_used': 'docker restart pi-monitor',
                        'safety_level': 'high',
                        'description': 'Container restart only - no system impact'
                    }
                else:
                    logger.info(f"  ❌ Docker restart failed: {result.stderr}")
            except Exception as e:
                logger.info(f"  ❌ Docker restart exception: {str(e)}")
            
            # If all methods failed
            logger.error("  ❌ All safe restart methods failed")
            return {
                'success': False,
                'error': 'All safe restart methods failed',
                'methods_tried': ['systemctl', 'service', 'docker'],
                'suggestions': [
                    'Check if pi-monitor service is properly configured',
                    'Verify systemctl/service commands are available',
                    'Check Docker if running in container',
                    'Review system logs for errors'
                ],
                'safety_level': 'high',
                'description': 'No restart attempted - system remains stable'
            }
            
        except Exception as e:
            logger.error(f"❌ Safe restart error: {str(e)}")
            return {
                'success': False,
                'error': f'Safe restart error: {str(e)}',
                'safety_level': 'high',
                'description': 'Exception occurred - no restart attempted'
            }
    
    def manage_service(self, request_handler):
        """Safely manage the pi-monitor service (start/stop/status)"""
        try:
            content_length = int(request_handler.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = request_handler.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                action = data.get('action', 'status')
            else:
                action = 'status'
            
            logger.info(f"🔧 Attempting {action} of pi-monitor service...")
            
            if action == 'start':
                try:
                    result = subprocess.run(['systemctl', 'start', 'pi-monitor'], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': 'Pi-monitor service started successfully',
                            'method': 'systemctl',
                            'action': 'start'
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'Failed to start service: {result.stderr}',
                            'action': 'start'
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Exception starting service: {str(e)}',
                        'action': 'start'
                    }
                    
            elif action == 'stop':
                try:
                    result = subprocess.run(['systemctl', 'stop', 'pi-monitor'], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': 'Pi-monitor service stopped successfully',
                            'method': 'systemctl',
                            'action': 'stop'
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'Failed to stop service: {result.stderr}',
                            'action': 'stop'
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Exception stopping service: {str(e)}',
                        'action': 'stop'
                    }
                    
            elif action == 'status':
                try:
                    result = subprocess.run(['systemctl', 'is-active', 'pi-monitor'], 
                                          capture_output=True, text=True, timeout=10)
                    status = result.stdout.strip() if result.returncode == 0 else 'unknown'
                    
                    detailed_result = subprocess.run(['systemctl', 'status', 'pi-monitor', '--no-pager'], 
                                                  capture_output=True, text=True, timeout=15)
                    detailed_status = detailed_result.stdout if detailed_result.returncode == 0 else 'Status unavailable'
                    
                    return {
                        'success': True,
                        'status': status,
                        'detailed_status': detailed_status,
                        'action': 'status'
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Exception checking status: {str(e)}',
                        'action': 'status'
                    }
                    
            else:
                return {
                    'success': False,
                    'error': f'Unknown action: {action}',
                    'available_actions': ['start', 'stop', 'status']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Service management error: {str(e)}',
                'action': action
            }
    
    def get_restart_info(self):
        """Get service restart information"""
        return {
            "endpoint": "/api/service/restart",
            "description": "Safe service restart endpoint",
            "methods": {
                "GET": "Get endpoint information",
                "POST": "Execute safe service restart"
            },
            "safety_features": [
                "No system shutdown/restart",
                "Service restart only",
                "Multiple fallback methods",
                "Graceful process handling"
            ],
            "available_methods": [
                "systemctl restart",
                "service restart", 
                "docker restart"
            ],
            "usage": {
                "method": "POST",
                "headers": "Authorization: Bearer <token>",
                "body": "{} (no body required)"
            }
        }
    
    def get_manage_info(self):
        """Get service management information"""
        return {
            "endpoint": "/api/service/manage",
            "description": "Service management endpoint",
            "methods": {
                "GET": "Get endpoint information",
                "POST": "Execute service management actions"
            },
            "available_actions": ["start", "stop", "status"],
            "safety_features": [
                "Service-level operations only",
                "No system impact",
                "Standard systemctl/service commands"
            ],
            "usage": {
                "method": "POST",
                "headers": "Authorization: Bearer <token>",
                "body": '{"action": "start|stop|status"}'
            }
        }
    
    def get_service_info(self):
        """Get service management information"""
        try:
            service_info = self._get_service_management_info()
            return {
                "success": True,
                "service_management": service_info,
                "endpoint_info": {
                    "description": "Service management information and recommendations",
                    "available_endpoints": [
                        "/api/service/restart - Safe service restart",
                        "/api/service/manage - Service start/stop/status",
                        "/api/service/info - Service management info"
                    ]
                }
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to get service info: {str(e)}"}
    
    def _get_service_management_info(self):
        """Get information about available service management methods"""
        try:
            info = {
                'available_methods': [],
                'systemctl_available': False,
                'service_available': False,
                'docker_available': False,
                'recommendations': []
            }
            
            # Check systemctl availability
            try:
                result = subprocess.run(['systemctl', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['systemctl_available'] = True
                    info['available_methods'].append('systemctl')
                    info['recommendations'].append('Use systemctl for service management (most reliable)')
            except:
                pass
            
            # Check service command availability
            try:
                result = subprocess.run(['service', '--help'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['service_available'] = True
                    info['available_methods'].append('service')
                    info['recommendations'].append('Use service command as fallback')
            except:
                pass
            
            # Check Docker availability
            try:
                result = subprocess.run(['docker', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['docker_available'] = True
                    info['available_methods'].append('docker')
                    info['recommendations'].append('Use Docker commands if running in container')
            except:
                pass
            
            # Add safety recommendations
            info['safety_recommendations'] = [
                'Service restart is safer than system restart',
                'Use systemctl/service commands when possible',
                'Avoid direct shutdown/reboot commands',
                'Monitor service logs for issues'
            ]
            
            return info
            
        except Exception as e:
            return {
                'error': f'Failed to get service management info: {str(e)}'
            }
    
    def _handle_service_action_alternative(self, service_name, action):
        """Handle service actions using alternative methods when systemctl is not available"""
        try:
            if platform.system() == 'Windows':
                # Windows service control using sc command
                if action == 'start':
                    result = subprocess.run(['sc', 'start', service_name], capture_output=True, text=True, shell=True)
                    if result.returncode == 0:
                        return {"success": True, "message": f"Service {service_name} started successfully using sc command"}
                    else:
                        return {"success": False, "message": f"Service {service_name} start failed: {result.stderr}"}
                elif action == 'stop':
                    result = subprocess.run(['sc', 'stop', service_name], capture_output=True, text=True, shell=True)
                    if result.returncode == 0:
                        return {"success": True, "message": f"Service {service_name} stopped successfully using sc command"}
                    else:
                        return {"success": False, "message": f"Service {service_name} stop failed: {result.stderr}"}
                elif action == 'restart':
                    stop_result = subprocess.run(['sc', 'stop', service_name], capture_output=True, text=True, shell=True)
                    time.sleep(2)  # Wait a bit
                    start_result = subprocess.run(['sc', 'start', service_name], capture_output=True, text=True, shell=True)
                    if start_result.returncode == 0:
                        return {"success": True, "message": f"Service {service_name} restarted successfully using sc command"}
                    else:
                        return {"success": False, "message": f"Service {service_name} restart failed: {start_result.stderr}"}
                elif action == 'status':
                    result = subprocess.run(['sc', 'query', service_name], capture_output=True, text=True, shell=True)
                    if 'RUNNING' in result.stdout:
                        return {"success": True, "service": service_name, "status": "running"}
                    else:
                        return {"success": True, "service": service_name, "status": "stopped"}
            else:
                # Linux service control using service command
                if service_name in ['ssh', 'nginx', 'docker']:
                    try:
                        result = subprocess.run(['service', service_name, action], capture_output=True, text=True)
                        if result.returncode == 0:
                            return {"success": True, "message": f"{service_name} service {action} using service command"}
                        else:
                            return {"success": False, "message": f"{service_name} {action} failed: {result.stderr}"}
                    except:
                        return {"success": False, "message": f"{service_name} service control not available"}
            
            # Default fallback for unknown services
            return {"success": False, "message": f"Service {service_name} control not available"}
            
        except Exception as e:
            return {"success": False, "message": f"Alternative service control failed: {str(e)}"}
