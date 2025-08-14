#!/usr/bin/env python3
"""
Pi Monitor - Utilities
Common utility functions and decorators
"""

import time
import logging
import json
from collections import defaultdict
from functools import wraps

logger = logging.getLogger(__name__)

def rate_limit(max_requests=100, window=60):
    """Rate limiting decorator"""
    def decorator(func):
        request_counts = defaultdict(list)
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                client_ip = getattr(self, 'client_address', ['unknown'])[0]
                now = time.time()
                
                # Clean old requests
                request_counts[client_ip] = [req_time for req_time in request_counts[client_ip] 
                                           if now - req_time < window]
                
                # Check rate limit
                if len(request_counts[client_ip]) >= max_requests:
                    self.send_response(429)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Retry-After', str(window))
                    self.end_headers()
                    response = {"error": "Rate limit exceeded", "retry_after": window}
                    self.wfile.write(json.dumps(response).encode())
                    return
                
                # Add current request
                request_counts[client_ip].append(now)
                
                return func(self, *args, **kwargs)
            except Exception as e:
                # If rate limiting fails, just execute the function
                logger.warning(f"Rate limiting failed: {e}, executing function anyway")
                return func(self, *args, **kwargs)
        return wrapper
    return decorator

def monitor_performance(func):
    """Monitor function performance"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    return wrapper
