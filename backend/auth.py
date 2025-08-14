#!/usr/bin/env python3
"""
Pi Monitor - Authentication
Handles API key authentication and validation
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages API key authentication"""
    
    def __init__(self):
        self.api_key = os.environ.get('PI_MONITOR_API_KEY') or os.environ.get('PI_MONITOR_API_KEY_FILE')
        if self.api_key and os.path.isfile(self.api_key):
            try:
                with open(self.api_key, 'r') as f:
                    self.api_key = f.read().strip()
            except Exception:
                self.api_key = None
        if not self.api_key:
            # Fallback for dev; print a warning in production
            self.api_key = 'pi-monitor-api-key-2024'
            logger.warning('Using default API key; set PI_MONITOR_API_KEY for production')
    
    def check_auth(self, request_handler):
        """Check if request is authenticated"""
        auth_header = request_handler.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        api_key = auth_header.split(' ')[1]
        return api_key == self.api_key
    
    def handle_auth(self, request_handler):
        """Handle authentication request"""
        try:
            content_length = int(request_handler.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = request_handler.rfile.read(content_length)
                auth_data = json.loads(post_data.decode('utf-8'))
                api_key = auth_data.get('api_key', '')
                
                if api_key == self.api_key:
                    logger.info("API key authentication successful")
                    return {
                        "success": True,
                        "message": "API key authentication successful",
                        "auth_method": "api_key"
                    }
                else:
                    logger.warning("API key authentication failed")
                    return {
                        "error": "Invalid API key",
                        "message": "Authentication failed"
                    }
            else:
                logger.warning("Missing request body in auth request")
                return {
                    "error": "Missing request body",
                    "message": "API key required"
                }
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Invalid JSON data in auth request: {e}")
            return {
                "error": "Invalid JSON data",
                "message": "Request body must be valid JSON"
            }
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return {
                "error": "Authentication failed",
                "message": str(e)
            }
    
    def generate_api_key(self):
        """Generate a new API key (for admin use)"""
        try:
            import secrets
            return secrets.token_urlsafe(32)
        except ImportError:
            import random
            import string
            return ''.join(random.choices(string.ascii_letters + string.digits, k=32))
