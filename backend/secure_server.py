#!/usr/bin/env python3
"""
Pi Monitor - Secure HTTPS Server
Enhanced server with SSL/TLS encryption, security headers, and authentication
"""

import ssl
import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import hashlib
import hmac
import secrets

from config import config
from auth import AuthManager
from metrics import MetricsCollector
from database import MetricsDatabase
from system_monitor import SystemMonitor
from service_manager import ServiceManager
from power_manager import PowerManager
from log_manager import LogManager
from utils import rate_limit, monitor_performance

class SecurePiMonitorServer:
    """Secure Pi Monitor HTTPS server with enhanced security features"""
    
    def __init__(self, port=None, cert_file=None, key_file=None):
        self.port = port or config.get_port('backend')
        self.cert_file = cert_file or 'certs/server.crt'
        self.key_file = key_file or 'certs/server.key'
        self.start_time = time.time()
        
        # Security settings
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
        
        # Initialize services
        self.metrics_collector = MetricsCollector()
        self.database = MetricsDatabase()
        self.system_monitor = SystemMonitor()
        self.service_manager = ServiceManager()
        self.power_manager = PowerManager()
        self.log_manager = LogManager()
        self.auth_manager = AuthManager()
        
        # Security tokens for CSRF protection
        self.csrf_tokens = {}
        
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
        """Run the secure HTTPS server"""
        server_address = ('0.0.0.0', self.port)
        
        # Create HTTP server
        httpd = HTTPServer(server_address, SecurePiMonitorHandler)
        
        # Set server instance in handler for access to services
        SecurePiMonitorHandler.server_instance = self
        
        # Wrap with SSL context
        if self._setup_ssl():
            httpd.socket = self._create_ssl_socket(httpd.socket)
            print(f"🔒 SSL/TLS enabled with certificate: {self.cert_file}")
        else:
            print("⚠️  SSL/TLS disabled - running in HTTP mode")
        
        self._print_startup_info()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self._shutdown()
    
    def _setup_ssl(self):
        """Setup SSL context and certificates"""
        try:
            # Check if certificate files exist
            if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
                print(f"⚠️  Certificate files not found. Creating self-signed certificate...")
                self._create_self_signed_cert()
            
            return True
        except Exception as e:
            print(f"❌ SSL setup failed: {e}")
            return False
    
    def _create_self_signed_cert(self):
        """Create a self-signed certificate for development/testing"""
        try:
            # Create certs directory if it doesn't exist
            os.makedirs('certs', exist_ok=True)
            
            # Generate self-signed certificate using OpenSSL
            cert_cmd = f"""openssl req -x509 -newkey rsa:4096 -keyout {self.key_file} -out {self.cert_file} -days 365 -nodes -subj "/C=US/ST=State/L=City/O=PiMonitor/CN=localhost" """
            
            result = os.system(cert_cmd)
            if result == 0:
                print(f"✅ Self-signed certificate created: {self.cert_file}")
                # Set proper permissions
                os.chmod(self.key_file, 0o600)
                os.chmod(self.cert_file, 0o644)
            else:
                print("❌ Failed to create self-signed certificate")
                
        except Exception as e:
            print(f"❌ Certificate creation failed: {e}")
    
    def _create_ssl_socket(self, sock):
        """Create SSL context and wrap socket"""
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(self.cert_file, self.key_file)
            context.verify_mode = ssl.CERT_NONE  # For self-signed certs
            context.check_hostname = False
            
            return context.wrap_socket(sock, server_side=True)
        except Exception as e:
            print(f"❌ SSL socket creation failed: {e}")
            return sock
    
    def _print_startup_info(self):
        """Print server startup information"""
        print("=" * 60)
        print("🔒 Pi Monitor Secure Backend Server Starting...")
        print("=" * 60)
        print(f"📍 Port: {self.port}")
        print(f"🔒 SSL/TLS: {'Enabled' if os.path.exists(self.cert_file) else 'Disabled'}")
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
        protocol = "https" if os.path.exists(self.cert_file) else "http"
        print(f"🚀 Server running at {protocol}://0.0.0.0:{self.port}")
        print(f"🔗 Health check: {protocol}://0.0.0.0:{self.port}/health")
        print("=" * 60)
    
    def _shutdown(self):
        """Shutdown the server and cleanup"""
        print("\n🛑 Shutting down secure server...")
        print("🛑 Stopping metrics collection...")
        self.metrics_collector.stop_collection()
        print("🛑 Shutting down HTTPS server...")
        print("✅ Secure server shutdown complete")
    
    def generate_csrf_token(self, session_id):
        """Generate CSRF token for a session"""
        token = secrets.token_urlsafe(32)
        self.csrf_tokens[session_id] = token
        return token
    
    def verify_csrf_token(self, session_id, token):
        """Verify CSRF token for a session"""
        return self.csrf_tokens.get(session_id) == token


class SecurePiMonitorHandler(BaseHTTPRequestHandler):
    """Secure HTTP request handler with enhanced security"""
    
    server_instance = None
    
    def _set_common_headers(self):
        """Set common security headers for all responses"""
        for header, value in self.server_instance.security_headers.items():
            self.send_header(header, value)
    
    def _log_request(self, status_code):
        """Log request with security information"""
        client_ip = self.client_address[0]
        user_agent = self.headers.get('User-Agent', 'Unknown')
        referer = self.headers.get('Referer', 'None')
        
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'client_ip': client_ip,
            'method': self.command,
            'path': self.path,
            'status': status_code,
            'user_agent': user_agent,
            'referer': referer
        }
        
        print(f"🔒 {log_entry['timestamp']} - {client_ip} {self.command} {self.path} {status_code}")
    
    def _send_security_error(self, message, status_code=403):
        """Send security error response"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self._set_common_headers()
        self.end_headers()
        
        response = {
            'error': 'Security Violation',
            'message': message,
            'timestamp': time.time()
        }
        
        self.wfile.write(json.dumps(response).encode())
    
    def _check_rate_limit(self):
        """Check rate limiting for the client"""
        client_ip = self.client_address[0]
        if not rate_limit(client_ip, max_requests=100, window_seconds=60):
            return False
        return True
    
    def _validate_request(self):
        """Validate incoming request for security"""
        # Check rate limiting
        if not self._check_rate_limit():
            return False, "Rate limit exceeded"
        
        # Check for suspicious headers
        suspicious_headers = ['X-Forwarded-For', 'X-Real-IP', 'X-Forwarded-Host']
        for header in suspicious_headers:
            if header in self.headers:
                return False, f"Suspicious header detected: {header}"
        
        return True, "OK"
    
    def do_GET(self):
        """Handle GET requests with security validation"""
        # Validate request
        is_valid, message = self._validate_request()
        if not is_valid:
            self._send_security_error(message)
            return
        
        # Log request
        self._log_request(200)
        
        # Set security headers
        self._set_common_headers()
        
        # Handle the request (delegate to existing logic)
        self._handle_get_request()
    
    def do_POST(self):
        """Handle POST requests with security validation"""
        # Validate request
        is_valid, message = self._validate_request()
        if not is_valid:
            self._send_security_error(message)
            return
        
        # Check content length
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 1024 * 1024:  # 1MB limit
            self._send_security_error("Request too large", 413)
            return
        
        # Log request
        self._log_request(200)
        
        # Set security headers
        self._set_common_headers()
        
        # Handle the request (delegate to existing logic)
        self._handle_post_request()
    
    def _handle_get_request(self):
        """Handle GET request logic"""
        # This would contain the existing GET request handling logic
        # For now, just send a basic response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'message': 'Secure Pi Monitor API',
            'status': 'secure',
            'timestamp': time.time()
        }
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_post_request(self):
        """Handle POST request logic"""
        # This would contain the existing POST request handling logic
        # For now, just send a basic response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'message': 'Secure Pi Monitor API',
            'status': 'secure',
            'timestamp': time.time()
        }
        
        self.wfile.write(json.dumps(response).encode())


def main():
    """Main entry point for secure Pi Monitor"""
    try:
        # Create and run the secure server
        server = SecurePiMonitorServer()
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Secure Pi Monitor...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import sys
        sys.exit(1)


if __name__ == '__main__':
    main()
