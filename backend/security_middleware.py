#!/usr/bin/env python3
"""
Pi Monitor - Security Middleware
Security middleware for request validation, rate limiting, and threat detection
"""

import time
import hashlib
import hmac
import secrets
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
import logging

from security_config import security_config

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Security middleware for Pi Monitor"""
    
    def __init__(self):
        self.rate_limit_store = defaultdict(lambda: deque(maxlen=1000))
        self.failed_attempts = defaultdict(int)
        self.lockout_until = defaultdict(float)
        self.suspicious_ips = defaultdict(int)
        self.blocked_ips = set()
        
        # Load security configuration
        self.config = security_config
        
        # Compile regex patterns for validation
        self.suspicious_patterns = [
            re.compile(r'<script', re.IGNORECASE),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'data:text/html', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'onload=', re.IGNORECASE),
            re.compile(r'onerror=', re.IGNORECASE),
            re.compile(r'../', re.IGNORECASE),
            re.compile(r'\.\./', re.IGNORECASE),
        ]
    
    def validate_request(self, client_ip: str, headers: Dict, method: str, 
                        path: str, content_length: int = 0) -> Tuple[bool, str, Dict]:
        """
        Validate incoming request for security threats
        
        Returns:
            Tuple[bool, str, Dict]: (is_valid, message, security_info)
        """
        security_info = {
            'threats_detected': [],
            'risk_score': 0,
            'validation_passed': True
        }
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return False, "IP address is blocked", security_info
        
        # Check rate limiting
        if not self._check_rate_limit(client_ip):
            return False, "Rate limit exceeded", security_info
        
        # Check for suspicious headers
        header_threats = self._check_suspicious_headers(headers)
        if header_threats:
            security_info['threats_detected'].extend(header_threats)
            security_info['risk_score'] += len(header_threats) * 10
        
        # Check for suspicious patterns in path
        path_threats = self._check_suspicious_patterns(path)
        if path_threats:
            security_info['threats_detected'].extend(path_threats)
            security_info['risk_score'] += len(path_threats) * 15
        
        # Check content length
        if content_length > self.config.get_input_validation_config().get('max_content_length', 1048576):
            return False, "Request too large", security_info
        
        # Check for failed authentication attempts
        if self._is_ip_locked_out(client_ip):
            return False, "Too many failed attempts", security_info
        
        # If risk score is too high, block the request
        if security_info['risk_score'] > 50:
            self._block_ip(client_ip)
            return False, "Suspicious activity detected", security_info
        
        # Log security event if threats detected
        if security_info['threats_detected']:
            self._log_security_event(client_ip, "threats_detected", security_info)
        
        return True, "OK", security_info
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check rate limiting for the client"""
        if not self.config.is_rate_limiting_enabled():
            return True
        
        rate_config = self.config.get_rate_limiting_config()
        max_requests = rate_config.get('max_requests', 100)
        window_seconds = rate_config.get('window_seconds', 60)
        
        now = time.time()
        client_requests = self.rate_limit_store[client_ip]
        
        # Remove old requests outside the window
        while client_requests and now - client_requests[0] > window_seconds:
            client_requests.popleft()
        
        # Check if limit exceeded
        if len(client_requests) >= max_requests:
            self._increment_suspicious_score(client_ip)
            return False
        
        # Add current request
        client_requests.append(now)
        return True
    
    def _check_suspicious_headers(self, headers: Dict) -> List[str]:
        """Check for suspicious HTTP headers"""
        threats = []
        suspicious_headers = self.config.get_input_validation_config().get('suspicious_headers', [])
        
        for header in suspicious_headers:
            if header in headers:
                threats.append(f"Suspicious header: {header}")
        
        # Check for other suspicious patterns
        for header_name, header_value in headers.items():
            header_lower = header_name.lower()
            value_lower = str(header_value).lower()
            
            # Check for XSS attempts in headers
            if any(pattern.search(value_lower) for pattern in self.suspicious_patterns):
                threats.append(f"XSS attempt in header: {header_name}")
            
            # Check for header injection attempts
            if '\n' in header_value or '\r' in header_value:
                threats.append(f"Header injection attempt: {header_name}")
        
        return threats
    
    def _check_suspicious_patterns(self, path: str) -> List[str]:
        """Check for suspicious patterns in request path"""
        threats = []
        path_lower = path.lower()
        
        # Check for path traversal attempts
        if '..' in path or '../' in path:
            threats.append("Path traversal attempt")
        
        # Check for XSS attempts
        if any(pattern.search(path_lower) for pattern in self.suspicious_patterns):
            threats.append("XSS attempt in path")
        
        # Check for SQL injection patterns
        sql_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter)\b)",
            r"(--|\b(and|or)\b\s+\d+\s*[=<>])",
            r"(\b(exec|execute|xp_|sp_)\b)"
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, path_lower, re.IGNORECASE):
                threats.append("SQL injection attempt")
                break
        
        return threats
    
    def _is_ip_locked_out(self, client_ip: str) -> bool:
        """Check if IP is temporarily locked out"""
        if client_ip in self.lockout_until:
            if time.time() < self.lockout_until[client_ip]:
                return True
            else:
                # Lockout expired, remove it
                del self.lockout_until[client_ip]
                self.failed_attempts[client_ip] = 0
        
        return False
    
    def _increment_suspicious_score(self, client_ip: str):
        """Increment suspicious activity score for an IP"""
        self.suspicious_ips[client_ip] += 1
        
        # If score gets too high, block the IP
        if self.suspicious_ips[client_ip] >= 10:
            self._block_ip(client_ip)
    
    def _block_ip(self, client_ip: str):
        """Block an IP address"""
        self.blocked_ips.add(client_ip)
        logger.warning(f"IP {client_ip} has been blocked due to suspicious activity")
    
    def record_failed_attempt(self, client_ip: str, attempt_type: str = "auth"):
        """Record a failed authentication attempt"""
        self.failed_attempts[client_ip] += 1
        
        auth_config = self.config.get_auth_config()
        max_attempts = auth_config.get('max_login_attempts', 5)
        lockout_duration = auth_config.get('lockout_duration', 900)
        
        if self.failed_attempts[client_ip] >= max_attempts:
            self.lockout_until[client_ip] = time.time() + lockout_duration
            logger.warning(f"IP {client_ip} locked out for {lockout_duration} seconds due to {attempt_type} failures")
    
    def record_successful_attempt(self, client_ip: str):
        """Record a successful authentication attempt"""
        self.failed_attempts[client_ip] = 0
        self.suspicious_ips[client_ip] = max(0, self.suspicious_ips[client_ip] - 1)
    
    def generate_csrf_token(self, session_id: str) -> str:
        """Generate a CSRF token for a session"""
        return secrets.token_urlsafe(32)
    
    def verify_csrf_token(self, session_id: str, token: str) -> bool:
        """Verify a CSRF token"""
        # In a real implementation, you'd store and verify against stored tokens
        # For now, we'll just check if it's a valid format
        return len(token) >= 32 and token.isalnum()
    
    def sanitize_input(self, input_data: str) -> str:
        """Sanitize user input to prevent XSS and injection attacks"""
        if not input_data:
            return input_data
        
        # Remove or escape dangerous characters
        sanitized = input_data
        
        # HTML entity encoding for dangerous characters
        dangerous_chars = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        
        for char, entity in dangerous_chars.items():
            sanitized = sanitized.replace(char, entity)
        
        return sanitized
    
    def _log_security_event(self, client_ip: str, event_type: str, details: Dict):
        """Log security events"""
        if self.config.get_logging_config().get('security_events', True):
            logger.warning(f"Security event: {event_type} from {client_ip} - {details}")
    
    def get_security_stats(self) -> Dict:
        """Get security statistics"""
        return {
            'blocked_ips': len(self.blocked_ips),
            'suspicious_ips': len(self.suspicious_ips),
            'locked_out_ips': len([ip for ip in self.lockout_until if time.time() < self.lockout_until[ip]]),
            'total_failed_attempts': sum(self.failed_attempts.values()),
            'rate_limit_violations': sum(1 for ip, requests in self.rate_limit_store.items() if len(requests) >= 100)
        }
    
    def cleanup_old_data(self):
        """Clean up old security data"""
        now = time.time()
        
        # Clean up expired lockouts
        expired_lockouts = [ip for ip, lockout_time in self.lockout_until.items() if now > lockout_time]
        for ip in expired_lockouts:
            del self.lockout_until[ip]
            self.failed_attempts[ip] = 0
        
        # Clean up old rate limit data (older than 1 hour)
        cutoff_time = now - 3600
        for ip, requests in self.rate_limit_store.items():
            while requests and requests[0] < cutoff_time:
                requests.popleft()
        
        # Clean up empty rate limit entries
        empty_ips = [ip for ip, requests in self.rate_limit_store.items() if not requests]
        for ip in empty_ips:
            del self.rate_limit_store[ip]


# Global security middleware instance
security_middleware = SecurityMiddleware()
