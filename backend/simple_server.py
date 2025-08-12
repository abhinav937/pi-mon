#!/usr/bin/env python3
"""
Pi Monitor - Enhanced HTTP Server
RPi-Monitor inspired monitoring system with real-time data collection
Enhanced with comprehensive system monitoring commands and optimizations
"""

import json
import time
import os

# Handle subprocess import gracefully
try:
    import subprocess
except ImportError:
    # Create a minimal subprocess fallback
    class MinimalSubprocess:
        class CompletedProcess:
            def __init__(self, returncode, stdout, stderr):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        
        @staticmethod
        def run(cmd, shell=False, capture_output=False, text=False, timeout=None):
            # Simple fallback that returns a mock result
            return MinimalSubprocess.CompletedProcess(0, "", "")
    
    subprocess = MinimalSubprocess()

# Handle psutil import gracefully
try:
    import psutil
except ImportError:
    # Create a minimal psutil fallback
    class MinimalPsutil:
        @staticmethod
        def cpu_percent(interval=None):
            return 0.0
        
        @staticmethod
        def virtual_memory():
            class Memory:
                total = 1024**3  # 1GB default
                available = 512**3  # 512MB default
                used = 512**3  # 512MB default
                free = 512**3  # 512MB default
                percent = 50.0
            return Memory()
        
        @staticmethod
        def disk_usage(path):
            class Disk:
                total = 10**12  # 1TB default
                used = 5**12  # 500GB default
                free = 5**12  # 500GB default
                percent = 50.0
            return Disk()
        
        @staticmethod
        def net_io_counters():
            class Network:
                bytes_sent = 0
                bytes_recv = 0
                packets_sent = 0
                packets_recv = 0
            return Network()
        
        @staticmethod
        def disk_io_counters():
            class DiskIO:
                read_bytes = 0
                write_bytes = 0
                read_count = 0
                write_count = 0
            return DiskIO()
        
        @staticmethod
        def cpu_freq():
            class CPUFreq:
                current = 1000.0  # 1GHz default
                min = 800.0  # 800MHz default
                max = 2000.0  # 2GHz default
            return CPUFreq()
        
        @staticmethod
        def cpu_count(logical=True):
            return 4  # Default to 4 cores
        
        @staticmethod
        def boot_time():
            return time.time() - 3600  # Default to 1 hour ago
    
    psutil = MinimalPsutil()

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
from functools import wraps
from collections import deque, defaultdict
import logging

# Handle optional imports gracefully
try:
    from functools import lru_cache
except ImportError:
    # Create a dummy lru_cache decorator if not available
    def lru_cache(maxsize=128, typed=False):
        def decorator(func):
            return func
        return decorator

try:
    import asyncio
except ImportError:
    asyncio = None

try:
    import concurrent.futures
except ImportError:
    concurrent.futures = None

try:
    from typing import Dict, List, Optional, Any, Union
except ImportError:
    # Create dummy types if typing module is not available
    Dict = dict
    List = list
    Optional = lambda x: x
    Any = object
    Union = lambda *args: args[0] if args else object

try:
    import weakref
except ImportError:
    weakref = None

# Configure logging
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('pi_monitor.log'),
            logging.StreamHandler()
        ]
    )
except Exception as e:
    # Fallback to console-only logging if file logging fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
logger = logging.getLogger(__name__)

# Add parent directory to path to import config
try:
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

# Configuration constants
API_KEY = os.environ.get('PI_MONITOR_API_KEY', 'pi-monitor-api-key-2024')  # Default fallback
MAX_CONNECTIONS = 100
REQUEST_TIMEOUT = 30
CACHE_TTL = 60  # Cache TTL in seconds

# Enhanced system monitoring commands with categories
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

# Connection pool for managing concurrent requests
class ConnectionPool:
    def __init__(self, max_connections=MAX_CONNECTIONS):
        self.max_connections = max_connections
        self.active_connections = 0
        self.connection_lock = threading.Lock()
        self.connection_semaphore = threading.Semaphore(max_connections)
    
    def acquire_connection(self):
        """Acquire a connection slot"""
        return self.connection_semaphore.acquire(blocking=True, timeout=REQUEST_TIMEOUT)
    
    def release_connection(self):
        """Release a connection slot"""
        self.connection_semaphore.release()
    
    def get_active_connections(self):
        """Get current active connection count"""
        return self.max_connections - self.connection_semaphore._value

# Enhanced caching system with TTL and LRU
class EnhancedCache:
    def __init__(self, max_size=1000, default_ttl=CACHE_TTL):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_order = deque()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self.lock:
            if key in self.cache:
                value, timestamp, ttl = self.cache[key]
                if time.time() - timestamp < ttl:
                    # Move to front (most recently used)
                    self.access_order.remove(key)
                    self.access_order.appendleft(key)
                    return value
                else:
                    # Expired, remove
                    del self.cache[key]
                    self.access_order.remove(key)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        if ttl is None:
            ttl = self.default_ttl
        
        with self.lock:
            # Remove if exists
            if key in self.cache:
                self.access_order.remove(key)
            
            # Add new entry
            self.cache[key] = (value, time.time(), ttl)
            self.access_order.appendleft(key)
            
            # Evict if cache is full
            if len(self.cache) > self.max_size:
                oldest_key = self.access_order.pop()
                del self.cache[oldest_key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.access_order.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)

# Thread pool for concurrent command execution
class CommandExecutor:
    def __init__(self, max_workers=10):
        if concurrent.futures:
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        else:
            self.executor = None
        self.cache = EnhancedCache()
    
    def execute_command(self, command: str, timeout: int = 10) -> Dict[str, Any]:
        """Execute a system command with caching"""
        cache_key = f"cmd:{hashlib.md5(command.encode()).hexdigest()}"
        
        # Check cache first
        cached_result = self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Execute command
        if self.executor:
            try:
                future = self.executor.submit(self._run_command, command, timeout)
                result = future.result(timeout=timeout + 5)
                
                # Cache successful results
                if result['success']:
                    self.cache.set(cache_key, result, ttl=30)  # Cache for 30 seconds
                
                return result
            except concurrent.futures.TimeoutError:
                return {
                    'success': False,
                    'output': None,
                    'error': 'Command execution timed out'
                }
            except Exception as e:
                return {
                    'success': False,
                    'output': None,
                    'error': str(e)
                }
        else:
            # Fallback to direct execution if ThreadPoolExecutor is not available
            result = self._run_command(command, timeout)
            if result['success']:
                self.cache.set(cache_key, result, ttl=30)
            return result
    
    def _run_command(self, command: str, timeout: int) -> Dict[str, Any]:
        """Run a system command safely"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=timeout
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
    
    def shutdown(self):
        """Shutdown the executor"""
        if self.executor:
            self.executor.shutdown(wait=True)

# Global instances
connection_pool = ConnectionPool()
command_executor = CommandExecutor()
metrics_cache = EnhancedCache(max_size=500, default_ttl=30)

# Network rate tracker for calculating upload/download speeds
net_rate_tracker = {
    'last_ts': 0.0,
    'pernic': {},  # name -> (bytes_recv, bytes_sent)
    'totals': {'bytes_recv': 0, 'bytes_sent': 0}
}

# Global data storage for real-time metrics with improved performance
class EnhancedMetricsCollector:
    def __init__(self):
        self.collection_interval = 5.0
        self.is_collecting = False
        self.collection_thread = None
        self.command_cache = EnhancedCache(max_size=100, default_ttl=30)
        self.last_collection = 0
        self.collection_lock = threading.Lock()
        
        # Performance counters
        self.collection_count = 0
        self.error_count = 0
        self.last_error = None
        self.max_history = 1000  # Keep last 1000 data points in memory for quick access
        
        # In-memory cache for recent data (for performance)
        self.recent_cache = deque(maxlen=100)
        
    def start_collection(self):
        """Start background metrics collection"""
        if not self.is_collecting:
            self.is_collecting = True
            self.collection_thread = threading.Thread(target=self._collect_metrics, daemon=True)
            self.collection_thread.start()
            logger.info("Metrics collection started")
    
    def stop_collection(self):
        """Stop background metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=1)
            logger.info("Metrics collection stopped")
    
    def _collect_metrics(self):
        """Background thread for collecting metrics with improved error handling"""
        while self.is_collecting:
            try:
                start_time = time.time()
                
                # Check if enough time has passed since last collection
                if start_time - self.last_collection < self.collection_interval:
                    time.sleep(0.1)
                    continue
                
                metrics = self._gather_current_metrics()
                if metrics and 'error' not in metrics:
                    with self.collection_lock:
                        # Store in database for persistence
                        if metrics_db.insert_metrics(metrics):
                            # Also keep in memory cache for quick access
                            self.recent_cache.append(metrics)
                            self.collection_count += 1
                        else:
                            self.error_count += 1
                            self.last_error = 'Failed to store metrics in database'
                    
                    self.last_collection = start_time
                else:
                    self.error_count += 1
                    self.last_error = metrics.get('error', 'Unknown error') if metrics else 'No metrics'
                    
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                logger.error(f"Error collecting metrics: {e}")
            
            time.sleep(0.1)  # Reduced sleep for more responsive collection
    
    def _gather_current_metrics(self):
        """Gather current system metrics with enhanced data and error handling"""
        try:
            # Basic metrics using psutil (more reliable)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            temperature = self._get_temperature()
            network = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()
            
            # Enhanced metrics using system commands (cached)
            enhanced_metrics = self._get_enhanced_metrics()
            
            return {
                "timestamp": time.time(),
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "disk_percent": round(disk.percent, 1),
                "temperature": temperature,
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
                },
                "enhanced": enhanced_metrics
            }
        except Exception as e:
            logger.error(f"Failed to gather metrics: {e}")
            return {"timestamp": time.time(), "error": str(e)}
    
    def _get_enhanced_metrics(self):
        """Get enhanced metrics using system commands with caching"""
        enhanced = {}
        
        # Get key metrics that don't change frequently
        key_commands = ['cpu_temperature', 'arm_clock', 'core_voltage', 'throttling_status']
        
        for metric in key_commands:
            if metric in SYSTEM_COMMANDS:
                try:
                    result = command_executor.execute_command(SYSTEM_COMMANDS[metric])
                    if result['success']:
                        enhanced[metric] = result['output']
                    else:
                        enhanced[metric] = None
                except:
                    enhanced[metric] = None
        
        return enhanced
    
    def get_metrics_history(self, minutes=60):
        """Get metrics history for the last N minutes from database with memory cache fallback"""
        try:
            # Try to get from database first
            db_metrics = metrics_db.get_metrics_history(minutes, self.max_history)
            if db_metrics:
                return db_metrics
            
            # Fallback to memory cache if database fails
            cutoff_time = time.time() - (minutes * 60)
            with self.collection_lock:
                return [m for m in self.recent_cache if m.get('timestamp', 0) > cutoff_time]
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            # Final fallback to memory cache
            cutoff_time = time.time() - (minutes * 60)
            with self.collection_lock:
                return [m for m in self.recent_cache if m.get('timestamp', 0) > cutoff_time]
    
    def get_latest_metrics(self):
        """Get the most recent metrics from memory cache or database"""
        try:
            # Try memory cache first for speed
            if self.recent_cache:
                return self.recent_cache[-1]
            
            # Fallback to database
            db_metrics = metrics_db.get_metrics_history(1, 1)  # Last 1 minute, 1 record
            return db_metrics[0] if db_metrics else None
        except Exception as e:
            logger.error(f"Failed to get latest metrics: {e}")
            return None
    
    def get_stats(self):
        """Get collection statistics"""
        try:
            db_stats = metrics_db.get_database_stats()
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            db_stats = {}
        
        return {
            "collection_count": self.collection_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "cache_size": len(self.recent_cache),
            "is_collecting": self.is_collecting,
            "database": db_stats
        }

# Global metrics collector instance
metrics_collector = EnhancedMetricsCollector()

# Rate limiting decorator
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

# Performance monitoring decorator
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

class SimplePiMonitorHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_start_time = time.time()
    
    def log_message(self, format, *args):
        """Custom logging with performance metrics"""
        try:
            execution_time = time.time() - getattr(self, 'request_start_time', time.time())
            logger.info(f"{self.client_address[0]} - {format % args} - {execution_time:.3f}s")
        except Exception as e:
            # Fallback logging if performance tracking fails
            logger.info(f"{self.client_address[0]} - {format % args}")
    
    def setup(self):
        """Setup method called before handling each request"""
        super().setup()
        self.request_start_time = time.time()
    
    @rate_limit(max_requests=100, window=60)
    def do_GET(self):
        """Handle GET requests with connection pooling"""
        if not connection_pool.acquire_connection():
            self.send_response(503)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Service temporarily unavailable - too many connections"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            self._handle_get_request()
        finally:
            connection_pool.release_connection()
    
    @monitor_performance
    def _handle_get_request(self):
        """Handle GET request logic"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # Route to appropriate handler
        if path == '/':
            self._handle_root_endpoint()
        elif path.startswith('/api/logs/') and '/download' in path:
            self._handle_log_download()
        elif path.startswith('/api/logs/') and path.endswith('/clear'):
            self._handle_log_clear()
        elif path.startswith('/api/services/'):
            self._handle_service_control()
        elif path == '/health':
            self._handle_health_check()
        elif path == '/api/system':
            self._handle_system_stats(query_params)
        elif path == '/api/system/enhanced':
            self._handle_enhanced_system_stats()
        elif path == '/api/system/info':
            self._handle_system_info_detail()
        elif path == '/api/service/restart':
            self._handle_service_restart_info()
        elif path == '/api/service/manage':
            self._handle_service_manage_info()
        elif path == '/api/service/info':
            self._handle_service_info()
        elif path == '/api/power':
            self._handle_power_status_get()
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
        elif path.startswith('/api/metrics/history'):
            self._handle_metrics_history(query_params)
        elif path == '/api/metrics/database':
            self._handle_database_stats()
        elif path == '/api/refresh':
            # Treat GET refresh to be idempotent for frontend convenience
            self._handle_refresh()
        else:
            self._handle_404()
    
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
            "system_info": self._get_system_info(),
            "available_commands": len(SYSTEM_COMMANDS),
            "enhanced_monitoring": True,
            "performance": {
                "active_connections": connection_pool.get_active_connections(),
                "cache_size": metrics_cache.size(),
                "metrics_stats": metrics_collector.get_stats()
            }
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_log_download(self):
        """Handle log download with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        try:
            # Extract log name from path
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            log_name = path.split('/')[-2]  # /api/logs/name/download
            
            # Try to find the log file in available directories
            log_file = self._find_log_file(log_name)
            
            if not log_file:
                self._send_not_found(f"Log file {log_name} not found")
                return
            
            # Read log content with streaming for large files
            self._stream_log_file(log_file, log_name)
            
        except Exception as e:
            logger.error(f"Log download failed: {e}")
            self._send_internal_error(f"Failed to download log: {str(e)}")
    
    def _find_log_file(self, log_name):
        """Find log file in available directories"""
        log_dirs = ['/var/log', '/tmp', './logs', 'logs']
        
        for log_dir in log_dirs:
            potential_path = os.path.join(log_dir, log_name)
            if os.path.exists(potential_path):
                return potential_path
        return None
    
    def _stream_log_file(self, log_file, log_name):
        """Stream log file content for better memory efficiency"""
        file_size = os.path.getsize(log_file)
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Content-Disposition', f'attachment; filename="{log_name}"')
        self.send_header('Content-Length', str(file_size))
        self._set_common_headers()
        
        # Stream file in chunks
        chunk_size = 8192
        with open(log_file, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)
    
    def _handle_log_clear(self):
        """Handle log clear with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        try:
            # Extract log name from path
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            log_name = path.split('/')[-2]  # /api/logs/name/clear
            
            # Try to find the log file in available directories
            log_file = self._find_log_file(log_name)
            
            if not log_file:
                self._send_not_found(f"Log file {log_name} not found")
                return
            
            # Clear log file (truncate to 0 bytes)
            with open(log_file, 'w') as f:
                pass  # This truncates the file
            
            self.send_response(200)
            self._set_common_headers()
            
            response = {
                "success": True,
                "message": f"Log {log_name} cleared successfully",
                "log_name": log_name,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            logger.error(f"Log clear failed: {e}")
            self._send_internal_error(f"Failed to clear log: {str(e)}")
    
    def _handle_service_control(self):
        """Handle service control with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        try:
            # Extract service name and action from path
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            path_parts = path.split('/')
            if len(path_parts) >= 4:
                service_name = path_parts[3]
                action = path_parts[4] if len(path_parts) > 4 else 'status'
                
                # Handle service actions
                result = self._execute_service_action(service_name, action)
                
                self.send_response(200)
                self._set_common_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self._send_bad_request("Invalid service path")
                
        except Exception as e:
            logger.error(f"Service control failed: {e}")
            self._send_internal_error(f"Service action failed: {str(e)}")
    
    def _execute_service_action(self, service_name, action):
        """Execute service action with improved error handling"""
        try:
            if action == 'start':
                result = os.system(f'sudo systemctl start {service_name}')
                if result == 0:
                    return {"success": True, "message": f"Service {service_name} started successfully"}
                else:
                    return {"success": False, "message": f"Failed to start service {service_name}"}
            elif action == 'stop':
                result = os.system(f'sudo systemctl stop {service_name}')
                if result == 0:
                    return {"success": True, "message": f"Service {service_name} stopped successfully"}
                else:
                    return {"success": False, "message": f"Failed to stop service {service_name}"}
            elif action == 'restart':
                result = os.system(f'sudo systemctl restart {service_name}')
                if result == 0:
                    return {"success": True, "message": f"Service {service_name} restarted successfully"}
                else:
                    return {"success": False, "message": f"Failed to restart service {service_name}"}
            elif action == 'status':
                result = os.system(f'sudo systemctl is-active {service_name}')
                if result == 0:
                    return {"success": True, "service": service_name, "status": "active"}
                else:
                    return {"success": True, "service": service_name, "status": "inactive"}
            else:
                return {"success": False, "message": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "message": f"Service action failed: {str(e)}"}
    
    def _handle_health_check(self):
        """Handle health check with enhanced information"""
        self.send_response(200)
        self._set_common_headers()
        
        response = {
            "status": "healthy",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "version": config.get('project.version', '1.0.0'),
            "uptime": self._get_uptime(),
            "config": {
                "ports": config.get('ports', {}),
                "features": config.get('backend.features', {})
            },
            "enhanced_monitoring": True,
            "performance": {
                "active_connections": connection_pool.get_active_connections(),
                "cache_size": metrics_cache.size(),
                "metrics_stats": metrics_collector.get_stats()
            }
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_system_stats(self, query_params):
        """Handle system stats with improved performance"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
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
    
    def _handle_enhanced_system_stats(self):
        """Handle enhanced system stats"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        response = self._get_enhanced_system_stats()
        self.wfile.write(json.dumps(response).encode())

    def _handle_system_info_detail(self):
        """Provide detailed system info used by frontend SystemStatus."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        try:
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            net_if_addrs = getattr(psutil, 'net_if_addrs', lambda: {})()
            network_interfaces = {}
            for name, addrs in net_if_addrs.items() if isinstance(net_if_addrs, dict) else []:
                network_interfaces[name] = {
                    'addrs': [
                        {
                            'addr': getattr(a, 'address', ''),
                            'netmask': getattr(a, 'netmask', ''),
                            'broadcast': getattr(a, 'broadcast', '')
                        }
                        for a in addrs
                    ]
                }
            response = {
                'cpu_info': {
                    'current_freq': round(cpu_freq.current, 1) if cpu_freq else 0,
                    'max_freq': round(cpu_freq.max, 1) if cpu_freq else 0,
                    'model': platform.processor() or platform.machine(),
                },
                'memory_info': {
                    'total': round(memory.total / (1024**3), 2) if memory else 0,
                    'available': round(memory.available / (1024**3), 2) if memory else 0,
                    'used': round(memory.used / (1024**3), 2) if memory else 0,
                    'percent': round(float(memory.percent), 1) if memory else 0,
                },
                'network_interfaces': network_interfaces
            }
        except Exception as e:
            response = {'error': str(e)}
        self.wfile.write(json.dumps(response).encode())

    def _handle_services_list(self):
        """List a small set of services with status for ServiceManagement UI."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        services = []
        candidate_services = ['ssh', 'nginx', 'docker', 'pi-monitor']
        for svc in candidate_services:
            status = 'unknown'
            active = False
            enabled = False
            try:
                result = subprocess.run(['systemctl', 'is-active', svc], capture_output=True, text=True, timeout=5)
                status = result.stdout.strip() if result.returncode == 0 else 'stopped'
                active = (status == 'active' or status == 'running')
                result2 = subprocess.run(['systemctl', 'is-enabled', svc], capture_output=True, text=True, timeout=5)
                enabled = (result2.returncode == 0 and 'enabled' in result2.stdout)
            except Exception:
                pass
            services.append({
                'name': svc,
                'status': 'running' if active else ('stopped' if status == 'stopped' else status or 'unknown'),
                'active': active,
                'enabled': enabled,
                'description': f'{svc} service'
            })
        self.wfile.write(json.dumps(services).encode())

    def _handle_network_info(self):
        """Return network interface details similar to frontend expectations."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        interfaces = []
        dns = {'primary': None, 'secondary': None}
        gateway = None
        route_status = None
        try:
            # Interfaces
            addrs = getattr(psutil, 'net_if_addrs', lambda: {})()
            stats = getattr(psutil, 'net_if_stats', lambda: {})()
            for name, addr_list in (addrs.items() if isinstance(addrs, dict) else []):
                iface_type = 'ethernet' if name.lower().startswith(('eth', 'enp', 'eno')) else ('wifi' if name.lower().startswith(('wlan', 'wl')) else 'other')
                iface = {
                    'name': name,
                    'type': iface_type,
                    'status': 'up' if (stats.get(name).isup if isinstance(stats, dict) and stats.get(name) else True) else 'down',
                }
                for a in addr_list:
                    if getattr(a, 'family', None) and str(getattr(a, 'family')) in ('AddressFamily.AF_INET', '2'):
                        iface['ip'] = getattr(a, 'address', None)
                    if hasattr(a, 'address') and a.address and ':' in a.address and 'mac' not in iface:
                        # crude MAC hint if psutil provides
                        iface['mac'] = a.address
                if isinstance(stats, dict) and stats.get(name):
                    iface['mtu'] = stats[name].mtu
                interfaces.append(iface)
            # DNS
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    servers = [line.split()[1] for line in f if line.startswith('nameserver')]
                    if servers:
                        dns['primary'] = servers[0]
                    if len(servers) > 1:
                        dns['secondary'] = servers[1]
            except Exception:
                pass
            # Gateway/route
            try:
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    for line in result.stdout.splitlines():
                        if line.startswith('default via'):
                            gateway = line.split()[2]
                            route_status = 'ok'
                            break
            except Exception:
                pass
        except Exception as e:
            interfaces = []
        self.wfile.write(json.dumps({
            'interfaces': interfaces,
            'dns': dns,
            'gateway': gateway,
            'routeStatus': route_status
        }).encode())

    def _handle_network_stats(self):
        """Return instantaneous upload/download speeds per interface and totals."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        try:
            now = time.time()
            pernic = getattr(psutil, 'net_io_counters', lambda pernic=False: None)(pernic=True)
            speeds = {}
            total_dl = 0.0
            total_ul = 0.0
            if isinstance(pernic, dict):
                last_ts = net_rate_tracker['last_ts']
                delta_t = max(1e-6, now - last_ts) if last_ts else None
                for name, counters in pernic.items():
                    prev = net_rate_tracker['pernic'].get(name, (counters.bytes_recv, counters.bytes_sent))
                    if delta_t:
                        dl = max(0, counters.bytes_recv - prev[0]) / delta_t
                        ul = max(0, counters.bytes_sent - prev[1]) / delta_t
                    else:
                        dl = 0.0
                        ul = 0.0
                    speeds[name] = {'download': dl, 'upload': ul}
                    net_rate_tracker['pernic'][name] = (counters.bytes_recv, counters.bytes_sent)
                    total_dl += dl
                    total_ul += ul
                net_rate_tracker['last_ts'] = now
            response = {'download': total_dl, 'upload': total_ul}
            response.update(speeds)
        except Exception as e:
            response = {'download': 0, 'upload': 0}
        self.wfile.write(json.dumps(response).encode())

    def _handle_logs_list(self, query_params):
        """Return a list of available log files (subset)."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        results = []
        for base in ['/var/log', './logs', 'logs']:
            try:
                if os.path.isdir(base):
                    for name in os.listdir(base):
                        # include a few common logs
                        if any(name.startswith(prefix) for prefix in ('syslog', 'auth', 'kern', 'daemon')) or name.endswith('.log'):
                            full = os.path.join(base, name)
                            try:
                                size_bytes = os.path.getsize(full)
                            except Exception:
                                size_bytes = 0
                            results.append({'name': name, 'path': base, 'size': size_bytes})
            except Exception:
                continue
        # include backend log if present
        if os.path.exists('pi_monitor.log'):
            try:
                size_bytes = os.path.getsize('pi_monitor.log')
            except Exception:
                size_bytes = 0
            results.append({'name': 'pi_monitor.log', 'path': '.', 'size': size_bytes})
        self.wfile.write(json.dumps(results).encode())

    def _handle_log_read(self, query_params):
        """Return last N lines of a specific log file."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            log_name = path.split('/')[-1]
            lines = int(query_params.get('lines', ['100'])[0])
            log_file = self._find_log_file(log_name) or ('pi_monitor.log' if log_name == 'pi_monitor.log' and os.path.exists('pi_monitor.log') else None)
            if not log_file:
                self.wfile.write(json.dumps({'error': 'Log not found'}).encode())
                return
            # Read last N lines efficiently
            content = self._tail_file(log_file, lines)
            entries = []
            error_count = 0
            warn_count = 0
            for line in content.splitlines():
                level = 'info'
                low = line.lower()
                if 'error' in low or ' err ' in low:
                    level = 'error'
                    error_count += 1
                elif 'warn' in low:
                    level = 'warning'
                    warn_count += 1
                entries.append({
                    'level': level,
                    'message': line,
                })
            try:
                size_bytes = os.path.getsize(log_file)
            except Exception:
                size_bytes = 0
            self.wfile.write(json.dumps({
                'name': log_name,
                'entries': entries,
                'totalEntries': len(entries),
                'errorCount': error_count,
                'warningCount': warn_count,
                'size': size_bytes
            }).encode())
        except Exception as e:
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _handle_refresh(self):
        """Invalidate caches and trigger an immediate metrics sample."""
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        try:
            # Clear caches
            metrics_cache.clear()
            command_executor.cache.clear()
            # Force an immediate metrics read and append to history
            data = self._get_system_stats()
            if data and 'error' not in data:
                with metrics_collector.collection_lock:
                    metrics_collector.metrics_history.append(data)
            response = {'success': True, 'message': 'Refreshed'}
        except Exception as e:
            response = {'success': False, 'message': str(e)}
        self.wfile.write(json.dumps(response).encode())

    def _tail_file(self, filepath, num_lines):
        try:
            result = subprocess.run(['sudo', 'tail', '-n', str(num_lines), filepath], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Failed to tail file {filepath}: {result.stderr}")
                return ''
        except Exception as e:
            logger.error(f"Error tailing file {filepath}: {str(e)}")
            return ''

    def _handle_metrics_history(self, query_params):
        if not self.check_auth():
            self._send_unauthorized()
            return
        self.send_response(200)
        self._set_common_headers()
        try:
            minutes = int(query_params.get('minutes', ['60'])[0])
        except Exception:
            minutes = 60
        
        # Get metrics from database
        metrics_list = metrics_collector.get_metrics_history(minutes)
        
        response = {
            'metrics': metrics_list,
            'collection_status': {
                'active': metrics_collector.is_collecting,
                'interval': int(metrics_collector.collection_interval),
                'total_points': len(metrics_list)
            },
            'database_info': {
                'source': 'database',
                'persistent': True,
                'survives_restart': True
            }
        }
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_database_stats(self):
        """Handle database statistics endpoint"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            db_stats = metrics_db.get_database_stats()
            response = {
                'success': True,
                'database_stats': db_stats,
                'collection_stats': metrics_collector.get_stats(),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'persistence_info': {
                    'survives_power_cycle': True,
                    'survives_restart': True,
                    'storage_type': 'SQLite',
                    'file_path': metrics_db.db_path,
                    'auto_cleanup': True,
                    'cleanup_interval_days': 30
                }
            }
        except Exception as e:
            response = {
                'success': False,
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_service_restart_info(self):
        """Handle service restart info"""
        if self.command == 'GET':
            self.send_response(200)
            self._set_common_headers()
            
            response = {
                "endpoint": "/api/service/restart",
                "description": "Safe service restart endpoint",
                "methods": {
                    "GET": "Get endpoint information",
                    "POST": "Execute safe service restart"
                },
                "safety_features": [
                    "No system shutdown/restart",
                    "Service restart only",
                    "Multiple fallback methods",
                    "Graceful process handling"
                ],
                "available_methods": [
                    "systemctl restart",
                    "service restart", 
                    "docker restart",
                    "process restart (kill + start)"
                ],
                "usage": {
                    "method": "POST",
                    "headers": "Authorization: Bearer <token>",
                    "body": "{} (no body required)"
                },
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self._send_method_not_allowed(["GET"])
    
    def _handle_service_manage_info(self):
        """Handle service manage info"""
        if self.command == 'GET':
            self.send_response(200)
            self._set_common_headers()
            
            response = {
                "endpoint": "/api/service/manage",
                "description": "Service management endpoint",
                "methods": {
                    "GET": "Get endpoint information",
                    "POST": "Execute service management actions"
                },
                "available_actions": ["start", "stop", "status"],
                "safety_features": [
                    "Service-level operations only",
                    "No system impact",
                    "Standard systemctl/service commands"
                ],
                "usage": {
                    "method": "POST",
                    "headers": "Authorization: Bearer <token>",
                    "body": '{"action": "start|stop|status"}'
                },
                "examples": {
                    "start": '{"action": "start"}',
                    "stop": '{"action": "stop"}',
                    "status": '{"action": "status"}'
                },
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self._send_method_not_allowed(["GET"])
    
    def _handle_service_info(self):
        """Handle service info"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            # Get service management information
            service_info = self._get_service_management_info()
            response = {
                "success": True,
                "service_management": service_info,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "endpoint_info": {
                    "description": "Service management information and recommendations",
                    "available_endpoints": [
                        "/api/service/restart - Safe service restart",
                        "/api/service/manage - Service start/stop/status",
                        "/api/service/info - Service management info"
                    ]
                }
            }
            
        except Exception as e:
            response = {"success": False, "message": f"Failed to get service info: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_404(self):
        """Handle 404 errors"""
        self.send_response(404)
        self._set_common_headers()
        response = {"error": "Not found"}
        self.wfile.write(json.dumps(response).encode())
    
    def _set_common_headers(self):
        """Set common response headers"""
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()
    
    def _send_unauthorized(self):
        """Send unauthorized response"""
        self.send_response(401)
        self._set_common_headers()
        response = {"error": "Unauthorized"}
        self.wfile.write(json.dumps(response).encode())
    
    def _send_not_found(self, message):
        """Send not found response"""
        self.send_response(404)
        self._set_common_headers()
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode())
    
    def _send_bad_request(self, message):
        """Send bad request response"""
        self.send_response(400)
        self._set_common_headers()
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode())
    
    def _send_internal_error(self, message):
        """Send internal error response"""
        self.send_response(500)
        self._set_common_headers()
        response = {"error": message}
        self.wfile.write(json.dumps(response).encode())
    
    def _send_method_not_allowed(self, allowed_methods):
        """Send method not allowed response"""
        self.send_response(405)
        self._set_common_headers()
        response = {"error": "Method not allowed", "allowed_methods": allowed_methods}
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests with connection pooling and rate limiting"""
        if not connection_pool.acquire_connection():
            self.send_response(503)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"error": "Service temporarily unavailable - too many connections"}
            self.wfile.write(json.dumps(response).encode())
            return
        
        try:
            self._handle_post_request()
        finally:
            connection_pool.release_connection()
    
    @monitor_performance
    def _handle_post_request(self):
        """Handle POST request logic"""
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
        elif path == '/api/service/restart':
            self._handle_service_restart_post()
        elif path == '/api/service/manage':
            self._handle_service_manage_post()
        elif path == '/api/service/info':
            self._handle_service_info_post()
        else:
            self._handle_404()
    
    def _handle_auth(self):
        """Handle authentication with improved security"""
        self.send_response(200)
        self._set_common_headers()
        
        response = self.handle_auth()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_services_post(self):
        """Handle services POST with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        response = self.handle_service_action()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_status_get(self):
        """Handle GET request for power status"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            # Get current power status with permission info
            shutdown_perms = self._check_shutdown_permissions()
            restart_perms = self._check_restart_permissions()
            
            # Get current uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_formatted = f"{uptime_hours}h {uptime_minutes}m"
            
            response = {
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
                "platform": platform.system(),
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Failed to get power status: {e}")
            response = {"success": False, "message": f"Failed to get power status: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_action(self):
        """Handle power management actions with improved error handling"""
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
                    shutdown_result = self._execute_shutdown()
                    if shutdown_result['success']:
                        return {
                            "success": True, 
                            "message": shutdown_result['message'],
                            "action": "shutdown",
                            "command_used": shutdown_result['command_used'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    else:
                        return {
                            "success": False, 
                            "message": f"Shutdown failed: {shutdown_result.get('error', 'Unknown error')}",
                            "action": "shutdown",
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    
                elif action == 'restart':
                    restart_result = self._execute_restart()
                    if restart_result['success']:
                        return {
                            "success": True, 
                            "message": restart_result['message'],
                            "action": "restart",
                            "command_used": restart_result['command_used'],
                            "current_uptime": uptime_formatted,
                            "platform": platform.system()
                        }
                    else:
                        return {
                            "success": False, 
                            "message": f"Restart failed: {restart_result.get('error', 'Unknown error')}",
                            "action": "restart",
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
                    return {"success": False, "message": f"Unknown action: {action}"}
            else:
                return {"success": False, "message": "No data received"}
        except Exception as e:
            logger.error(f"Power action failed: {e}")
            return {"success": False, "message": f"Power action failed: {str(e)}"}
    
    def _handle_power_shutdown(self):
        """Handle power shutdown with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            shutdown_result = self._execute_shutdown()
            if shutdown_result['success']:
                response = {
                    "success": True,
                    "message": shutdown_result['message'],
                    "action": "shutdown",
                    "command_used": shutdown_result['command_used'],
                    "platform": platform.system()
                }
            else:
                response = {
                    "success": False,
                    "message": f"Shutdown failed: {shutdown_result.get('error', 'Unknown error')}",
                    "action": "shutdown"
                }
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            response = {"success": False, "message": f"Shutdown failed: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_restart(self):
        """Handle power restart with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            restart_result = self._execute_restart()
            if restart_result['success']:
                response = {
                    "success": True,
                    "message": restart_result['message'],
                    "action": "restart",
                    "command_used": restart_result['command_used'],
                    "platform": platform.system()
                }
            else:
                response = {
                    "success": False,
                    "message": f"Restart failed: {restart_result.get('error', 'Unknown error')}",
                    "action": "restart"
                }
        except Exception as e:
            logger.error(f"Restart failed: {e}")
            response = {"success": False, "message": f"Restart failed: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_power_sleep(self):
        """Handle power sleep with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
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
            logger.error(f"Sleep failed: {e}")
            response = {"success": False, "message": f"Sleep failed: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_service_restart_post(self):
        """Handle service restart POST with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            # Use the safe service restart method
            restart_result = self._safe_restart_pi_monitor_service()
            response = {
                "success": restart_result['success'],
                "message": restart_result.get('message', ''),
                "method": restart_result.get('method', ''),
                "command_used": restart_result.get('command_used', ''),
                "safety_level": restart_result.get('safety_level', ''),
                "description": restart_result.get('description', ''),
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if not restart_result['success']:
                response["error"] = restart_result.get('error', '')
                response["methods_tried"] = restart_result.get('methods_tried', [])
                response["suggestions"] = restart_result.get('suggestions', [])
                
        except Exception as e:
            logger.error(f"Service restart failed: {e}")
            response = {"success": False, "message": f"Service restart failed: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_service_manage_post(self):
        """Handle service manage POST with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            # Get action from POST data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                action = data.get('action', 'status')
            else:
                action = 'status'
            
            # Use the safe service management method
            manage_result = self._safe_manage_pi_monitor_service(action)
            response = {
                "success": manage_result['success'],
                "action": manage_result.get('action', ''),
                "message": manage_result.get('message', ''),
                "method": manage_result.get('method', ''),
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if manage_result['success'] and action == 'status':
                response["status"] = manage_result.get('status', '')
                response["detailed_status"] = manage_result.get('detailed_status', '')
            elif not manage_result['success']:
                response["error"] = manage_result.get('error', '')
                response["available_actions"] = manage_result.get('available_actions', [])
                
        except Exception as e:
            logger.error(f"Service management failed: {e}")
            response = {"success": False, "message": f"Service management failed: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_service_info_post(self):
        """Handle service info POST with improved error handling"""
        if not self.check_auth():
            self._send_unauthorized()
            return
        
        self.send_response(200)
        self._set_common_headers()
        
        try:
            # Get service management information
            service_info = self._get_service_management_info()
            response = {
                "success": True,
                "service_management": service_info,
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "endpoint_info": {
                    "description": "Service management information and recommendations",
                    "available_endpoints": [
                        "/api/service/restart - Safe service restart",
                        "/api/service/manage - Service start/stop/status",
                        "/api/service/info - Service management info"
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get service info: {e}")
            response = {"success": False, "message": f"Failed to get service info: {str(e)}"}
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight with improved headers"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Set CORS headers for preflight
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')  # Cache preflight for 24 hours
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
    
    def check_auth(self):
        """Simple API key authentication check"""
        auth_header = self.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        api_key = auth_header.split(' ')[1]
        
        # Check if API key matches
        return api_key == API_KEY
    
    def handle_auth(self):
        """Handle API key validation"""
        # Get content length from headers
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            # Read POST data
            post_data = self.rfile.read(content_length)
            try:
                # Parse JSON data
                auth_data = json.loads(post_data.decode('utf-8'))
                api_key = auth_data.get('api_key', '')
                
                # Check API key
                if api_key == API_KEY:
                    # Authentication successful
                    logger.info("API key authentication successful")
                    
                    return {
                        "success": True,
                        "message": "API key authentication successful",
                        "auth_method": "api_key"
                    }
                else:
                    # Authentication failed
                    logger.warning("API key authentication failed")
                    return {
                        "error": "Invalid API key",
                        "message": "Authentication failed"
                    }
                    
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Invalid JSON data in auth request: {e}")
                return {
                    "error": "Invalid JSON data",
                    "message": "Request body must be valid JSON"
                }
        else:
            logger.warning("Missing request body in auth request")
            return {
                "error": "Missing request body",
                "message": "API key required"
            }
    
    def generate_api_key(self):
        """Generate a new API key (for admin use)"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @lru_cache(maxsize=128)
    def _get_system_info(self):
        """Get basic system information with caching"""
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
            logger.error(f"Failed to get system info: {e}")
            return {"error": f"Failed to get system info: {str(e)}"}
    
    def _get_uptime(self):
        """Get system uptime with improved error handling"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            return f"{uptime_hours}h {uptime_minutes}m"
        except Exception as e:
            logger.error(f"Failed to get uptime: {e}")
            return {"error": f"Failed to get uptime: {str(e)}"}
    
    def _get_system_stats(self):
        """Get current system statistics (real-time) with improved performance"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get temperature using the global metrics collector
            temperature = self._get_temperature()
            
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
            logger.error(f"Failed to get system stats: {e}")
            return {"timestamp": time.time(), "error": f"Failed to get system stats: {str(e)}"}
    
    def _get_system_stats_with_history(self, minutes):
        """Get system statistics with history for the last N minutes with improved performance"""
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
            logger.error(f"Failed to get historical system stats: {e}")
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
            logger.error(f"Failed to get enhanced system stats: {e}")
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
    
    def _get_temperature(self):
        """Get system temperature using multiple methods with improved error handling"""
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
                
        except Exception as e:
            logger.error(f"Failed to get temperature: {e}")
        
        # Return a safe default value if all methods fail
        return 25.0  # Room temperature as safe default
    
    def handle_service_action(self):
        """Handle service control actions with improved error handling"""
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
            logger.error(f"Service action failed: {e}")
            return {"success": False, "message": f"Service action failed: {str(e)}"}
    
    def _check_shutdown_permissions(self):
        """Check if current user can execute shutdown commands with improved error handling"""
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
                logger.info(f"Checking shutdown permissions for user: {current_user}")
                
                # Check if running as root
                try:
                    if os.geteuid() == 0:
                        logger.info("Running as root user - shutdown allowed")
                        return {
                            'can_shutdown': True,
                            'method': 'root',
                            'reason': 'Running as root user',
                            'suggestions': []
                        }
                except AttributeError:
                    logger.info("geteuid not available on this platform")
                
                # Check if user can use sudo without password for shutdown commands
                sudo_check = self._check_sudo_permissions()
                if sudo_check['can_sudo']:
                    logger.info(f"User {current_user} can use sudo for shutdown")
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
                        logger.info(f"User {current_user} in sudo group but may need password")
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
                except Exception as e:
                    logger.error(f"Error checking groups: {str(e)}")
                
                # Check if shutdown commands are available in PATH
                shutdown_available = self._check_command_availability(['shutdown', 'poweroff', 'halt'])
                if shutdown_available:
                    logger.info(f"Shutdown commands available but user {current_user} lacks permissions")
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
                    logger.info(f"Shutdown commands not available for user {current_user}")
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
            logger.error(f"Error checking shutdown permissions: {str(e)}")
            return {
                'can_shutdown': False,
                'method': 'error',
                'reason': f'Error checking permissions: {str(e)}',
                'suggestions': ['Check system configuration and try again']
            }
    
    def _check_restart_permissions(self):
        """Check if current user can execute restart commands with improved error handling"""
        try:
            if platform.system() == 'Windows':
                # Same as shutdown for Windows
                return self._check_shutdown_permissions()
            else:
                # Linux/Raspberry Pi permission checking
                current_user = os.getenv('USER', 'unknown')
                logger.info(f"Checking restart permissions for user: {current_user}")
                
                # Check if running as root
                try:
                    if os.geteuid() == 0:
                        logger.info("Running as root user - restart allowed")
                        return {
                            'can_restart': True,
                            'method': 'root',
                            'reason': 'Running as root user',
                            'suggestions': []
                        }
                except AttributeError:
                    logger.info("geteuid not available on this platform")
                
                # Check if user can use sudo without password for restart commands
                sudo_check = self._check_sudo_permissions()
                if sudo_check['can_sudo']:
                    logger.info(f"User {current_user} can use sudo for restart")
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
                        logger.info(f"User {current_user} in sudo group but may need password")
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
                except Exception as e:
                    logger.error(f"Error checking groups: {str(e)}")
                
                # Check if restart commands are available in PATH
                restart_available = self._check_command_availability(['reboot', 'shutdown', 'systemctl'])
                if restart_available:
                    logger.info(f"Restart commands available but user {current_user} lacks permissions")
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
                    logger.info(f"Restart commands not available for user {current_user}")
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
            logger.error(f"Error checking restart permissions: {str(e)}")
            return {
                'can_restart': False,
                'method': 'error',
                'reason': f'Error checking permissions: {str(e)}',
                'suggestions': ['Check system configuration and try again']
            }
    
    def _check_sudo_permissions(self):
        """Check if current user can use sudo without password for shutdown/restart commands"""
        try:
            logger.info("Testing sudo permissions for shutdown/restart commands...")
            
            # Test if user can run shutdown command with sudo without password
            test_commands = [
                ['sudo', '-n', 'shutdown', '--help'],
                ['sudo', '-n', 'poweroff', '--help'],
                ['sudo', '-n', 'reboot', '--help']
            ]
            
            for cmd in test_commands:
                try:
                    logger.info(f"Testing sudo command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        logger.info(f"Sudo command successful: {' '.join(cmd)}")
                        return {
                            'can_sudo': True,
                            'command': ' '.join(cmd),
                            'reason': 'Sudo command executed successfully without password'
                        }
                    else:
                        logger.info(f"Sudo command failed: {' '.join(cmd)} - return code: {result.returncode}")
                        if result.stderr:
                            logger.info(f"Error output: {result.stderr.strip()}")
                except subprocess.TimeoutExpired:
                    logger.info(f"Sudo command timed out: {' '.join(cmd)}")
                except Exception as e:
                    logger.info(f"Exception testing sudo command {' '.join(cmd)}: {str(e)}")
                    continue
            
            logger.info("No sudo commands worked without password")
            return {
                'can_sudo': False,
                'command': None,
                'reason': 'No sudo commands worked without password'
            }
            
        except Exception as e:
            logger.error(f"Error testing sudo: {str(e)}")
            return {
                'can_sudo': False,
                'command': None,
                'reason': f'Error testing sudo: {str(e)}'
            }
    
    def _check_command_availability(self, commands):
        """Check if specified commands are available in PATH"""
        available_commands = []
        logger.info(f"Checking command availability for: {commands}")
        
        for cmd in commands:
            try:
                result = subprocess.run(['which', cmd], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    available_commands.append(cmd)
                    logger.info(f"  ✅ {cmd}: {result.stdout.strip()}")
                else:
                    logger.info(f"  ❌ {cmd}: Not found in PATH")
            except subprocess.TimeoutExpired:
                logger.info(f"  ⏰ {cmd}: Timeout checking availability")
            except Exception as e:
                logger.info(f"  💥 {cmd}: Error checking availability - {str(e)}")
        
        logger.info(f"Available commands: {available_commands}")
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
                cmd = ['sudo', 'shutdown', '-h', 'now']
                try:
                    subprocess.run(cmd, timeout=15)
                    logger.info(f"Shutdown command executed: {' '.join(cmd)}")
                    return {
                        'success': True,
                        'message': 'Shutdown initiated',
                        'command_used': ' '.join(cmd)
                    }
                except subprocess.TimeoutExpired:
                    logger.info(f"Shutdown command timed out (expected): {' '.join(cmd)}")
                    return {
                        'success': True,
                        'message': 'Shutdown initiated (timeout expected)',
                        'command_used': ' '.join(cmd)
                    }
                except Exception as e:
                    logger.error(f"Shutdown failed: {str(e)}")
                    return {
                        'success': False,
                        'error': str(e),
                        'command_used': ' '.join(cmd)
                    }
        except Exception as e:
            logger.error(f"Shutdown execution error: {str(e)}")
            return {
                'success': False,
                'error': f'Shutdown execution error: {str(e)}',
                'command_used': 'error'
            }
    
    def _execute_restart(self):
        """Execute restart command using simple, reliable methods"""
        try:
            logger.info("🔄 Attempting system restart...")
            cmd = ['sudo', 'reboot']
            try:
                subprocess.run(cmd, timeout=15)
                logger.info(f"Restart command executed: {' '.join(cmd)}")
                return {
                    'success': True,
                    'message': 'Restart initiated',
                    'command_used': ' '.join(cmd)
                }
            except subprocess.TimeoutExpired:
                logger.info(f"Restart command timed out (expected): {' '.join(cmd)}")
                return {
                    'success': True,
                    'message': 'Restart initiated (timeout expected)',
                    'command_used': ' '.join(cmd)
                }
            except Exception as e:
                logger.error(f"Restart failed: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'command_used': ' '.join(cmd)
                }
        except Exception as e:
            logger.error(f"Restart execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'command_used': 'error'
            }
    
    def _safe_restart_pi_monitor_service(self):
        """Safely restart the pi-monitor service without system restart"""
        try:
            logger.info("🔄 Attempting safe restart of pi-monitor service...")
            
            # Method 1: Try systemctl first (most reliable)
            try:
                logger.info("  🔧 Trying systemctl restart...")
                result = subprocess.run(['systemctl', 'restart', 'pi-monitor'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("  ✅ systemctl restart successful")
                    return {
                        'success': True,
                        'message': 'Pi-monitor service restarted successfully using systemctl',
                        'method': 'systemctl',
                        'command_used': 'systemctl restart pi-monitor',
                        'safety_level': 'high',
                        'description': 'Service restart only - no system impact'
                    }
                else:
                    logger.info(f"  ❌ systemctl restart failed: {result.stderr}")
            except Exception as e:
                logger.info(f"  ❌ systemctl restart exception: {str(e)}")
            
            # Method 2: Try service command (fallback)
            try:
                logger.info("  🔧 Trying service restart...")
                result = subprocess.run(['service', 'pi-monitor', 'restart'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("  ✅ service restart successful")
                    return {
                        'success': True,
                        'message': 'Pi-monitor service restarted successfully using service command',
                        'method': 'service',
                        'command_used': 'service pi-monitor restart',
                        'safety_level': 'high',
                        'description': 'Service restart only - no system impact'
                    }
                else:
                    logger.info(f"  ❌ service restart failed: {result.stderr}")
            except Exception as e:
                logger.info(f"  ❌ service restart exception: {str(e)}")
            
            # Method 3: Try Docker restart if running in container
            try:
                logger.info("  🔧 Trying Docker restart...")
                result = subprocess.run(['docker', 'restart', 'pi-monitor'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("  ✅ Docker restart successful")
                    return {
                        'success': True,
                        'message': 'Pi-monitor container restarted successfully using Docker',
                        'method': 'docker',
                        'command_used': 'docker restart pi-monitor',
                        'safety_level': 'high',
                        'description': 'Container restart only - no system impact'
                    }
                else:
                    logger.info(f"  ❌ Docker restart failed: {result.stderr}")
            except Exception as e:
                logger.info(f"  ❌ Docker restart exception: {str(e)}")
            
            # Method 4: Try process restart (kill and restart)
            try:
                logger.info("  🔧 Trying process restart...")
                # Find pi-monitor processes
                result = subprocess.run(['pgrep', '-f', 'pi-monitor'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    logger.info(f"  📍 Found {len(pids)} pi-monitor processes: {pids}")
                    
                    # Kill processes gracefully
                    for pid in pids:
                        if pid.strip():
                            try:
                                subprocess.run(['kill', '-TERM', pid.strip()], 
                                             capture_output=True, timeout=5)
                                logger.info(f"  🛑 Sent TERM signal to PID {pid}")
                            except Exception as e:
                                logger.info(f"  ❌ Failed to kill PID {pid}: {str(e)}")
                    
                    # Wait a moment for graceful shutdown
                    time.sleep(2)
                    
                    # Try to start the service again
                    start_result = subprocess.run(['systemctl', 'start', 'pi-monitor'], 
                                                capture_output=True, text=True, timeout=30)
                    if start_result.returncode == 0:
                        logger.info("  ✅ Process restart successful")
                        return {
                            'success': True,
                            'message': 'Pi-monitor service restarted successfully using process restart',
                            'method': 'process_restart',
                            'command_used': f'kill -TERM {len(pids)} processes + systemctl start',
                            'safety_level': 'medium',
                            'description': 'Process restart - minimal system impact'
                        }
                    else:
                        logger.info(f"  ❌ Process restart failed: {start_result.stderr}")
                else:
                    logger.info("  ❌ No pi-monitor processes found")
            except Exception as e:
                logger.info(f"  ❌ Process restart exception: {str(e)}")
            
            # If all methods failed
            logger.error("  ❌ All safe restart methods failed")
            return {
                'success': False,
                'error': 'All safe restart methods failed',
                'methods_tried': ['systemctl', 'service', 'docker', 'process_restart'],
                'suggestions': [
                    'Check if pi-monitor service is properly configured',
                    'Verify systemctl/service commands are available',
                    'Check Docker if running in container',
                    'Review system logs for errors',
                    'Consider manual restart as last resort'
                ],
                'safety_level': 'high',
                'description': 'No restart attempted - system remains stable'
            }
            
        except Exception as e:
            logger.error(f"❌ Safe restart error: {str(e)}")
            return {
                'success': False,
                'error': f'Safe restart error: {str(e)}',
                'safety_level': 'high',
                'description': 'Exception occurred - no restart attempted'
            }
    
    def _safe_manage_pi_monitor_service(self, action):
        """Safely manage the pi-monitor service (start/stop/status)"""
        try:
            logger.info(f"🔧 Attempting {action} of pi-monitor service...")
            
            if action == 'start':
                # Try to start the service
                try:
                    result = subprocess.run(['systemctl', 'start', 'pi-monitor'], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': 'Pi-monitor service started successfully',
                            'method': 'systemctl',
                            'action': 'start'
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'Failed to start service: {result.stderr}',
                            'action': 'start'
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Exception starting service: {str(e)}',
                        'action': 'start'
                    }
                    
            elif action == 'stop':
                # Try to stop the service
                try:
                    result = subprocess.run(['systemctl', 'stop', 'pi-monitor'], 
                                          capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        return {
                            'success': True,
                            'message': 'Pi-monitor service stopped successfully',
                            'method': 'systemctl',
                            'action': 'stop'
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'Failed to stop service: {result.stderr}',
                            'action': 'stop'
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Exception stopping service: {str(e)}',
                        'action': 'stop'
                    }
                    
            elif action == 'status':
                # Check service status
                try:
                    result = subprocess.run(['systemctl', 'is-active', 'pi-monitor'], 
                                          capture_output=True, text=True, timeout=10)
                    status = result.stdout.strip() if result.returncode == 0 else 'unknown'
                    
                    # Get more detailed status
                    detailed_result = subprocess.run(['systemctl', 'status', 'pi-monitor', '--no-pager'], 
                                                  capture_output=True, text=True, timeout=15)
                    detailed_status = detailed_result.stdout if detailed_result.returncode == 0 else 'Status unavailable'
                    
                    return {
                        'success': True,
                        'status': status,
                        'detailed_status': detailed_status,
                        'action': 'status'
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Exception checking status: {str(e)}',
                        'action': 'status'
                    }
                    
            else:
                return {
                    'success': False,
                    'error': f'Unknown action: {action}',
                    'available_actions': ['start', 'stop', 'status']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Service management error: {str(e)}',
                'action': action
            }
    
    def _get_service_management_info(self):
        """Get information about available service management methods"""
        try:
            info = {
                'available_methods': [],
                'systemctl_available': False,
                'service_available': False,
                'docker_available': False,
                'recommendations': []
            }
            
            # Check systemctl availability
            try:
                result = subprocess.run(['systemctl', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['systemctl_available'] = True
                    info['available_methods'].append('systemctl')
                    info['recommendations'].append('Use systemctl for service management (most reliable)')
            except:
                pass
            
            # Check service command availability
            try:
                result = subprocess.run(['service', '--help'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['service_available'] = True
                    info['available_methods'].append('service')
                    info['recommendations'].append('Use service command as fallback')
            except:
                pass
            
            # Check Docker availability
            try:
                result = subprocess.run(['docker', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info['docker_available'] = True
                    info['available_methods'].append('docker')
                    info['recommendations'].append('Use Docker commands if running in container')
            except:
                pass
            
            # Add safety recommendations
            info['safety_recommendations'] = [
                'Service restart is safer than system restart',
                'Use systemctl/service commands when possible',
                'Avoid direct shutdown/reboot commands',
                'Monitor service logs for issues'
            ]
            
            return info
            
        except Exception as e:
            return {
                'error': f'Failed to get service management info: {str(e)}'
            }
    
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

# Database management for persistent storage
class MetricsDatabase:
    def __init__(self, db_path='pi_monitor.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create metrics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL NOT NULL,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_percent REAL,
                        temperature REAL,
                        network_bytes_sent INTEGER,
                        network_bytes_recv INTEGER,
                        network_packets_sent INTEGER,
                        network_packets_recv INTEGER,
                        disk_read_bytes INTEGER,
                        disk_write_bytes INTEGER,
                        disk_read_count INTEGER,
                        disk_write_count INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON metrics(created_at)')
                
                # Create system info table for persistent system information
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE NOT NULL,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info(f"Database initialized successfully: {self.db_path}")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def insert_metrics(self, metrics_data):
        """Insert metrics data into database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO metrics (
                        timestamp, cpu_percent, memory_percent, disk_percent, temperature,
                        network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                        disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics_data.get('timestamp', time.time()),
                    metrics_data.get('cpu_percent'),
                    metrics_data.get('memory_percent'),
                    metrics_data.get('disk_percent'),
                    metrics_data.get('temperature'),
                    metrics_data.get('network', {}).get('bytes_sent', 0),
                    metrics_data.get('network', {}).get('bytes_recv', 0),
                    metrics_data.get('network', {}).get('packets_sent', 0),
                    metrics_data.get('network', {}).get('packets_recv', 0),
                    metrics_data.get('disk_io', {}).get('read_bytes', 0),
                    metrics_data.get('disk_io', {}).get('write_bytes', 0),
                    metrics_data.get('disk_io', {}).get('read_count', 0),
                    metrics_data.get('disk_io', {}).get('write_count', 0)
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert metrics: {e}")
            return False
    
    def get_metrics_history(self, minutes=60, limit=1000):
        """Get metrics history from database for the last N minutes"""
        try:
            cutoff_time = time.time() - (minutes * 60)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, temperature,
                           network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                           disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    FROM metrics 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (cutoff_time, limit))
                
                rows = cursor.fetchall()
                
                # Convert to the format expected by frontend
                metrics = []
                for row in rows:
                    metrics.append({
                        'timestamp': row[0],
                        'cpu_percent': row[1],
                        'memory_percent': row[2],
                        'disk_percent': row[3],
                        'temperature': row[4],
                        'network': {
                            'bytes_sent': row[5],
                            'bytes_recv': row[6],
                            'packets_sent': row[7],
                            'packets_recv': row[8]
                        },
                        'disk_io': {
                            'read_bytes': row[9],
                            'write_bytes': row[10],
                            'read_count': row[11],
                            'write_count': row[12]
                        }
                    })
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep=30):
        """Clean up old metrics data to prevent database bloat"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_time,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} old metrics records")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get total records
                cursor.execute('SELECT COUNT(*) FROM metrics')
                total_records = cursor.fetchone()[0]
                
                # Get oldest and newest timestamps
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM metrics')
                time_range = cursor.fetchone()
                oldest_time = time_range[0] if time_range[0] else None
                newest_time = time_range[1] if time_range[1] else None
                
                # Get database file size
                try:
                    db_size = os.path.getsize(self.db_path)
                except:
                    db_size = 0
                
                return {
                    'total_records': total_records,
                    'oldest_timestamp': oldest_time,
                    'newest_timestamp': newest_time,
                    'database_size_bytes': db_size,
                    'database_size_mb': round(db_size / (1024 * 1024), 2) if db_size else 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

# Global database instance
metrics_db = MetricsDatabase()

def run_server(port=None):
    """Run the enhanced Pi Monitor HTTP server"""
    if port is None:
        port = config.get_port('backend')
    
    # Start metrics collection
    print("Starting metrics collection...")
    metrics_collector.start_collection()
    
    # Start database cleanup task (clean old data every 24 hours)
    def cleanup_database():
        while True:
            try:
                time.sleep(24 * 60 * 60)  # 24 hours
                deleted_count = metrics_db.cleanup_old_data(days_to_keep=30)
                if deleted_count > 0:
                    print(f"🧹 Cleaned up {deleted_count} old metrics records")
            except Exception as e:
                print(f"❌ Database cleanup error: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_database, daemon=True)
    cleanup_thread.start()
    
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
    print(f"💾 Database: {metrics_db.db_path}")
    
    # Get and display database stats
    try:
        db_stats = metrics_db.get_database_stats()
        if db_stats:
            print(f"📊 Database Records: {db_stats.get('total_records', 0)}")
            print(f"💾 Database Size: {db_stats.get('database_size_mb', 0)} MB")
    except Exception as e:
        print(f"❌ Database stats unavailable: {e}")
    print()
    print("🌐 Available Endpoints:")
    endpoints = config.get_backend_endpoints()
    for name, path in endpoints.items():
        print(f"  📍 {name.upper()}: {path}")
    
    # Add new endpoints
    print(f"  📊 METRICS: /api/metrics")
    print(f"  💾 DATABASE: /api/metrics/database")
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
        print("🛑 Shutting down command executor...")
        command_executor.shutdown()
        print("🛑 Shutting down HTTP server...")
        httpd.shutdown()
        print("✅ Server shutdown complete")

if __name__ == '__main__':
    run_server()
