#!/usr/bin/env python3
"""
Pi Monitor - Security Configuration
Centralized security settings and configuration
"""

import os
import json
from typing import Dict, List, Optional

class SecurityConfig:
    """Security configuration manager for Pi Monitor"""
    
    def __init__(self, config_file: str = 'security_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load security configuration from file"""
        default_config = {
            'ssl': {
                'enabled': True,
                'cert_file': 'certs/server.crt',
                'key_file': 'certs/server.key',
                'verify_mode': 'none',  # none, optional, required
                'check_hostname': False
            },
            'security_headers': {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
            },
            'rate_limiting': {
                'enabled': True,
                'max_requests': 100,
                'window_seconds': 60,
                'burst_limit': 20
            },
            'authentication': {
                'enabled': True,
                'session_timeout': 3600,  # 1 hour
                'max_login_attempts': 5,
                'lockout_duration': 900,  # 15 minutes
                'require_https': True
            },
            'cors': {
                'enabled': True,
                'allowed_origins': ['https://localhost:3000', 'https://127.0.0.1:3000'],
                'allowed_methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'allowed_headers': ['Content-Type', 'Authorization'],
                'expose_headers': ['X-CSRF-Token']
            },
            'input_validation': {
                'max_content_length': 1048576,  # 1MB
                'allowed_file_types': ['.txt', '.log', '.json'],
                'block_suspicious_headers': True,
                'suspicious_headers': ['X-Forwarded-For', 'X-Real-IP', 'X-Forwarded-Host']
            },
            'logging': {
                'security_events': True,
                'failed_attempts': True,
                'suspicious_activity': True,
                'log_level': 'INFO'
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge user config with defaults
                    self._merge_configs(default_config, user_config)
            else:
                # Create default config file
                self._save_config(default_config)
                default_config = default_config
        except Exception as e:
            print(f"⚠️  Warning: Could not load security config: {e}")
            print("   Using default security settings")
        
        return default_config
    
    def _merge_configs(self, default: Dict, user: Dict):
        """Recursively merge user configuration with defaults"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_configs(default[key], value)
            else:
                default[key] = value
    
    def _save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save security config: {e}")
    
    def get_ssl_config(self) -> Dict:
        """Get SSL configuration"""
        return self.config.get('ssl', {})
    
    def get_security_headers(self) -> Dict:
        """Get security headers configuration"""
        return self.config.get('security_headers', {})
    
    def get_rate_limiting_config(self) -> Dict:
        """Get rate limiting configuration"""
        return self.config.get('rate_limiting', {})
    
    def get_auth_config(self) -> Dict:
        """Get authentication configuration"""
        return self.config.get('authentication', {})
    
    def get_cors_config(self) -> Dict:
        """Get CORS configuration"""
        return self.config.get('cors', {})
    
    def get_input_validation_config(self) -> Dict:
        """Get input validation configuration"""
        return self.config.get('input_validation', {})
    
    def get_logging_config(self) -> Dict:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def is_ssl_enabled(self) -> bool:
        """Check if SSL is enabled"""
        return self.config.get('ssl', {}).get('enabled', False)
    
    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled"""
        return self.config.get('authentication', {}).get('enabled', False)
    
    def is_rate_limiting_enabled(self) -> bool:
        """Check if rate limiting is enabled"""
        return self.config.get('rate_limiting', {}).get('enabled', False)
    
    def is_cors_enabled(self) -> bool:
        """Check if CORS is enabled"""
        return self.config.get('cors', {}).get('enabled', False)
    
    def update_config(self, section: str, key: str, value):
        """Update a specific configuration value"""
        if section in self.config and key in self.config[section]:
            self.config[section][key] = value
            self._save_config(self.config)
            return True
        return False
    
    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()
    
    def get_full_config(self) -> Dict:
        """Get the complete configuration"""
        return self.config.copy()
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return any errors"""
        errors = []
        
        # Check SSL certificate files
        ssl_config = self.get_ssl_config()
        if ssl_config.get('enabled', False):
            cert_file = ssl_config.get('cert_file')
            key_file = ssl_config.get('key_file')
            
            if cert_file and not os.path.exists(cert_file):
                errors.append(f"SSL certificate file not found: {cert_file}")
            
            if key_file and not os.path.exists(key_file):
                errors.append(f"SSL private key file not found: {key_file}")
        
        # Check rate limiting values
        rate_config = self.get_rate_limiting_config()
        if rate_config.get('enabled', False):
            if rate_config.get('max_requests', 0) <= 0:
                errors.append("Rate limiting max_requests must be greater than 0")
            
            if rate_config.get('window_seconds', 0) <= 0:
                errors.append("Rate limiting window_seconds must be greater than 0")
        
        return errors


# Global security configuration instance
security_config = SecurityConfig()
