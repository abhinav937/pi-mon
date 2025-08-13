#!/usr/bin/env python3
"""
Pi Monitor - HTTP Server
Main server class that handles HTTP requests and routing
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from config import config
from auth import AuthManager
from metrics import MetricsCollector
from database import MetricsDatabase
from system_monitor import SystemMonitor
from service_manager import ServiceManager
from power_manager import PowerManager
from log_manager import LogManager
from utils import rate_limit, monitor_performance

class PiMonitorServer:
    """Main Pi Monitor HTTP server"""
    
    def __init__(self, port=None):
        self.port = port or config.get_port('backend')
        self.metrics_collector = MetricsCollector()
        self.database = MetricsDatabase()
        self.system_monitor = SystemMonitor()
        self.service_manager = ServiceManager()
        self.power_manager = PowerManager()
        self.log_manager = LogManager()
        self.auth_manager = AuthManager()
        
        # Start background services
        self._start_background_services()
    
    def _start_background_services(self):
        """Start background services like metrics collection"""
        self.metrics_collector.start_collection()
        
        # Start database cleanup task
        def cleanup_database():
            while True:
                try:
                    time.sleep(24 * 60 * 60)  # 24 hours
                    deleted_count = self.database.cleanup_old_data(days_to_keep=30)
                    if deleted_count > 0:
                        print(f"🧹 Cleaned up {deleted_count} old metrics records")
                except Exception as e:
                    print(f"❌ Database cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_database, daemon=True)
        cleanup_thread.start()
    
    def run(self):
        """Run the HTTP server"""
        server_address = ('0.0.0.0', self.port)
        httpd = HTTPServer(server_address, PiMonitorHandler)
        
        # Set server instance in handler for access to services
        PiMonitorHandler.server_instance = self
        
        self._print_startup_info()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self._shutdown()
    
    def _print_startup_info(self):
        """Print server startup information"""
        print("=" * 60)
        print("🚀 Pi Monitor Backend Server Starting...")
        print("=" * 60)
        print(f"📍 Port: {self.port}")
        print(f"⚙️  Config: {config.config_file}")
        print(f"📊 Metrics Collection: {'Active' if self.metrics_collector.is_collecting else 'Inactive'}")
        print(f"🔄 Collection Interval: {self.metrics_collector.collection_interval}s")
        print(f"💾 Database: {self.database.db_path}")
        print()
        print("🌐 Available Endpoints:")
        endpoints = config.get_backend_endpoints()
        for name, path in endpoints.items():
            print(f"  📍 {name.upper()}: {path}")
        print()
        print(f"🚀 Server running at http://0.0.0.0:{self.port}")
        print(f"🔗 Health check: http://0.0.0.0:{self.port}/health")
        print("=" * 60)
    
    def _shutdown(self):
        """Shutdown the server and cleanup"""
        print("\n🛑 Shutting down server...")
        print("🛑 Stopping metrics collection...")
        self.metrics_collector.stop_collection()
        print("🛑 Shutting down HTTP server...")
        print("✅ Server shutdown complete")


class PiMonitorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Pi Monitor"""
    
    server_instance = None  # Will be set by server
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_start_time = time.time()
    
    def log_message(self, format_str, *args):
        """Custom logging with performance metrics"""
        try:
            execution_time = time.time() - getattr(self, 'request_start_time', time.time())
            print(f"{self.client_address[0]} - {format_str % args} - {execution_time:.3f}s")
        except Exception:
            print(f"{self.client_address[0]} - {format_str % args}")
    
    def setup(self):
        """Setup method called before handling each request"""
        super().setup()
        self.request_start_time = time.time()
    
    @rate_limit(max_requests=100, window=60)
    def do_GET(self):
        """Handle GET requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # Route to appropriate handler
        if path == '/':
            self._handle_root_endpoint()
        elif path == '/health':
            self._handle_health_check()
        elif path == '/api/system':
            self._handle_system_stats(query_params)
        elif path == '/api/system/enhanced':
            self._handle_enhanced_system_stats()
        elif path == '/api/system/info':
            self._handle_system_info_detail()
        elif path == '/api/services':
            self._handle_services_list()
        elif path == '/api/network':
            self._handle_network_info()
        elif path == '/api/network/stats':
            self._handle_network_stats()
        elif path == '/api/logs':
            self._handle_logs_list(query_params)
        elif path.startswith('/api/logs/') and '?' in self.path:
            self._handle_log_read(query_params)
        elif path.startswith('/api/logs/') and '/download' in path:
            self._handle_log_download()
        elif path.startswith('/api/logs/') and path.endswith('/clear'):
            self._handle_log_clear()
        elif path.startswith('/api/metrics/history'):
            self._handle_metrics_history(query_params)
        elif path == '/api/metrics/database':
            self._handle_database_stats()
        elif path == '/api/refresh':
            self._handle_refresh()
        elif path == '/api/power':
            self._handle_power_status_get()
        elif path.startswith('/api/service/'):
            self._handle_service_endpoints(path)
        else:
            self._handle_404()
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Route to appropriate handler
        if path == '/api/auth/token':
            self._handle_auth()
        elif path == '/api/services':
            self._handle_services_post()
        elif path == '/api/power':
            self._handle_power_action()
        elif path == '/api/power/shutdown':
            self._handle_power_shutdown()
        elif path == '/api/power/restart':
            self._handle_power_restart()
        elif path == '/api/power/sleep':
            self._handle_power_sleep()
        elif path.startswith('/api/service/'):
            self._handle_service_post_endpoints(path)
        else:
            self._handle_404()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    # Handler methods for different endpoints
    def _handle_root_endpoint(self):
        """Handle root endpoint"""
        self.send_response(200)
        self._set_common_headers()
        
        response = {
            "message": "Pi Monitor Backend is running!",
            "status": "ok",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "version": config.get('project.version', '1.0.0'),
            "endpoints": config.get_backend_endpoints(),
            "features": config.get('backend.features', {}),
            "system_info": self.server_instance.system_monitor.get_system_info(),
            "enhanced_monitoring": True
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_health_check(self):
        """Handle health check"""
        self.send_response(200)
        self._set_common_headers()
        
        response = {
            "status": "healthy",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "version": config.get('project.version', '1.0.0'),
            "uptime": self.server_instance.system_monitor.get_uptime(),
            "enhanced_monitoring": True
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_system_stats(self, query_params):
        """Handle system stats"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        if 'history' in query_params:
            minutes = int(query_params.get('history', ['60'])[0])
            response = self.server_instance.system_monitor.get_system_stats_with_history(minutes)
        else:
            response = self.server_instance.system_monitor.get_system_stats()
            
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_enhanced_system_stats(self):
        """Handle enhanced system stats"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.system_monitor.get_enhanced_system_stats()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_system_info_detail(self):
        """Handle system info detail"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.system_monitor.get_system_info_detail()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_services_list(self):
        """Handle services list"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.service_manager.get_services_list()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_network_info(self):
        """Handle network info"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.system_monitor.get_network_info()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_network_stats(self):
        """Handle network stats"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.system_monitor.get_network_stats()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_logs_list(self, query_params):
        """Handle logs list"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.log_manager.get_logs_list()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_log_read(self, query_params):
        """Handle log read"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        log_name = self.path.split('/')[-1]
        lines = int(query_params.get('lines', ['100'])[0])
        response = self.server_instance.log_manager.read_log(log_name, lines)
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_log_download(self):
        """Handle log download"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        try:
            log_name = self.path.split('/')[-2]
            self.server_instance.log_manager.download_log(self, log_name)
        except Exception as e:
            self._send_internal_error(f"Failed to download log: {str(e)}")
    
    def _handle_log_clear(self):
        """Handle log clear"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        log_name = self.path.split('/')[-2]
        response = self.server_instance.log_manager.clear_log(log_name)
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_metrics_history(self, query_params):
        """Handle metrics history"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        minutes = int(query_params.get('minutes', ['60'])[0])
        include_date = query_params.get('include_date', ['true' if minutes > 60 else 'false'])[0].lower() == 'true'
        
        response = self.server_instance.metrics_collector.get_metrics_history_formatted(minutes, include_date)
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_database_stats(self):
        """Handle database stats"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.database.get_database_stats()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_refresh(self):
        """Handle refresh"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.metrics_collector.refresh()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_status_get(self):
        """Handle power status GET"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.power_manager.get_power_status()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_service_endpoints(self, path):
        """Handle service-related GET endpoints"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        if 'restart' in path:
            response = self.server_instance.service_manager.get_restart_info()
        elif 'manage' in path:
            response = self.server_instance.service_manager.get_manage_info()
        elif 'info' in path:
            response = self.server_instance.service_manager.get_service_info()
        else:
            response = {"error": "Unknown service endpoint"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_auth(self):
        """Handle authentication"""
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.auth_manager.handle_auth(self)
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_services_post(self):
        """Handle services POST"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.service_manager.handle_service_action(self)
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_action(self):
        """Handle power action"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.power_manager.handle_power_action(self)
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_shutdown(self):
        """Handle power shutdown"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.power_manager.shutdown()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_restart(self):
        """Handle power restart"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.power_manager.restart()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_sleep(self):
        """Handle power sleep"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.power_manager.sleep()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_service_post_endpoints(self, path):
        """Handle service-related POST endpoints"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        if 'restart' in path:
            response = self.server_instance.service_manager.restart_service()
        elif 'manage' in path:
            response = self.server_instance.service_manager.manage_service(self)
        elif 'info' in path:
            response = self.server_instance.service_manager.get_service_info()
        else:
            response = {"error": "Unknown service endpoint"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_404(self):
        """Handle 404 errors"""
        self.send_response(404)
        self._set_common_headers()
        response = {"error": "Not found"}
        self.wfile.write(json.dumps(response).encode())
    
    def _check_auth(self):
        """Check authentication"""
        return self.server_instance.auth_manager.check_auth(self)
    
    def _set_common_headers(self):
        """Set common response headers"""
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
    
    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def _send_unauthorized(self):
        """Send unauthorized response"""
        self.send_response(401)
        self._set_common_headers()
        response = {"error": "Unauthorized"}
        self.wfile.write(json.dumps(response).encode())
    
    def _send_internal_error(self, message):
        """Send internal error response"""
        self.send_response(500)
        self._set_common_headers()
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode())
