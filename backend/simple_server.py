#!/usr/bin/env python3
"""
Pi Monitor - Enhanced HTTP Server
RPi-Monitor inspired monitoring system with real-time data collection
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

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# Simple JWT-like token (for demo purposes)
JWT_SECRET = "pi-monitor-secret-key-2024"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours

# Global data storage for real-time metrics
class MetricsCollector:
    def __init__(self):
        self.metrics_history = []
        self.max_history = 1000  # Keep last 1000 data points
        self.collection_interval = 5.0  # 5 seconds
        self.is_collecting = False
        self.collection_thread = None
        
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
        """Gather current system metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get temperature
            temperature = self._get_temperature()
            
            # Get network stats
            network = psutil.net_io_counters()
            
            # Get disk I/O
            disk_io = psutil.disk_io_counters()
            
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
                }
            }
        except Exception as e:
            return {"timestamp": time.time(), "error": str(e)}
    
    def _get_temperature(self):
        """Get system temperature using multiple methods"""
        try:
            # Try Raspberry Pi specific path
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = f.read().strip()
                    return round(float(temp_raw) / 1000.0, 1)
            
            # Try other thermal zones
            for i in range(10):
                thermal_path = f'/sys/class/thermal/thermal_zone{i}/temp'
                if os.path.exists(thermal_path):
                    with open(thermal_path, 'r') as f:
                        temp_raw = f.read().strip()
                        return round(float(temp_raw) / 1000.0, 1)
            
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
                                    return round(float(value), 1)
            except:
                pass
                
        except Exception:
            pass
        
        return 0.0
    
    def get_metrics_history(self, minutes=60):
        """Get metrics history for the last N minutes"""
        cutoff_time = time.time() - (minutes * 60)
        return [m for m in self.metrics_history if m.get('timestamp', 0) > cutoff_time]
    
    def get_latest_metrics(self):
        """Get the most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None

# Global metrics collector instance
metrics_collector = MetricsCollector()

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
                "system_info": self._get_system_info()
            }
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
                }
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
                else:
                    response = self._get_system_stats()
                    
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
            
            # Get temperature
            temperature = self._get_temperature()
            
            # Get network stats
            network = psutil.net_io_counters()
            
            # Get disk I/O
            disk_io = psutil.disk_io_counters()
            
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
                "cpu_percent": round(sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics), 1),
                "memory_percent": round(sum(m['memory_percent'] for m in recent_metrics) / len(recent_metrics), 1),
                "disk_percent": round(sum(m['disk_percent'] for m in recent_metrics) / len(recent_metrics), 1),
                "temperature": round(sum(m['temperature'] for m in recent_metrics) / len(recent_metrics), 1),
                "network": {
                    "bytes_sent": sum(m['network']['bytes_sent'] for m in recent_metrics),
                    "bytes_recv": sum(m['network']['bytes_recv'] for m in recent_metrics),
                    "packets_sent": sum(m['network']['packets_sent'] for m in recent_metrics),
                    "packets_recv": sum(m['network']['packets_recv'] for m in recent_metrics)
                },
                "disk_io": {
                    "read_bytes": sum(m['disk_io']['read_bytes'] for m in recent_metrics),
                    "write_bytes": sum(m['disk_io']['write_bytes'] for m in recent_metrics),
                    "read_count": sum(m['disk_io']['read_count'] for m in recent_metrics),
                    "write_count": sum(m['disk_io']['write_count'] for m in recent_metrics)
                }
            }
            return aggregated_metrics
        except Exception as e:
            return {"timestamp": time.time(), "error": f"Failed to get historical system stats: {str(e)}"}
    
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
                {"name": "pi-monitor", "status": "running", "active": True, "enabled": True, "description": "Pi Monitor Backend"},
                {"name": "system", "status": "ok", "active": True, "enabled": True, "description": "System Services"}
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
                # systemctl not available, provide alternative service info
                services.extend([
                    {"name": "ssh", "status": "unknown", "active": False, "enabled": False, "description": "SSH service (systemctl not available)"},
                    {"name": "docker", "status": "unknown", "active": False, "enabled": False, "description": "Docker service (systemctl not available)"},
                    {"name": "nginx", "status": "unknown", "active": False, "enabled": False, "description": "Nginx service (systemctl not available)"}
                ])
            
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
                        result = subprocess.run(['systemctl', action, service_name], capture_output=True, text=True)
                        if result.returncode == 0:
                            return {"success": True, "message": f"Service {service_name} {action} successful"}
                        else:
                            return {"success": False, "message": f"Service {service_name} {action} failed: {result.stderr}"}
                    except Exception as e:
                        return {"success": False, "message": f"Service control failed: {str(e)}"}
                else:
                    return {"success": False, "message": f"Unknown action: {action}"}
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            return {"success": False, "message": f"Service action failed: {str(e)}"}
    
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
                    # Schedule shutdown
                    if delay > 0:
                        threading.Timer(delay, lambda: os.system('shutdown -h now')).start()
                        return {
                            "success": True, 
                            "message": f"Shutdown scheduled in {delay} seconds",
                            "action": "shutdown",
                            "delay_seconds": delay,
                            "scheduled_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + delay)),
                            "current_uptime": uptime_formatted
                        }
                    else:
                        return {
                            "success": True, 
                            "message": "Shutdown command received (use delay for safety)",
                            "action": "shutdown",
                            "warning": "No delay specified - command not executed",
                            "current_uptime": uptime_formatted,
                            "recommendation": "Specify delay > 0 to actually execute"
                        }
                elif action == 'restart':
                    # Schedule restart
                    if delay > 0:
                        threading.Timer(delay, lambda: os.system('reboot')).start()
                        return {
                            "success": True, 
                            "message": f"Restart scheduled in {delay} seconds",
                            "action": "restart",
                            "delay_seconds": delay,
                            "scheduled_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + delay)),
                            "current_uptime": uptime_formatted
                        }
                    else:
                        return {
                            "success": True, 
                            "message": "Restart command received (use delay for safety)",
                            "action": "restart",
                            "warning": "No delay specified - command not executed",
                            "current_uptime": uptime_formatted,
                            "recommendation": "Specify delay > 0 to actually execute"
                        }
                elif action == 'status':
                    # Return current power status
                    return {
                        "success": True,
                        "action": "status",
                        "power_state": "on",
                        "current_uptime": uptime_formatted,
                        "uptime_seconds": int(uptime_seconds),
                        "last_boot": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
                        "available_actions": ["restart", "shutdown", "reboot"]
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
    
    server_address = ('', port)
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
