#!/usr/bin/env python3
"""
Pi Monitor - HTTP Server
Main server class that handles HTTP requests and routing
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import os
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

# WebAuthn imports
try:
    from webauthn_manager import WebAuthnManager
    WEBAUTHN_ENABLED = True
except ImportError:
    WEBAUTHN_ENABLED = False
    WebAuthnManager = None

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class PiMonitorServer:
    """Main Pi Monitor HTTP server"""
    
    def __init__(self, port=None):
        self.port = port or config.get_port('backend')
        self.start_time = time.time()
        self.metrics_collector = MetricsCollector()
        self.database = MetricsDatabase()
        self.system_monitor = SystemMonitor()
        self.service_manager = ServiceManager()
        self.power_manager = PowerManager()
        self.log_manager = LogManager()
        self.auth_manager = AuthManager()
        
        # Initialize WebAuthn manager if available
        if WEBAUTHN_ENABLED:
            try:
                self.webauthn_manager = WebAuthnManager()
                print("🔐 WebAuthn authentication enabled")
            except Exception as e:
                print(f"⚠️  WebAuthn initialization failed: {e}")
                self.webauthn_manager = None
        else:
            self.webauthn_manager = None
        
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
        httpd = ThreadingHTTPServer(server_address, PiMonitorHandler)
        
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

    def version_string(self):
        """Reduce server signature exposure"""
        try:
            from config import config as _config
            name = _config.get('project.name', 'Pi Monitor')
            version = _config.get('project.version', '1.0.0')
            return f"{name}/{version}"
        except Exception:
            return "PiMonitor"
    
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
        elif path == '/api/version':
            self._handle_version()
        elif path == '/api/auth/user':
            self._handle_get_user_info()
        elif path == '/api/auth/status':
            self._handle_auth_status()
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
        elif path.startswith('/api/metrics/range'):
            self._handle_metrics_range(query_params)
        elif path == '/api/metrics/database':
            self._handle_database_stats()
        elif path == '/api/metrics/export':
            self._handle_metrics_export()
        elif path == '/api/metrics/interval':
            self._handle_metrics_interval(query_params)
        elif path == '/api/metrics/retention':
            self._handle_metrics_retention(query_params)
        elif path == '/api/refresh':
            self._handle_refresh()
        elif path == '/api/power':
            self._handle_power_status_get()
        elif path.startswith('/api/service/'):
            self._handle_service_endpoints(path)
        else:
            self._handle_404()
    
    def do_HEAD(self):
        """Handle HEAD requests (no response body)"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Public endpoints
        if path == '/health' or path == '/':
            self.send_response(200)
            self._set_common_headers()
            return

        # Protected API endpoints: authorize but do not send a body
        if path.startswith('/api/'):
            if not self._check_auth():
                self.send_response(401)
                self._set_common_headers()
                return
            self.send_response(200)
            self._set_common_headers()
            return

        # Not found
        self.send_response(404)
        self._set_common_headers()
        return

    def do_POST(self):
        """Handle POST requests"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Route to appropriate handler
        if path == '/api/auth/token':
            self._handle_auth()
        elif path == '/api/auth/webauthn/register/begin':
            self._handle_webauthn_register_begin()
        elif path == '/api/auth/webauthn/register/complete':
            self._handle_webauthn_register_complete()
        elif path == '/api/auth/webauthn/authenticate/begin':
            self._handle_webauthn_authenticate_begin()
        elif path == '/api/auth/webauthn/authenticate/complete':
            self._handle_webauthn_authenticate_complete()
        elif path == '/api/auth/logout':
            self._handle_logout()
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
        elif path == '/api/metrics/clear':
            self._handle_metrics_clear()
        elif path == '/api/metrics/interval':
            self._handle_metrics_interval(parse_qs(urlparse(self.path).query))
        elif path == '/api/metrics/retention':
            self._handle_metrics_retention(parse_qs(urlparse(self.path).query))
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
            "enhanced_monitoring": True,
            "service": "backend",
            "name": config.get('project.name', 'Pi Monitor')
        }
        self.wfile.write(json.dumps(response).encode())

    def _handle_version(self):
        """Return backend version and build information"""
        self.send_response(200)
        self._set_common_headers()
        version = config.get('project.version', '1.0.0')
        name = config.get('project.name', 'Pi Monitor')
        commit = config.get('project.commit', None) or os.environ.get('PI_MONITOR_COMMIT')
        started_at = self.server_instance.start_time
        response = {
            "service": "backend",
            "name": name,
            "version": version,
            "commit": commit,
            "started_at": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(started_at)),
            "uptime_seconds": int(time.time() - started_at)
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
        
        # Ensure we extract the log filename from the URL path without query params
        parsed_url = urlparse(self.path)
        log_name = parsed_url.path.split('/')[-1]
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

    def _handle_metrics_range(self, query_params):
        """Return metrics for a specific time range with optional pagination.

        Query params:
          start: epoch seconds (float)
          end: epoch seconds (float)
          limit: optional int
          offset: optional int
        """
        if not self._check_auth():
            self._send_unauthorized()
            return
        try:
            start_ts = float(query_params.get('start', [str(time.time() - 3600)])[0])
            end_ts = float(query_params.get('end', [str(time.time())])[0])
            limit = query_params.get('limit', [None])[0]
            offset = query_params.get('offset', [None])[0]
            limit_val = int(limit) if limit is not None else None
            offset_val = int(offset) if offset is not None else None

            metrics = self.server_instance.database.get_metrics_range(start_ts, end_ts, limit_val, offset_val)
            response = {
                "count": len(metrics),
                "start": start_ts,
                "end": end_ts,
                "metrics": metrics
            }
            self.send_response(200)
            self._set_common_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self._send_internal_error(f"Failed to get metrics range: {str(e)}")
    
    def _handle_database_stats(self):
        """Handle database stats"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self.server_instance.database.get_database_stats()
        self.wfile.write(json.dumps(response).encode())

    def _handle_metrics_export(self):
        """Export metrics as JSON"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        try:
            # Large range to include most historical data
            metrics = self.server_instance.database.get_metrics_history(minutes=525600, limit=1000000)
            self.send_response(200)
            # Override headers for download-friendly response
            self.send_header('Content-type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            response = {
                "exported_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "count": len(metrics),
                "metrics": metrics
            }
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self._send_internal_error(f"Failed to export metrics: {str(e)}")

    def _handle_metrics_interval(self, query_params):
        """Handle metrics interval updates"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        try:
            if self.command == 'GET':
                # Get current interval
                current_interval = self.server_instance.metrics_collector.get_collection_interval()
                response = {
                    "current_interval": current_interval,
                    "message": f"Current metrics collection interval: {current_interval} seconds"
                }
            elif self.command == 'POST':
                # Update interval from POST body
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        interval_str = data.get('interval', '5')
                        interval_seconds = float(interval_str)
                        
                        # Validate interval range
                        if interval_seconds < 1 or interval_seconds > 300:
                            response = {
                                "success": False,
                                "message": "Interval must be between 1 and 300 seconds"
                            }
                        else:
                            success = self.server_instance.metrics_collector.set_collection_interval(interval_seconds)
                            if success:
                                response = {
                                    "success": True,
                                    "message": f"Metrics collection interval updated to {interval_seconds} seconds",
                                    "new_interval": interval_seconds
                                }
                            else:
                                response = {
                                    "success": False,
                                    "message": "Failed to update collection interval"
                                }
                    except (ValueError, json.JSONDecodeError):
                        response = {
                            "success": False,
                            "message": "Invalid interval value. Must be a valid number."
                        }
                else:
                    response = {
                        "success": False,
                        "message": "No data provided in POST request"
                    }
            else:
                response = {
                    "success": False,
                    "message": "Method not allowed. Use GET to retrieve or POST to update."
                }
            
            self.send_response(200)
            self._set_common_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self._send_internal_error(f"Failed to handle metrics interval: {str(e)}")

    def _handle_metrics_retention(self, query_params):
        """Handle metrics retention updates"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        
        try:
            if self.command == 'GET':
                # Get current retention setting
                current_retention = self.server_instance.database.get_retention_hours()
                response = {
                    "current_retention_hours": current_retention,
                    "message": f"Current data retention: {current_retention} hours"
                }
            elif self.command == 'POST':
                # Update retention from POST body
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    try:
                        data = json.loads(post_data.decode('utf-8'))
                        retention_str = data.get('retention_hours', '24')
                        retention_hours = int(retention_str)
                        
                        # Validate retention range (1 hour to 168 hours = 1 week)
                        if retention_hours < 1 or retention_hours > 168:
                            response = {
                                "success": False,
                                "message": "Retention must be between 1 and 168 hours (1 week)"
                            }
                        else:
                            success = self.server_instance.database.set_retention_hours(retention_hours)
                            if success:
                                response = {
                                    "success": True,
                                    "message": f"Data retention updated to {retention_hours} hours",
                                    "new_retention_hours": retention_hours
                                }
                            else:
                                response = {
                                    "success": False,
                                    "message": "Failed to update data retention"
                                }
                    except (ValueError, json.JSONDecodeError):
                        response = {
                            "success": False,
                            "message": "Invalid retention value. Must be a valid number."
                        }
                else:
                    response = {
                        "success": False,
                        "message": "No data provided in POST request"
                    }
            else:
                response = {
                    "success": False,
                    "message": "Method not allowed. Use GET to retrieve or POST to update."
                }
            
            self.send_response(200)
            self._set_common_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self._send_internal_error(f"Failed to handle metrics retention: {str(e)}")

    def _handle_metrics_clear(self):
        """Clear all metrics from the database"""
        if not self._check_auth():
            self._send_unauthorized()
            return
        try:
            deleted = self.server_instance.database.clear_all_metrics()
            self.send_response(200)
            self._set_common_headers()
            self.wfile.write(json.dumps({"success": True, "deleted": deleted}).encode())
        except Exception as e:
            self._send_internal_error(f"Failed to clear metrics: {str(e)}")
    
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
        """Check authentication - supports both API key and WebAuthn JWT"""
        # First try WebAuthn JWT authentication
        if self._check_webauthn_auth():
            return True
        
        # Fall back to legacy API key authentication
        return self.server_instance.auth_manager.check_auth(self)
    
    def _set_common_headers(self):
        """Set common response headers"""
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        # Versioning headers for easier diagnostics
        try:
            self.send_header('X-PiMonitor-Name', config.get('project.name', 'Pi Monitor'))
            self.send_header('X-PiMonitor-Version', config.get('project.version', '1.0.0'))
            self.send_header('X-PiMonitor-Service', 'backend')
        except Exception:
            pass
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
    
    def _set_cors_headers(self):
        """Set CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        # Expose custom headers so frontend can read versioning
        self.send_header('Access-Control-Expose-Headers', 'X-PiMonitor-Name, X-PiMonitor-Version, X-PiMonitor-Service')
    
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
    
    # WebAuthn Authentication Handlers
    def _handle_webauthn_register_begin(self):
        """Handle WebAuthn registration initiation"""
        if not self.server_instance.webauthn_manager:
            self.send_response(503)
            self._set_common_headers()
            response = {"error": "WebAuthn not available"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                username = request_data.get('username', 'admin')
                
                result = self.server_instance.webauthn_manager.generate_registration_options(username)
                
                if 'error' in result:
                    self.send_response(400)
                else:
                    self.send_response(200)
                
                self._set_common_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(400)
                self._set_common_headers()
                response = {"error": "Missing request body"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            self._send_internal_error(f"Registration initiation failed: {str(e)}")
    
    def _handle_webauthn_register_complete(self):
        """Handle WebAuthn registration completion"""
        if not self.server_instance.webauthn_manager:
            self.send_response(503)
            self._set_common_headers()
            response = {"error": "WebAuthn not available"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                user_id = request_data.get('user_id')
                credential = request_data.get('credential')
                device_name = request_data.get('device_name', 'Unknown Device')
                
                if not user_id or not credential:
                    self.send_response(400)
                    self._set_common_headers()
                    response = {"error": "Missing user_id or credential"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                result = self.server_instance.webauthn_manager.verify_registration(
                    user_id, credential, device_name
                )
                
                if 'error' in result:
                    self.send_response(400)
                else:
                    self.send_response(200)
                
                self._set_common_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(400)
                self._set_common_headers()
                response = {"error": "Missing request body"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            self._send_internal_error(f"Registration completion failed: {str(e)}")
    
    def _handle_webauthn_authenticate_begin(self):
        """Handle WebAuthn authentication initiation"""
        if not self.server_instance.webauthn_manager:
            self.send_response(503)
            self._set_common_headers()
            response = {"error": "WebAuthn not available"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            username = None
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                username = request_data.get('username')
            
            result = self.server_instance.webauthn_manager.generate_authentication_options(username)
            
            if 'error' in result:
                self.send_response(400)
            else:
                self.send_response(200)
            
            self._set_common_headers()
            self.wfile.write(json.dumps(result).encode())
                
        except Exception as e:
            self._send_internal_error(f"Authentication initiation failed: {str(e)}")
    
    def _handle_webauthn_authenticate_complete(self):
        """Handle WebAuthn authentication completion"""
        if not self.server_instance.webauthn_manager:
            self.send_response(503)
            self._set_common_headers()
            response = {"error": "WebAuthn not available"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
                
                credential = request_data.get('credential')
                challenge_key = request_data.get('challenge_key')
                
                if not credential or not challenge_key:
                    self.send_response(400)
                    self._set_common_headers()
                    response = {"error": "Missing credential or challenge_key"}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Get request info for session tracking
                request_info = {
                    'user_agent': self.headers.get('User-Agent'),
                    'ip_address': self.client_address[0]
                }
                
                result = self.server_instance.webauthn_manager.verify_authentication(
                    credential, challenge_key, request_info
                )
                
                if 'error' in result:
                    self.send_response(400)
                else:
                    self.send_response(200)
                
                self._set_common_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(400)
                self._set_common_headers()
                response = {"error": "Missing request body"}
                self.wfile.write(json.dumps(response).encode())
                
        except Exception as e:
            self._send_internal_error(f"Authentication completion failed: {str(e)}")
    
    def _handle_logout(self):
        """Handle logout request"""
        if not self.server_instance.webauthn_manager:
            self.send_response(503)
            self._set_common_headers()
            response = {"error": "WebAuthn not available"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            # Get token from Authorization header
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self.send_response(400)
                self._set_common_headers()
                response = {"error": "Missing or invalid token"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            token = auth_header.split(' ')[1]
            result = self.server_instance.webauthn_manager.logout(token)
            
            self.send_response(200)
            self._set_common_headers()
            self.wfile.write(json.dumps(result).encode())
                
        except Exception as e:
            self._send_internal_error(f"Logout failed: {str(e)}")
    
    def _handle_get_user_info(self):
        """Handle get user info request"""
        if not self.server_instance.webauthn_manager:
            self.send_response(503)
            self._set_common_headers()
            response = {"error": "WebAuthn not available"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            # Get token from Authorization header
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                self._send_unauthorized()
                return
            
            token = auth_header.split(' ')[1]
            user_info = self.server_instance.webauthn_manager.get_user_info(token)
            
            if user_info:
                self.send_response(200)
                self._set_common_headers()
                response = {'success': True, 'user': user_info}
                self.wfile.write(json.dumps(response).encode())
            else:
                self._send_unauthorized()
                
        except Exception as e:
            self._send_internal_error(f"Get user info failed: {str(e)}")
    
    def _handle_auth_status(self):
        """Handle authentication status check"""
        self.send_response(200)
        self._set_common_headers()
        
        status = {
            'webauthn_enabled': self.server_instance.webauthn_manager is not None,
            'api_key_auth': True,  # Legacy API key auth still available
        }
        
        if self.server_instance.webauthn_manager:
            status.update(self.server_instance.webauthn_manager.get_stats())
        
        self.wfile.write(json.dumps(status).encode())
    
    def _check_webauthn_auth(self):
        """Check WebAuthn JWT authentication"""
        if not self.server_instance.webauthn_manager:
            return False
        
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        return self.server_instance.webauthn_manager.verify_jwt_token(token) is not None
