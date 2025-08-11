#!/usr/bin/env python3
"""
Pi Monitor - Enhanced HTTP Server
RPi-Monitor inspired monitoring system with real-time data collection
Enhanced with comprehensive system monitoring commands
"""

import json
import time
import os
import subprocess
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import base64
import hmac
import hashlib
import sys
import platform
import socket
from datetime import datetime, timedelta
import sqlite3
import tempfile
import re

# Add parent directory to path to import config
try:
    # Try to import from parent directory first
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import config
except ImportError:
    # Fallback: try to import from current directory
    try:
        from config import config
    except ImportError:
        # Create a minimal config if import fails
        class MinimalConfig:
            def get(self, key, default=None):
                if key == 'ports.backend':
                    return 5001
                elif key == 'project.version':
                    return '2.0.0'
                elif key == 'backend.endpoints':
                    return {}
                elif key == 'backend.features':
                    return {}
                return default
            
            def get_port(self, service):
                return 5001 if service == 'backend' else 80
            
            def get_backend_endpoints(self):
                return {}
        
        config = MinimalConfig()

# Simple JWT-like token (for demo purposes)
JWT_SECRET = "pi-monitor-secret-key-2024"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours

# Enhanced system monitoring commands
SYSTEM_COMMANDS = {
    # System Information
    'kernel_info': 'uname -a',
    'cpu_info': 'cat /proc/cpuinfo',
    'memory_info': 'cat /proc/meminfo',
    'disk_partitions': 'cat /proc/partitions',
    'os_release': 'lsb_release -a',
    'kernel_messages': 'dmesg | tail -20',
    'system_version': 'cat /proc/version',
    'hostname_info': 'hostnamectl',
    
    # Hardware Detection
    'arm_memory': 'vcgencmd get_mem arm',
    'gpu_memory': 'vcgencmd get_mem gpu',
    'device_model': 'cat /proc/device-tree/model',
    'cpu_architecture': 'lscpu',
    'usb_devices': 'lsusb',
    'pci_devices': 'lspci',
    
    # Resource Usage
    'system_load': 'uptime',
    'load_average': 'cat /proc/loadavg',
    'memory_usage': 'free -h',
    'memory_detailed': 'cat /proc/meminfo',
    'disk_usage': 'df -h',
    'disk_io_stats': 'cat /proc/diskstats',
    'process_list': 'ps aux --sort=-%cpu | head -10',
    'top_processes': 'ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%cpu | head -10',
    
    # Network Information
    'network_interfaces': 'ip a',
    'network_stats': 'cat /proc/net/dev',
    'network_connections': 'ss -tuln',
    'routing_table': 'ip route',
    'dns_servers': 'cat /etc/resolv.conf',
    
    # Raspberry Pi Specific (with fallbacks)
    'cpu_temperature': 'vcgencmd measure_temp',
    'arm_clock': 'vcgencmd measure_clock arm',
    'core_clock': 'vcgencmd measure_clock core',
    'gpu_clock': 'vcgencmd measure_clock h264',
    'core_voltage': 'vcgencmd measure_volts core',
    'throttling_status': 'vcgencmd get_throttled',
    'pi_config': 'vcgencmd get_config int',
    
    # System Services
    'service_status': 'systemctl list-units --type=service --state=running',
    'docker_status': 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"',
    'ssh_status': 'systemctl status ssh --no-pager',
    
    # System Logs
    'recent_logs': 'tail -50 /var/log/syslog',
    'auth_logs': 'tail -20 /var/log/auth.log',
    'kernel_logs': 'journalctl -k --no-pager | tail -20',
    
    # Performance Monitoring
    'cpu_stats': 'mpstat 1 1',
    'memory_stats': 'vmstat 1 1',
    'disk_stats': 'iostat 1 1',
    'network_stats': 'cat /proc/net/snmp'
}

# Global data storage for real-time metrics
class EnhancedMetricsCollector:
    def __init__(self):
        self.metrics_history = []
        self.max_history = 1000  # Keep last 1000 data points
        self.collection_interval = 5.0  # 5 seconds
        self.is_collecting = False
        self.collection_thread = None
        self.command_cache = {}
        self.cache_duration = 30  # Cache command results for 30 seconds
        
    def start_collection(self):
        """Start background metrics collection"""
        if not self.is_collecting:
            self.is_collecting = True
            self.collection_thread = threading.Thread(target=self._collect_metrics, daemon=True)
            self.collection_thread.start()
    
    def stop_collection(self):
        """Stop background metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=1)
    
    def _collect_metrics(self):
        """Background thread for collecting metrics"""
        while self.is_collecting:
            try:
                metrics = self._gather_current_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only recent history
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                    
            except Exception as e:
                print(f"Error collecting metrics: {e}")
            
            time.sleep(self.collection_interval)
    
    def _gather_current_metrics(self):
        """Gather current system metrics with enhanced data"""
        try:
            # Basic metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            temperature = self._get_temperature()
            network = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()
            
            # Enhanced metrics using system commands
            enhanced_metrics = self._get_enhanced_metrics()
            
            return {
                "timestamp": time.time(),
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "disk_percent": round(disk.percent, 1),
                "temperature": temperature,
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "disk_io": {
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0
                },
                "enhanced": enhanced_metrics
            }
        except Exception as e:
            return {"timestamp": time.time(), "error": str(e)}
    
    def _get_enhanced_metrics(self):
        """Get enhanced metrics using system commands"""
        enhanced = {}
        
        # Get key metrics that don't change frequently
        key_commands = ['cpu_temperature', 'arm_clock', 'core_voltage', 'throttling_status']
        
        for metric in key_commands:
            if metric in SYSTEM_COMMANDS:
                try:
                    result = self._run_command_cached(SYSTEM_COMMANDS[metric])
                    if result['success']:
                        enhanced[metric] = result['output']
                    else:
                        enhanced[metric] = None
                except:
                    enhanced[metric] = None
        
        return enhanced
    
    def _run_command_cached(self, command):
        """Run a command with caching to avoid excessive execution"""
        cache_key = command
        
        # Check if we have a cached result
        if cache_key in self.command_cache:
            cached_time, cached_result = self.command_cache[cache_key]
            if time.time() - cached_time < self.cache_duration:
                return cached_result
        
        # Run the command
        result = self._run_command(command)
        
        # Cache the result
        self.command_cache[cache_key] = (time.time(), result)
        
        return result
    
    def _run_command(self, command):
        """Run a system command safely"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout.strip(),
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'output': None,
                    'error': result.stderr.strip()
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': None,
                'error': 'Command timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': str(e)
            }
    
    def _get_temperature(self):
        """Get system temperature using multiple methods"""
        try:
            # Try Raspberry Pi specific path
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = f.read().strip()
                    temp_value = float(temp_raw) / 1000.0
                    if temp_value > 0 and temp_value < 200:  # Sanity check for reasonable temperature range
                        return round(temp_value, 1)
            
            # Try other thermal zones
            for i in range(10):
                thermal_path = f'/sys/class/thermal/thermal_zone{i}/temp'
                if os.path.exists(thermal_path):
                    with open(thermal_path, 'r') as f:
                        temp_raw = f.read().strip()
                        temp_value = float(temp_raw) / 1000.0
                        if temp_value > 0 and temp_value < 200:  # Sanity check for reasonable temperature range
                            return round(temp_value, 1)
            
            # Try vcgencmd for Raspberry Pi
            try:
                result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    temp_match = re.search(r'temp=(\d+\.?\d*)', result.stdout)
                    if temp_match:
                        temp_value = float(temp_match.group(1))
                        if temp_value > 0 and temp_value < 200:  # Sanity check for reasonable temperature range
                            return round(temp_value, 1)
            except:
                pass
            
            # Try sensors command if available
            try:
                result = subprocess.run(['sensors', '-j'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    # Parse sensors output for temperature
                    for device, values in data.items():
                        if isinstance(values, dict):
                            for key, value in values.items():
                                if 'temp' in key.lower() and isinstance(value, (int, float)):
                                    temp_value = float(value)
                                    if temp_value > 0 and temp_value < 200:  # Sanity check for reasonable temperature range
                                        return round(temp_value, 1)
            except:
                pass
                
        except Exception:
            pass
        
        # Return a safe default value if all methods fail
        return 25.0  # Room temperature as safe default
    
    def _run_command_with_fallback(self, command_name, primary_command, fallback_commands=None):
        """Run a command with fallback options for Pi-specific commands"""
        # Try primary command first
        result = self._run_command(primary_command)
        
        if result['success']:
            return result
        
        # If primary failed and we have fallbacks, try them
        if fallback_commands:
            for fallback_cmd in fallback_commands:
                fallback_result = self._run_command(fallback_cmd)
                if fallback_result['success']:
                    return fallback_result
        
        # If all failed, return the original error but with fallback info
        if command_name in ['cpu_temperature', 'arm_clock', 'core_voltage', 'throttling_status']:
            result['fallback_available'] = True
            result['fallback_suggestion'] = 'Use alternative system commands for hardware monitoring'
        
        return result
    
    def get_metrics_history(self, minutes=60):
        """Get metrics history for the last N minutes"""
        cutoff_time = time.time() - (minutes * 60)
        return [m for m in self.metrics_history if m.get('timestamp', 0) > cutoff_time]
    
    def get_latest_metrics(self):
        """Get the most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def run_system_command(self, command_name):
        """Run a specific system command by name with fallbacks for Pi-specific commands"""
        if command_name in SYSTEM_COMMANDS:
            primary_command = SYSTEM_COMMANDS[command_name]
            
            # Define fallback commands for Pi-specific hardware monitoring
            fallback_commands = {
                'cpu_temperature': [
                    'cat /sys/class/thermal/thermal_zone0/temp',
                    'cat /sys/class/thermal/thermal_zone1/temp',
                    'sensors -j'
                ],
                'arm_clock': [
                    'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq',
                    'cat /proc/cpuinfo | grep "cpu MHz"'
                ],
                'core_voltage': [
                    'cat /sys/class/hwmon/hwmon*/in1_input',
                    'cat /sys/class/hwmon/hwmon*/in2_input'
                ],
                'throttling_status': [
                    'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor',
                    'cat /proc/cpuinfo | grep "flags"'
                ]
            }
            
            # Use fallback system for Pi-specific commands
            if command_name in fallback_commands:
                return self._run_command_with_fallback(
                    command_name, 
                    primary_command, 
                    fallback_commands[command_name]
                )
            else:
                return self._run_command(primary_command)
        else:
            return {
                'success': False,
                'output': None,
                'error': f'Unknown command: {command_name}'
            }
    
    def get_available_commands(self):
        """Get list of available system commands"""
        return list(SYSTEM_COMMANDS.keys())

# Global metrics collector instance
metrics_collector = EnhancedMetricsCollector()

class SimplePiMonitorHandler(BaseHTTPRequestHandler):
    # Class variable to persist tokens between requests
    auth_tokens = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        if path == '/':
            # Root endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            
            response = {
                "message": "Pi Monitor Backend is running!",
                "status": "ok",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": config.get('project.version', '1.0.0'),
                "endpoints": config.get_backend_endpoints(),
                "features": config.get('backend.features', {}),
                "system_info": self._get_system_info(),
                "available_commands": len(SYSTEM_COMMANDS),
                "enhanced_monitoring": True
            }
            self.wfile.write(json.dumps(response).encode())
                
        elif path.startswith('/api/logs/') and '/download' in path:
            # Log download endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                try:
                    # Extract log name from path
                    log_name = path.split('/')[-2]  # /api/logs/name/download
                    
                    # Try to find the log file in available directories
                    log_file = None
                    log_dirs = ['/var/log', '/tmp', './logs', 'logs']
                    
                    for log_dir in log_dirs:
                        potential_path = os.path.join(log_dir, log_name)
                        if os.path.exists(potential_path):
                            log_file = potential_path
                            break
                    
                    if not log_file:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        response = {"error": f"Log file {log_name} not found"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                    
                    # Read log content
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.send_header('Content-Disposition', f'attachment; filename="{log_name}"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    self.wfile.write(content.encode())
                    
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {"error": f"Failed to download log: {str(e)}"}
                    self.wfile.write(json.dumps(response).encode())
                
        elif path.startswith('/api/logs/') and path.endswith('/clear'):
            # Log clear endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                try:
                    # Extract log name from path
                    log_name = path.split('/')[-2]  # /api/logs/name/clear
                    
                    # Try to find the log file in available directories
                    log_file = None
                    log_dirs = ['/var/log', '/tmp', './logs', 'logs']
                    
                    for log_dir in log_dirs:
                        potential_path = os.path.join(log_dir, log_name)
                        if os.path.exists(potential_path):
                            log_file = potential_path
                            break
                    
                    if not log_file:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        response = {"error": f"Log file {log_name} not found"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                    
                    # Clear log file (truncate to 0 bytes)
                    with open(log_file, 'w') as f:
                        pass  # This truncates the file
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                    self.end_headers()
                    
                    response = {
                        "success": True,
                        "message": f"Log {log_name} cleared successfully",
                        "log_name": log_name,
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    self.wfile.write(json.dumps(response).encode())
                    
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {"error": f"Failed to clear log: {str(e)}"}
                    self.wfile.write(json.dumps(response).encode())
                
        elif path.startswith('/api/services/'):
            # Service control endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                try:
                    # Extract service name and action from path
                    path_parts = path.split('/')
                    if len(path_parts) >= 4:
                        service_name = path_parts[3]
                        action = path_parts[4] if len(path_parts) > 4 else 'status'
                        
                        # Handle service actions
                        if action == 'start':
                            result = os.system(f'systemctl start {service_name}')
                            if result == 0:
                                response = {"success": True, "message": f"Service {service_name} started successfully"}
                            else:
                                response = {"success": False, "message": f"Failed to start service {service_name}"}
                        elif action == 'stop':
                            result = os.system(f'systemctl stop {service_name}')
                            if result == 0:
                                response = {"success": True, "message": f"Service {service_name} stopped successfully"}
                            else:
                                response = {"success": False, "message": f"Failed to stop service {service_name}"}
                        elif action == 'restart':
                            result = os.system(f'systemctl restart {service_name}')
                            if result == 0:
                                response = {"success": True, "message": f"Service {service_name} restarted successfully"}
                            else:
                                response = {"success": False, "message": f"Failed to restart service {service_name}"}
                        elif action == 'status':
                            result = os.system(f'systemctl is-active {service_name}')
                            if result == 0:
                                response = {"success": True, "service": service_name, "status": "active"}
                            else:
                                response = {"success": True, "service": service_name, "status": "inactive"}
                        else:
                            response = {"success": False, "message": f"Unknown action: {action}"}
                    else:
                        response = {"success": False, "message": "Invalid service path"}
                        
                except Exception as e:
                    response = {"success": False, "message": f"Service action failed: {str(e)}"}
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/health':
            # Health check
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "version": config.get('project.version', '1.0.0'),
                "uptime": self._get_uptime(),
                "config": {
                    "ports": config.get('ports', {}),
                    "features": config.get('backend.features', {})
                },
                "enhanced_monitoring": True
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/api/system':
            # System stats endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                # Get real-time or historical data based on query params
                if 'history' in query_params:
                    minutes = int(query_params.get('history', ['60'])[0])
                    response = self._get_system_stats_with_history(minutes)
                elif 'enhanced' in query_params:
                    # Return enhanced stats with formatted values and status indicators
                    response = self._get_enhanced_system_stats()
                else:
                    response = self._get_system_stats()
                    
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/system/enhanced':
            # Enhanced system stats endpoint with formatted values and status indicators
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                response = self._get_enhanced_system_stats()
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/metrics':
            # Metrics endpoint for historical data
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                minutes = int(query_params.get('minutes', ['60'])[0])
                response = {
                    "metrics": metrics_collector.get_metrics_history(minutes),
                    "collection_status": {
                        "active": metrics_collector.is_collecting,
                        "interval": metrics_collector.collection_interval,
                        "total_points": len(metrics_collector.metrics_history)
                    }
                }
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/metrics/history':
            # Metrics history endpoint for historical data
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                minutes = int(query_params.get('minutes', ['60'])[0])
                response = {
                    "metrics": metrics_collector.get_metrics_history(minutes),
                    "collection_status": {
                        "active": metrics_collector.is_collecting,
                        "collection_interval": metrics_collector.collection_interval,
                        "total_points": len(metrics_collector.metrics_history)
                    }
                }
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/services':
            # Services endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = self._get_services_status()
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/power':
            # Power management endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = self._get_power_status()
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/system/info':
            # Detailed system information
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            response = self._get_detailed_system_info()
            self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/network':
            # Network information endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Get network interface information
                    network_info = {}
                    for interface, addrs in psutil.net_if_addrs().items():
                        network_info[interface] = {
                            'addresses': [addr.address for addr in addrs if addr.family == socket.AF_INET],
                            'mac': [addr.address for addr in addrs if addr.family == socket.AF_LINK]
                        }
                    
                    response = {
                        "interfaces": network_info,
                        "default_gateway": self._run_command_with_fallback('gateway', 'ip route | grep default | head -1', ['route -n | grep "^0.0.0.0" | head -1']),
                        "dns_servers": self._run_command_with_fallback('dns', 'cat /etc/resolv.conf | grep nameserver', ['cat /etc/resolv.conf']),
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as e:
                    response = {"error": f"Failed to get network info: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/network/stats':
            # Network statistics endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Get network I/O statistics
                    net_io = psutil.net_io_counters()
                    response = {
                        "bytes_sent": net_io.bytes_sent,
                        "bytes_recv": net_io.bytes_recv,
                        "packets_sent": net_io.packets_sent,
                        "packets_recv": net_io.packets_recv,
                        "errin": net_io.errin,
                        "errout": net_io.errout,
                        "dropin": net_io.dropin,
                        "dropout": net_io.dropout,
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as e:
                    response = {"error": f"Failed to get network stats: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/logs':
            # Available logs endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Get available log files - try multiple log directories
                    log_dirs = ['/var/log', '/tmp', './logs', 'logs']
                    available_logs = []
                    
                    for log_dir in log_dirs:
                        if os.path.exists(log_dir):
                            try:
                                for filename in os.listdir(log_dir):
                                    if filename.endswith('.log') or filename in ['syslog', 'messages', 'auth.log', 'system.log']:
                                        filepath = os.path.join(log_dir, filename)
                                        if os.path.isfile(filepath):
                                            try:
                                                stat = os.stat(filepath)
                                                available_logs.append({
                                                    'name': filename,
                                                    'size': f"{stat.st_size / 1024:.1f} KB",
                                                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                                    'path': log_dir
                                                })
                                            except (OSError, PermissionError):
                                                # Skip files we can't access
                                                continue
                            except (OSError, PermissionError):
                                # Skip directories we can't access
                                continue
                    
                    # If no logs found, create a sample log for testing
                    if not available_logs:
                        sample_log_path = './logs/system.log'
                        os.makedirs('./logs', exist_ok=True)
                        with open(sample_log_path, 'w') as f:
                            f.write(f"{datetime.now().strftime('%b %d %H:%M:%S')} INFO: Pi Monitor started\n")
                            f.write(f"{datetime.now().strftime('%b %d %H:%M:%S')} INFO: System monitoring active\n")
                        
                        stat = os.stat(sample_log_path)
                        available_logs.append({
                            'name': 'system.log',
                            'size': f"{stat.st_size / 1024:.1f} KB",
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'path': './logs'
                        })
                    
                    response = {
                        "logs": available_logs,
                        "log_directory": log_dirs[0] if available_logs else './logs',
                        "total_logs": len(available_logs)
                    }
                except Exception as e:
                    response = {"error": f"Failed to get available logs: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path.startswith('/api/logs/') and '/download' not in path:
            # Log content endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                try:
                    # Extract log name from path
                    log_name = path.split('/')[-1]
                    max_lines = int(query_params.get('lines', ['100'])[0])
                    
                    # Try to find the log file in available directories
                    log_file = None
                    log_dirs = ['/var/log', '/tmp', './logs', 'logs']
                    
                    for log_dir in log_dirs:
                        potential_path = os.path.join(log_dir, log_name)
                        if os.path.exists(potential_path):
                            log_file = potential_path
                            break
                    
                    if not log_file:
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        response = {"error": f"Log file {log_name} not found"}
                        self.wfile.write(json.dumps(response).encode())
                        return
                    
                    # Read log content
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        recent_lines = lines[-max_lines:] if len(lines) > max_lines else lines
                        
                        # Parse log entries
                        entries = []
                        for line in recent_lines:
                            # Simple log parsing (can be enhanced)
                            entry = {
                                'message': line.strip(),
                                'timestamp': None,
                                'level': 'info',
                                'source': log_name
                            }
                            
                            # Try to extract timestamp and level
                            if ' ' in line:
                                parts = line.split(' ', 2)
                                if len(parts) >= 2:
                                    try:
                                        # Try to parse timestamp
                                        timestamp_str = f"{parts[0]} {parts[1]}"
                                        datetime.strptime(timestamp_str, '%b %d %H:%M:%S')
                                        entry['timestamp'] = timestamp_str
                                        entry['message'] = parts[2] if len(parts) > 2 else line.strip()
                                    except ValueError:
                                        pass
                                    
                                    # Try to detect log level
                                    if any(level in line.lower() for level in ['error', 'err', 'fail', 'critical']):
                                        entry['level'] = 'error'
                                    elif any(level in line.lower() for level in ['warn', 'warning']):
                                        entry['level'] = 'warning'
                                    elif any(level in line.lower() for level in ['debug']):
                                        entry['level'] = 'debug'
                            
                            entries.append(entry)
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                    self.end_headers()
                    
                    response = {
                        "log_name": log_name,
                        "entries": entries,
                        "total_entries": len(entries),
                        "max_lines": max_lines,
                        "size": f"{os.path.getsize(log_file) / 1024:.1f} KB"
                    }
                    
                    self.wfile.write(json.dumps(response).encode())
                    
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {"error": f"Failed to read log: {str(e)}"}
                    self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/power/status':
            # Power status endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    response = self._get_power_status()
                except Exception as e:
                    response = {"error": f"Failed to get power status: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/refresh':
            # Refresh endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Force refresh of metrics
                    if hasattr(metrics_collector, 'refresh'):
                        metrics_collector.refresh()
                    
                    response = {
                        "message": "System data refreshed successfully",
                        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "status": "success"
                    }
                except Exception as e:
                    response = {"error": f"Failed to refresh: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/commands':
            # System commands endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                # Get available commands or run a specific command
                if 'command' in query_params:
                    command_name = query_params['command'][0]
                    response = {
                        "command": command_name,
                        "result": metrics_collector.run_system_command(command_name)
                    }
                else:
                    response = {
                        "available_commands": metrics_collector.get_available_commands(),
                        "total_commands": len(SYSTEM_COMMANDS),
                        "categories": {
                            "system_info": [cmd for cmd in SYSTEM_COMMANDS.keys() if 'info' in cmd or 'version' in cmd],
                            "hardware": [cmd for cmd in SYSTEM_COMMANDS.keys() if 'memory' in cmd or 'cpu' in cmd or 'disk' in cmd],
                            "network": [cmd for cmd in SYSTEM_COMMANDS.keys() if 'network' in cmd or 'ip' in cmd],
                            "raspberry_pi": [cmd for cmd in SYSTEM_COMMANDS.keys() if 'vcgencmd' in SYSTEM_COMMANDS[cmd]],
                            "performance": [cmd for cmd in SYSTEM_COMMANDS.keys() if 'stats' in cmd or 'load' in cmd],
                            "services": [cmd for cmd in SYSTEM_COMMANDS.keys() if 'service' in cmd or 'status' in cmd]
                        }
                    }
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/status':
            # Quick status overview endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                # Get quick status overview
                try:
                    # Get basic system info
                    cpu_percent = psutil.cpu_percent(interval=0.1)
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')
                    temperature = metrics_collector._get_temperature()
                    
                    # Determine overall system health
                    health_score = 100
                    warnings = []
                    
                    if cpu_percent > 80:
                        health_score -= 20
                        warnings.append("High CPU usage")
                    if memory.percent > 85:
                        health_score -= 20
                        warnings.append("High memory usage")
                    if disk.percent > 85:
                        health_score -= 20
                        warnings.append("High disk usage")
                    if temperature > 70:
                        health_score -= 20
                        warnings.append("High temperature")
                    
                    health_status = "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical"
                    
                    response = {
                        "timestamp": time.time(),
                        "overall_status": health_status,
                        "health_score": health_score,
                        "warnings": warnings,
                        "quick_stats": {
                            "cpu": round(cpu_percent, 1),
                            "memory": round(memory.percent, 1),
                            "disk": round(disk.percent, 1),
                            "temperature": temperature
                        },
                        "uptime": self._get_uptime(),
                        "last_update": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "enhanced_monitoring": True
                    }
                except Exception as e:
                    response = {
                        "timestamp": time.time(),
                        "overall_status": "error",
                        "health_score": 0,
                        "warnings": [f"Failed to get status: {str(e)}"],
                        "quick_stats": {},
                        "uptime": "Unknown",
                        "last_update": time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                
                self.wfile.write(json.dumps(response).encode())
                
        else:
            # 404 for unknown paths
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/api/auth/token':
            # Authentication endpoint
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            
            response = self.handle_auth()
            self.wfile.write(json.dumps(response).encode())
            
        elif path == '/api/services':
            # Service control endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = self.handle_service_action()
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/power':
            # Power management endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = self.handle_power_action()
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/power/shutdown':
            # Shutdown endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Check permissions first
                    permission_check = self._check_shutdown_permissions()
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
                        shutdown_result = self._execute_shutdown()
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
                except Exception as e:
                    response = {"success": False, "message": f"Shutdown failed: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/power/restart':
            # Restart endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Check permissions first
                    permission_check = self._check_restart_permissions()
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
                        restart_result = self._execute_restart()
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
                except Exception as e:
                    response = {"success": False, "message": f"Restart failed: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/api/power/sleep':
            # Sleep endpoint
            if not self.check_auth():
                self.send_response(401)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                response = {"error": "Unauthorized"}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                
                try:
                    # Try to put system to sleep (cross-platform)
                    if platform.system() == 'Windows':
                        os.system('powercfg /hibernate off')  # Disable hibernate first
                        os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')  # Sleep
                    else:
                        os.system('systemctl suspend')
                    
                    response = {
                        "success": True,
                        "message": "Sleep command sent",
                        "action": "sleep",
                        "platform": platform.system()
                    }
                except Exception as e:
                    response = {"success": False, "message": f"Sleep failed: {str(e)}"}
                
                self.wfile.write(json.dumps(response).encode())
                
        elif path == '/health':
            # Health endpoint doesn't support POST
            self.send_response(405)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            response = {"error": "Method not allowed"}
            self.wfile.write(json.dumps(response).encode())
                
        else:
            # 404 for unknown paths
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Set CORS headers for preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')  # Cache preflight for 24 hours
        self.end_headers()
    
    def check_auth(self):
        """Simple authentication check"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        return token in SimplePiMonitorHandler.auth_tokens
    
    def handle_auth(self):
        """Handle authentication and return token"""
        # Get content length from headers
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            # Read POST data
            post_data = self.rfile.read(content_length)
            try:
                # Parse JSON data
                auth_data = json.loads(post_data.decode('utf-8'))
                username = auth_data.get('username', '')
                password = auth_data.get('password', '')
                
                # Check credentials
                if username == 'abhinav' and password == 'kavachi':
                    # Authentication successful
                    token = self.generate_token()
                    SimplePiMonitorHandler.auth_tokens[token] = {
                        'user': username,
                        'expires': time.time() + JWT_EXPIRATION
                    }
                    
                    return {
                        "access_token": token,
                        "token_type": "bearer",
                        "message": "Authentication successful"
                    }
                else:
                    # Authentication failed
                    return {
                        "error": "Invalid username or password",
                        "message": "Authentication failed"
                    }
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {
                    "error": "Invalid JSON data",
                    "message": "Request body must be valid JSON"
                }
        else:
            return {
                "error": "Missing request body",
                "message": "Username and password required"
            }
    
    def generate_token(self):
        """Generate a simple token"""
        timestamp = str(int(time.time()))
        message = f"pi-monitor:{timestamp}"
        signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        return base64.b64encode(f"{message}:{signature}".encode()).decode()
    
    def _get_system_info(self):
        """Get basic system information"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime = f"{uptime_hours}h {uptime_minutes}m"
            
            return {
                "uptime": uptime,
                "platform": platform.platform(),
                "python_version": sys.version.split()[0],
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            return {"error": f"Failed to get system info: {str(e)}"}
    
    def _get_uptime(self):
        """Get system uptime"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            return f"{uptime_hours}h {uptime_minutes}m"
        except Exception as e:
            return {"error": f"Failed to get uptime: {str(e)}"}
    
    def _get_system_stats(self):
        """Get current system statistics (real-time)"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get temperature using the global metrics collector
            temperature = metrics_collector._get_temperature()
            
            # Get network stats
            network = psutil.net_io_counters()
            
            # Get disk I/O
            disk_io = psutil.disk_io_counters()
            
            # Get uptime
            uptime = self._get_uptime()
            
            # Ensure all numeric values are valid numbers, not None
            return {
                "timestamp": time.time(),
                "uptime": uptime,
                "cpu_percent": round(float(cpu_percent) if cpu_percent is not None else 0.0, 1),
                "memory_percent": round(float(memory.percent) if memory.percent is not None else 0.0, 1),
                "disk_percent": round(float(disk.percent) if disk.percent is not None else 0.0, 1),
                "temperature": float(temperature) if temperature is not None else 0.0,
                "network": {
                    "bytes_sent": network.bytes_sent if network else 0,
                    "bytes_recv": network.bytes_recv if network else 0,
                    "packets_sent": network.packets_sent if network else 0,
                    "packets_recv": network.packets_recv if network else 0
                },
                "disk_io": {
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0
                }
            }
        except Exception as e:
            return {"timestamp": time.time(), "error": f"Failed to get system stats: {str(e)}"}
    
    def _get_system_stats_with_history(self, minutes):
        """Get system statistics with history for the last N minutes"""
        try:
            cutoff_time = time.time() - (minutes * 60)
            recent_metrics = [m for m in metrics_collector.metrics_history if m.get('timestamp', 0) > cutoff_time]
            
            if not recent_metrics:
                return {"message": f"No metrics data available for the last {minutes} minutes."}
            
            # Aggregate metrics for the last N minutes
            aggregated_metrics = {
                "timestamp": time.time(), # Current timestamp for the response
                "cpu_percent": round(sum(float(m['cpu_percent']) if m['cpu_percent'] is not None else 0.0 for m in recent_metrics) / len(recent_metrics), 1),
                "memory_percent": round(sum(float(m['memory_percent']) if m['memory_percent'] is not None else 0.0 for m in recent_metrics) / len(recent_metrics), 1),
                "disk_percent": round(sum(float(m['disk_percent']) if m['disk_percent'] is not None else 0.0 for m in recent_metrics) / len(recent_metrics), 1),
                "temperature": round(sum(float(m['temperature']) if m['temperature'] is not None else 0.0 for m in recent_metrics) / len(recent_metrics), 1),
                "network": {
                    "bytes_sent": sum(m['network']['bytes_sent'] if m['network'] and m['network']['bytes_sent'] is not None else 0 for m in recent_metrics),
                    "bytes_recv": sum(m['network']['bytes_recv'] if m['network'] and m['network']['bytes_recv'] is not None else 0 for m in recent_metrics),
                    "packets_sent": sum(m['network']['packets_sent'] if m['network'] and m['network']['packets_sent'] is not None else 0 for m in recent_metrics),
                    "packets_recv": sum(m['network']['packets_recv'] if m['network'] and m['network']['packets_recv'] is not None else 0 for m in recent_metrics)
                },
                "disk_io": {
                    "read_bytes": sum(m['disk_io']['read_bytes'] if m['disk_io'] and m['disk_io']['read_bytes'] is not None else 0 for m in recent_metrics),
                    "write_bytes": sum(m['disk_io']['write_bytes'] if m['disk_io'] and m['disk_io']['write_bytes'] is not None else 0 for m in recent_metrics),
                    "read_count": sum(m['disk_io']['read_count'] if m['disk_io'] and m['disk_io']['read_count'] is not None else 0 for m in recent_metrics),
                    "write_count": sum(m['disk_io']['write_count'] if m['disk_io'] and m['disk_io']['write_count'] is not None else 0 for m in recent_metrics)
                }
            }
            return aggregated_metrics
        except Exception as e:
            return {"timestamp": time.time(), "error": f"Failed to get historical system stats: {str(e)}"}
    
    def _get_enhanced_system_stats(self):
        """Get enhanced system statistics with formatted values and status indicators"""
        try:
            # Get basic stats
            basic_stats = self._get_system_stats()
            
            if "error" in basic_stats:
                return basic_stats
            
            # Get additional system information
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_freq = psutil.cpu_freq()
            
            # Get enhanced metrics from system commands
            enhanced_metrics = {}
            if "enhanced" in basic_stats:
                enhanced_metrics = basic_stats["enhanced"]
            
            # Format values for frontend display
            enhanced_stats = {
                "timestamp": basic_stats["timestamp"],
                "cpu": {
                    "percent": basic_stats["cpu_percent"],
                    "frequency_mhz": round(cpu_freq.current if cpu_freq else 0, 1),
                    "frequency_ghz": round((cpu_freq.current if cpu_freq else 0) / 1000, 2),
                    "status": self._get_cpu_status(basic_stats["cpu_percent"]),
                    "cores": psutil.cpu_count(),
                    "cores_logical": psutil.cpu_count(logical=True),
                    "enhanced": {
                        "temperature": enhanced_metrics.get('cpu_temperature'),
                        "arm_clock": enhanced_metrics.get('arm_clock'),
                        "core_voltage": enhanced_metrics.get('core_voltage')
                    }
                },
                "memory": {
                    "percent": basic_stats["memory_percent"],
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "free_gb": round(memory.free / (1024**3), 2),
                    "status": self._get_memory_status(basic_stats["memory_percent"])
                },
                "disk": {
                    "percent": basic_stats["disk_percent"],
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "status": self._get_disk_status(basic_stats["disk_percent"])
                },
                "temperature": {
                    "celsius": basic_stats["temperature"],
                    "fahrenheit": round((basic_stats["temperature"] * 9/5) + 32, 1),
                    "status": self._get_temperature_status(basic_stats["temperature"]),
                    "enhanced": enhanced_metrics.get('cpu_temperature')
                },
                "network": {
                    "bytes_sent": basic_stats["network"]["bytes_sent"],
                    "bytes_recv": basic_stats["network"]["bytes_recv"],
                    "bytes_sent_mb": round(basic_stats["network"]["bytes_sent"] / (1024**2), 2),
                    "bytes_recv_mb": round(basic_stats["network"]["bytes_recv"] / (1024**2), 2),
                    "packets_sent": basic_stats["network"]["packets_sent"],
                    "packets_recv": basic_stats["network"]["packets_recv"]
                },
                "disk_io": {
                    "read_bytes": basic_stats["disk_io"]["read_bytes"],
                    "write_bytes": basic_stats["disk_io"]["write_bytes"],
                    "read_mb": round(basic_stats["disk_io"]["read_bytes"] / (1024**2), 2),
                    "write_mb": round(basic_stats["disk_io"]["write_bytes"] / (1024**2), 2),
                    "read_count": basic_stats["disk_io"]["read_count"],
                    "write_count": basic_stats["disk_io"]["write_count"]
                },
                "system": {
                    "uptime": self._get_uptime(),
                    "boot_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
                    "platform": platform.platform(),
                    "python_version": sys.version.split()[0]
                },
                "enhanced_monitoring": True,
                "available_commands": len(SYSTEM_COMMANDS)
            }
            
            return enhanced_stats
            
        except Exception as e:
            return {"timestamp": time.time(), "error": f"Failed to get enhanced system stats: {str(e)}"}
    
    def _get_cpu_status(self, cpu_percent):
        """Get CPU status indicator based on usage percentage"""
        if cpu_percent >= 90:
            return {"level": "critical", "color": "red", "message": "Very High"}
        elif cpu_percent >= 80:
            return {"level": "high", "color": "orange", "message": "High"}
        elif cpu_percent >= 60:
            return {"level": "moderate", "color": "yellow", "message": "Moderate"}
        else:
            return {"level": "normal", "color": "green", "message": "Normal"}
    
    def _get_memory_status(self, memory_percent):
        """Get memory status indicator based on usage percentage"""
        if memory_percent >= 95:
            return {"level": "critical", "color": "red", "message": "Critical"}
        elif memory_percent >= 85:
            return {"level": "high", "color": "orange", "message": "High"}
        elif memory_percent >= 70:
            return {"level": "moderate", "color": "yellow", "message": "Moderate"}
        else:
            return {"level": "normal", "color": "green", "message": "Normal"}
    
    def _get_disk_status(self, disk_percent):
        """Get disk status indicator based on usage percentage"""
        if disk_percent >= 95:
            return {"level": "critical", "color": "red", "message": "Critical"}
        elif disk_percent >= 85:
            return {"level": "high", "color": "orange", "message": "High"}
        elif disk_percent >= 70:
            return {"level": "moderate", "color": "yellow", "message": "Moderate"}
        else:
            return {"level": "normal", "color": "green", "message": "Normal"}
    
    def _get_temperature_status(self, temperature):
        """Get temperature status indicator based on temperature value"""
        if temperature >= 80:
            return {"level": "critical", "color": "red", "message": "Very Hot"}
        elif temperature >= 70:
            return {"level": "high", "color": "orange", "message": "Hot"}
        elif temperature >= 60:
            return {"level": "moderate", "color": "yellow", "message": "Warm"}
        else:
            return {"level": "normal", "color": "green", "message": "Normal"}
    
    def _get_power_status(self):
        """Get power status and available actions"""
        try:
            # Get actual uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
            
            # Get system load
            load_avg = os.getloadavg()
            
            # Get power source info (try to detect if running on battery)
            power_source = "AC"
            try:
                # Check if we're on a Pi (no battery)
                with open('/proc/cpuinfo', 'r') as f:
                    if 'Raspberry Pi' in f.read():
                        power_source = "AC (Pi)"
            except:
                pass
            
            return {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "status": "ready",
                "power_state": "on",
                "power_source": power_source,
                "uptime": uptime_formatted,
                "uptime_seconds": int(uptime_seconds),
                "system_load": {
                    "1min": round(load_avg[0], 2),
                    "5min": round(load_avg[1], 2),
                    "15min": round(load_avg[2], 2)
                },
                "available_actions": ["restart", "shutdown", "reboot"],
                "last_boot": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
                "battery": None  # Pi doesn't have battery
            }
        except Exception as e:
            return {
                "error": f"Failed to get power status: {str(e)}",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _get_services_status(self):
        """Get services status"""
        try:
            services = [
                {"name": "pi-monitor", "status": "running", "active": True, "enabled": True, "description": "Pi Monitor Backend"}
            ]
            
            # Try to get actual service statuses
            systemctl_available = False
            try:
                # Check if systemctl is available
                result = subprocess.run(['systemctl', '--version'], capture_output=True, text=True)
                systemctl_available = result.returncode == 0
            except:
                systemctl_available = False
            
            if systemctl_available:
                # systemctl is available, check some common services
                common_services = config.get('monitoring.common_services', ['ssh', 'nginx', 'apache2', 'docker', 'systemd'])
                for service in common_services:
                    try:
                        result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
                        status = "running" if result.returncode == 0 else "stopped"
                        services.append({
                            "name": service,
                            "status": status,
                            "active": result.returncode == 0,
                            "enabled": True,
                            "description": f"{service} service"
                        })
                    except:
                        pass
            else:
                # systemctl not available, try alternative detection methods
                services.extend(self._detect_services_alternative())
            
            # Add system information
            system_info = {
                "systemctl_available": systemctl_available,
                "platform": "Raspberry Pi" if os.path.exists('/proc/cpuinfo') else "Unknown",
                "python_version": sys.version.split()[0],
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return {
                "services": services,
                "system_info": system_info,
                "total_services": len(services)
            }
        except Exception as e:
            return {"error": f"Failed to get services: {str(e)}"}
    
    def _detect_services_alternative(self):
        """Detect services using alternative methods when systemctl is not available"""
        alternative_services = []
        
        # Check for SSH service
        try:
            # Check if SSH port is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 22))
            ssh_status = "running" if result == 0 else "stopped"
            alternative_services.append({
                "name": "ssh",
                "status": ssh_status,
                "active": result == 0,
                "enabled": True,
                "description": "SSH service (port 22)"
            })
            sock.close()
        except:
            alternative_services.append({
                "name": "ssh",
                "status": "unknown",
                "active": False,
                "enabled": False,
                "description": "SSH service (detection failed)"
            })
        
        # Check for Docker
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
            docker_status = "running" if result.returncode == 0 else "stopped"
            alternative_services.append({
                "name": "docker",
                "status": docker_status,
                "active": result.returncode == 0,
                "enabled": True,
                "description": "Docker service (daemon check)"
            })
        except:
            alternative_services.append({
                "name": "docker",
                "status": "unknown",
                "active": False,
                "enabled": False,
                "description": "Docker service (not installed)"
            })
        
        # Check for Nginx
        try:
            # Check if nginx port is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 80))
            nginx_status = "running" if result == 0 else "stopped"
            alternative_services.append({
                "name": "nginx",
                "status": nginx_status,
                "active": result == 0,
                "enabled": True,
                "description": "Nginx service (port 80)"
            })
            sock.close()
        except:
            alternative_services.append({
                "name": "nginx",
                "status": "unknown",
                "active": False,
                "enabled": False,
                "description": "Nginx service (not running)"
            })
        
        # Check for Python processes
        try:
            result = subprocess.run(['pgrep', '-f', 'python'], capture_output=True, text=True)
            if result.returncode == 0:
                alternative_services.append({
                    "name": "python",
                    "status": "running",
                    "active": True,
                    "enabled": True,
                    "description": "Python processes active"
                })
        except:
            # On Windows, try tasklist instead of pgrep
            try:
                result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq python.exe'], capture_output=True, text=True, shell=True)
                if 'python.exe' in result.stdout:
                    alternative_services.append({
                        "name": "python",
                        "status": "running",
                        "active": True,
                        "enabled": True,
                        "description": "Python processes active (Windows)"
                    })
            except:
                pass
        
        # Add Windows-specific services
        if platform.system() == 'Windows':
            try:
                # Check for Windows services
                result = subprocess.run(['sc', 'query', 'wuauserv'], capture_output=True, text=True, shell=True)
                if 'RUNNING' in result.stdout:
                    alternative_services.append({
                        "name": "wuauserv",
                        "status": "running",
                        "active": True,
                        "enabled": True,
                        "description": "Windows Update service"
                    })
                else:
                    alternative_services.append({
                        "name": "wuauserv",
                        "status": "stopped",
                        "active": False,
                        "enabled": True,
                        "description": "Windows Update service"
                    })
            except:
                pass
        
        return alternative_services
    
    def handle_service_action(self):
        """Handle service control actions"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                service_name = data.get('service_name', '')
                action = data.get('action', '')
                
                if action == 'status':
                    # Just return status
                    return {"success": True, "message": f"Service {service_name} status checked"}
                elif action in ['start', 'stop', 'restart']:
                    # Try to control service
                    try:
                        # First try systemctl
                        result = subprocess.run(['systemctl', action, service_name], capture_output=True, text=True)
                        if result.returncode == 0:
                            return {"success": True, "message": f"Service {service_name} {action} successful"}
                        else:
                            # Try alternative methods if systemctl fails
                            return self._handle_service_action_alternative(service_name, action)
                    except FileNotFoundError:
                        # systemctl not available, try alternative methods
                        return self._handle_service_action_alternative(service_name, action)
                    except Exception as e:
                        return {"success": False, "message": f"Service control failed: {str(e)}"}
                else:
                    return {"success": False, "message": f"Unknown action: {action}"}
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            return {"success": False, "message": f"Service action failed: {str(e)}"}
    
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
                    # Stop then start
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
                if service_name == 'ssh':
                    if action == 'start':
                        try:
                            result = subprocess.run(['service', 'ssh', 'start'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "SSH service started using service command"}
                            else:
                                return {"success": False, "message": f"SSH start failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "SSH service control not available (systemctl and service commands not found)"}
                    elif action == 'stop':
                        try:
                            result = subprocess.run(['service', 'ssh', 'stop'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "SSH service stopped using service command"}
                            else:
                                return {"success": False, "message": f"SSH stop failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "SSH service control not available (systemctl and service commands not found)"}
                    elif action == 'restart':
                        try:
                            result = subprocess.run(['service', 'ssh', 'restart'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "SSH service restarted using service command"}
                            else:
                                return {"success": False, "message": f"SSH restart failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "SSH service control not available (systemctl and service commands not found)"}
                
                elif service_name == 'nginx':
                    if action == 'start':
                        try:
                            result = subprocess.run(['service', 'nginx', 'start'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "Nginx service started using service command"}
                            else:
                                return {"success": False, "message": f"Nginx start failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "Nginx service control not available (systemctl and service commands not found)"}
                    elif action == 'stop':
                        try:
                            result = subprocess.run(['service', 'nginx', 'stop'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "Nginx service stopped using service command"}
                            else:
                                return {"success": False, "message": f"Nginx stop failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "Nginx service control not available (systemctl and service commands not found)"}
                    elif action == 'restart':
                        try:
                            result = subprocess.run(['service', 'nginx', 'restart'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "Nginx service restarted using service command"}
                            else:
                                return {"success": False, "message": f"Nginx restart failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "Nginx service control not available (systemctl and service commands not found)"}
                
                elif service_name == 'docker':
                    if action == 'start':
                        try:
                            result = subprocess.run(['service', 'docker', 'start'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "Docker service started using service command"}
                            else:
                                return {"success": False, "message": f"Docker start failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "Docker service control not available (systemctl and service commands not found)"}
                    elif action == 'stop':
                        try:
                            result = subprocess.run(['service', 'docker', 'stop'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "Docker service stopped using service command"}
                            else:
                                return {"success": False, "message": f"Docker stop failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "Docker service control not available (systemctl and service commands not found)"}
                    elif action == 'restart':
                        try:
                            result = subprocess.run(['service', 'docker', 'restart'], capture_output=True, text=True)
                            if result.returncode == 0:
                                return {"success": True, "message": "Docker service restarted using service command"}
                            else:
                                return {"success": False, "message": f"Docker restart failed: {result.stderr}"}
                        except:
                            return {"success": False, "message": "Docker service control not available (systemctl and service commands not found)"}
            
            # Default fallback for unknown services
            return {"success": False, "message": f"Service {service_name} control not available (systemctl and service commands not found)"}
            
        except Exception as e:
            return {"success": False, "message": f"Alternative service control failed: {str(e)}"}
    
    def handle_power_action(self):
        """Handle power management actions"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                
                action = data.get('action', '')
                delay = data.get('delay', 0)
                
                # Get current system info
                uptime_seconds = time.time() - psutil.boot_time()
                uptime_hours = int(uptime_seconds // 3600)
                uptime_minutes = int((uptime_seconds % 3600) // 60)
                uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
                
                if action == 'shutdown':
                    # Check permissions first
                    permission_check = self._check_shutdown_permissions()
                    if not permission_check['can_shutdown']:
                        return {
                            "success": False, 
                            "message": f"Permission denied: {permission_check['reason']}",
                            "action": "shutdown",
                            "permission_details": permission_check,
                            "suggestions": permission_check['suggestions'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    
                    # Execute shutdown with proper command
                    shutdown_result = self._execute_shutdown()
                    if shutdown_result['success']:
                        return {
                            "success": True, 
                            "message": shutdown_result['message'],
                            "action": "shutdown",
                            "command_used": shutdown_result['command_used'],
                            "permission_method": permission_check['method'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    else:
                        return {
                            "success": False, 
                            "message": f"Shutdown failed: {shutdown_result['error']}",
                            "action": "shutdown",
                            "permission_details": permission_check,
                            "suggestions": permission_check['suggestions'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                        
                elif action == 'restart':
                    # Check permissions first
                    permission_check = self._check_restart_permissions()
                    if not permission_check['can_restart']:
                        return {
                            "success": False, 
                            "message": f"Permission denied: {permission_check['reason']}",
                            "action": "restart",
                            "permission_details": permission_check,
                            "suggestions": permission_check['suggestions'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    
                    # Execute restart with proper command
                    restart_result = self._execute_restart()
                    if restart_result['success']:
                        return {
                            "success": True, 
                            "message": restart_result['message'],
                            "action": "restart",
                            "command_used": restart_result['command_used'],
                            "permission_method": permission_check['method'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    else:
                        return {
                            "success": False, 
                            "message": f"Restart failed: {restart_result['error']}",
                            "action": "restart",
                            "permission_details": permission_check,
                            "suggestions": permission_check['suggestions'],
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
                    return {
                        "success": False, 
                        "message": f"Unknown power action: {action}",
                        "available_actions": ["restart", "shutdown", "reboot", "status"]
                    }
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            return {"success": False, "message": f"Power action failed: {str(e)}"}
    
    def _get_detailed_system_info(self):
        """Get detailed system information including hardware and software"""
        try:
            system_info = self._get_system_info()
            power_status = self._get_power_status()
            services_status = self._get_services_status()
            
            # Get CPU model and frequency
            cpu_info = psutil.cpu_freq()
            cpu_model = platform.processor()
            
            # Get memory details
            memory_info = psutil.virtual_memory()
            swap_info = psutil.swap_memory()
            
            # Get disk details
            disk_partitions = psutil.disk_partitions()
            disk_usage = psutil.disk_usage('/')
            
            # Get network interfaces
            network_interfaces = psutil.net_if_addrs()
            
            # Get system logs (example: last 100 lines of /var/log/syslog)
            syslog_path = '/var/log/syslog' if os.path.exists('/var/log/syslog') else '/var/log/messages'
            system_logs = []
            try:
                with open(syslog_path, 'r') as f:
                    lines = f.readlines()
                    system_logs = [{"timestamp": datetime.fromtimestamp(os.path.getmtime(syslog_path)).strftime('%Y-%m-%d %H:%M:%S'), "message": line.strip()} for line in lines[-100:]]
            except:
                system_logs = [{"timestamp": "N/A", "message": "Could not read system logs."}]
            
            # Get system uptime history
            uptime_history = metrics_collector.get_metrics_history(60) # Get last 60 minutes
            
            return {
                "system_info": system_info,
                "power_status": power_status,
                "services_status": services_status,
                "cpu_info": {
                    "current_freq": round(cpu_info.current, 2) if cpu_info and cpu_info.current else 0,
                    "min_freq": round(cpu_info.min, 2) if cpu_info and cpu_info.min else 0,
                    "max_freq": round(cpu_info.max, 2) if cpu_info and cpu_info.max else 0,
                    "model": cpu_model or "Unknown"
                },
                "memory_info": {
                    "total": round(memory_info.total / (1024**3), 2), # GB
                    "available": round(memory_info.available / (1024**3), 2), # GB
                    "used": round(memory_info.used / (1024**3), 2), # GB
                    "percent": round(memory_info.percent, 1)
                },
                "swap_info": {
                    "total": round(swap_info.total / (1024**3), 2), # GB
                    "used": round(swap_info.used / (1024**3), 2), # GB
                    "free": round(swap_info.free / (1024**3), 2), # GB
                    "percent": round(swap_info.percent, 1)
                },
                "disk_info": {
                    "total": round(disk_usage.total / (1024**3), 2), # GB
                    "used": round(disk_usage.used / (1024**3), 2), # GB
                    "free": round(disk_usage.free / (1024**3), 2), # GB
                    "percent": round(disk_usage.percent, 1)
                },
                "network_interfaces": {
                    iface: {
                        "addrs": [{"addr": addr.address, "netmask": addr.netmask, "broadcast": addr.broadcast} for addr in addrs]
                    } for iface, addrs in network_interfaces.items()
                },
                "system_logs": system_logs,
                "uptime_history": uptime_history
            }
        except Exception as e:
            return {"error": f"Failed to get detailed system info: {str(e)}"}
    
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
                
                # Check if running as root
                if os.geteuid() == 0:
                    return {
                        'can_shutdown': True,
                        'method': 'root',
                        'reason': 'Running as root user',
                        'suggestions': []
                    }
                
                # Check if user can use sudo without password for shutdown commands
                sudo_check = self._check_sudo_permissions()
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
                shutdown_available = self._check_command_availability(['shutdown', 'poweroff', 'halt'])
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
    
    def _check_restart_permissions(self):
        """Check if current user can execute restart commands"""
        try:
            if platform.system() == 'Windows':
                # Same as shutdown for Windows
                return self._check_shutdown_permissions()
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
                sudo_check = self._check_sudo_permissions()
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
                restart_available = self._check_command_availability(['reboot', 'shutdown', 'systemctl'])
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
    
    def _check_sudo_permissions(self):
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
    
    def _check_command_availability(self, commands):
        """Check if specified commands are available in PATH"""
        available_commands = []
        for cmd in commands:
            try:
                result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    available_commands.append(cmd)
            except:
                pass
        return available_commands
    
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
    
    def _execute_restart(self):
        """Execute restart command with proper permissions and fallbacks"""
        try:
            if platform.system() == 'Windows':
                # Windows restart
                restart_cmd = 'shutdown /r /t 5'
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
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(port=None):
    """Run the enhanced Pi Monitor HTTP server"""
    if port is None:
        port = config.get_port('backend')
    
    # Start metrics collection
    print("Starting metrics collection...")
    metrics_collector.start_collection()
    
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimplePiMonitorHandler)
    
    print("=" * 60)
    print("🚀 Pi Monitor Backend Server Starting...")
    print("=" * 60)
    print(f"📍 Port: {port}")
    print(f"⚙️  Config: {config.config_file}")
    print(f"📊 Metrics Collection: {'Active' if metrics_collector.is_collecting else 'Inactive'}")
    print(f"🔄 Collection Interval: {metrics_collector.collection_interval}s")
    print(f"📈 Max History: {metrics_collector.max_history} data points")
    print()
    print("🌐 Available Endpoints:")
    endpoints = config.get_backend_endpoints()
    for name, path in endpoints.items():
        print(f"  📍 {name.upper()}: {path}")
    
    # Add new endpoints
    print(f"  📊 METRICS: /api/metrics")
    print(f"  ℹ️  SYSTEM_INFO: /api/system/info")
    print(f"  🖥️  COMMANDS: /api/commands")
    print()
    print("🔧 Enhanced System Monitoring:")
    print(f"  📈 Total Commands: {len(SYSTEM_COMMANDS)}")
    print(f"  🖥️  System Info: {len([cmd for cmd in SYSTEM_COMMANDS.keys() if 'info' in cmd or 'version' in cmd])} commands")
    print(f"  🔧 Hardware: {len([cmd for cmd in SYSTEM_COMMANDS.keys() if 'memory' in cmd or 'cpu' in cmd or 'disk' in cmd])} commands")
    print(f"  🌐 Network: {len([cmd for cmd in SYSTEM_COMMANDS.keys() if 'network' in cmd or 'ip' in cmd])} commands")
    print(f"  🍓 Raspberry Pi: {len([cmd for cmd in SYSTEM_COMMANDS.keys() if 'vcgencmd' in SYSTEM_COMMANDS[cmd]])} commands")
    print(f"  📊 Performance: {len([cmd for cmd in SYSTEM_COMMANDS.keys() if 'stats' in cmd or 'load' in cmd])} commands")
    print(f"  🚀 Services: {len([cmd for cmd in SYSTEM_COMMANDS.keys() if 'service' in cmd or 'status' in cmd])} commands")
    print()
    print(f"🚀 Server running at http://0.0.0.0:{port}")
    print(f"🔗 Health check: http://0.0.0.0:{port}/health")
    print("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        print("🛑 Stopping metrics collection...")
        metrics_collector.stop_collection()
        print("🛑 Shutting down HTTP server...")
        httpd.shutdown()
        print("✅ Server shutdown complete")

if __name__ == '__main__':
    run_server()
