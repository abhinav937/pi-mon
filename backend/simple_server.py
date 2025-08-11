#!/usr/bin/env python3
"""
Pi Monitor - Simple HTTP Server
Complete replacement for FastAPI with all necessary endpoints
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

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

# Simple JWT-like token (for demo purposes)
JWT_SECRET = "pi-monitor-secret-key-2024"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours

class SimplePiMonitorHandler(BaseHTTPRequestHandler):
    # Class variable to persist tokens between requests
    auth_tokens = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
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
                "endpoints": config.get_backend_endpoints()
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
                response = self.get_system_stats()
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
                response = self.get_services_status()
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
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
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
        # Simple demo authentication - always succeeds
        token = self.generate_token()
        SimplePiMonitorHandler.auth_tokens[token] = {
            'user': 'pi-monitor',
            'expires': time.time() + JWT_EXPIRATION
        }
        
        return {
            "access_token": token,
            "token_type": "bearer"
        }
    
    def generate_token(self):
        """Generate a simple token"""
        timestamp = str(int(time.time()))
        message = f"pi-monitor:{timestamp}"
        signature = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        return base64.b64encode(f"{message}:{signature}".encode()).decode()
    
    def get_system_stats(self):
        """Get system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get temperature (try different methods)
            temperature = 0.0
            try:
                # Try to read from /sys/class/thermal
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = f.read().strip()
                    temperature = float(temp_raw) / 1000.0
            except:
                pass
            
            # Get uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime = f"{uptime_hours}h {uptime_minutes}m"
            
            # Get network stats
            network = psutil.net_io_counters()
            
            return {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "disk_percent": round(disk.percent, 1),
                "temperature": round(temperature, 1),
                "uptime": uptime,
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
        except Exception as e:
            return {
                "error": f"Failed to get system stats: {str(e)}",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def get_power_status(self):
        """Get power status and available actions"""
        try:
            return {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "status": "ready",
                "actions": ["restart", "shutdown", "reboot"],
                "current_power": "on",
                "battery": None,  # Pi doesn't have battery
                "uptime": time.time() - psutil.boot_time()
            }
        except Exception as e:
            return {
                "error": f"Failed to get power status: {str(e)}",
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def get_services_status(self):
        """Get services status"""
        try:
            services = [
                {"name": "pi-monitor", "status": "running", "active": True, "enabled": True, "description": "Pi Monitor Backend"},
                {"name": "system", "status": "ok", "active": True, "enabled": True, "description": "System Services"}
            ]
            
            # Try to get actual service statuses
            try:
                # Check if systemctl is available
                result = subprocess.run(['systemctl', 'is-active', '--quiet'], capture_output=True, text=True)
                if result.returncode == 0:
                    # systemctl is available, check some common services
                    common_services = config.get('monitoring.common_services', ['ssh', 'nginx', 'apache2'])
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
            except:
                pass
            
            return {"services": services}
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
                
                if action == 'shutdown':
                    # Schedule shutdown
                    if delay > 0:
                        threading.Timer(delay, lambda: os.system('shutdown -h now')).start()
                        return {"success": True, "message": f"Shutdown scheduled in {delay} seconds"}
                    else:
                        return {"success": True, "message": "Shutdown command received (use delay for safety)"}
                elif action == 'restart':
                    # Schedule restart
                    if delay > 0:
                        threading.Timer(delay, lambda: os.system('reboot')).start()
                        return {"success": True, "message": f"Restart scheduled in {delay} seconds"}
                    else:
                        return {"success": True, "message": "Restart command received (use delay for safety)"}
                else:
                    return {"success": False, "message": f"Unknown power action: {action}"}
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            return {"success": False, "message": f"Power action failed: {str(e)}"}
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server(port=None):
    """Run the simple HTTP server"""
    if port is None:
        port = config.get_port('backend')
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimplePiMonitorHandler)
    print(f"Starting simple Pi Monitor server on port {port}")
    print(f"Configuration loaded from: {config.config_file}")
    print(f"Available endpoints:")
    endpoints = config.get_backend_endpoints()
    for name, path in endpoints.items():
        print(f"  {name.upper()}: {path}")
    print(f"Server running at http://0.0.0.0:{port}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == '__main__':
    run_server()
