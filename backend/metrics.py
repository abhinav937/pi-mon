#!/usr/bin/env python3
"""
Pi Monitor - Metrics Collection
Handles system metrics gathering, storage, and retrieval
"""

import time
import threading
import logging
from collections import deque
from functools import lru_cache
import os # Added missing import for os

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
        def boot_time():
            return time.time() - 3600  # Default to 1 hour ago
    
    psutil = MinimalPsutil()

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and manages system metrics"""
    
    def __init__(self):
        self.collection_interval = 5.0  # Default 5 seconds
        self.is_collecting = False
        self.collection_thread = None
        self.last_collection = 0
        self.collection_lock = threading.Lock()
        
        # Performance counters
        self.collection_count = 0
        self.error_count = 0
        self.last_error = None
        # Increased max_history to support 24-hour data logging
        # 24 hours * 60 minutes * 60 seconds / 5 second interval = 17,280 data points
        self.max_history = 20000  # Keep last 20,000 data points in memory for 24+ hours
        
        # In-memory cache for recent data
        self.recent_cache = deque(maxlen=self.max_history)
        # Maintain compatibility with any code referencing metrics_history
        self.metrics_history = self.recent_cache
    
    def set_collection_interval(self, interval_seconds):
        """Update the collection interval (in seconds)"""
        try:
            new_interval = float(interval_seconds)
            if new_interval < 1.0:  # Minimum 1 second
                new_interval = 1.0
            elif new_interval > 300.0:  # Maximum 5 minutes
                new_interval = 300.0
                
            with self.collection_lock:
                self.collection_interval = new_interval
                logger.info(f"Metrics collection interval updated to {new_interval} seconds")
            return True
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid interval value: {e}")
            return False
    
    def get_collection_interval(self):
        """Get current collection interval in seconds"""
        return self.collection_interval
    
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
        """Background thread for collecting metrics"""
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
                        # Keep in memory cache for quick access
                        self.recent_cache.append(metrics)
                        # Store in database for persistence
                        from database import MetricsDatabase
                        db = MetricsDatabase()
                        if db.insert_metrics(metrics):
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
        """Gather current system metrics"""
        try:
            # Basic metrics using psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            temperature = self._get_temperature()
            network = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()
            
            return {
                "timestamp": time.time(),
                "cpu_percent": float(cpu_percent),
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
                }
            }
        except Exception as e:
            logger.error(f"Failed to gather metrics: {e}")
            return {"timestamp": time.time(), "error": str(e)}
    
    def _get_temperature(self):
        """Get system temperature using multiple methods"""
        try:
            # Try Raspberry Pi specific path
            if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    temp_raw = f.read().strip()
                    temp_value = float(temp_raw) / 1000.0
                    if temp_value > 0 and temp_value < 200:  # Sanity check
                        return round(temp_value, 1)
            
            # Try other thermal zones
            for i in range(10):
                thermal_path = f'/sys/class/thermal/thermal_zone{i}/temp'
                if os.path.exists(thermal_path):
                    with open(thermal_path, 'r') as f:
                        temp_raw = f.read().strip()
                        temp_value = float(temp_raw) / 1000.0
                        if temp_value > 0 and temp_value < 200:  # Sanity check
                            return round(temp_value, 1)
            
            # Try vcgencmd for Raspberry Pi
            try:
                import subprocess
                result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    import re
                    temp_match = re.search(r'temp=(\d+\.?\d*)', result.stdout)
                    if temp_match:
                        temp_value = float(temp_match.group(1))
                        if temp_value > 0 and temp_value < 200:  # Sanity check
                            return round(temp_value, 1)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Failed to get temperature: {e}")
        
        # Return a safe default value if all methods fail
        return 25.0  # Room temperature as safe default
    
    def get_metrics_history(self, minutes=60):
        """Get metrics history for the last N minutes"""
        try:
            # Try to get from database first
            from database import MetricsDatabase
            db = MetricsDatabase()
            db_metrics = db.get_metrics_history(minutes)
            if db_metrics:
                logger.info(f"Retrieved {len(db_metrics)} metrics from database")
                return db_metrics

            # Fallback to memory cache if database fails
            logger.info("Database retrieval failed, falling back to memory cache")
            cutoff_time = time.time() - (minutes * 60)
            with self.collection_lock:
                memory_metrics = [m for m in self.recent_cache if m.get('timestamp', 0) > cutoff_time]
                logger.info(f"Retrieved {len(memory_metrics)} metrics from memory cache")
                return memory_metrics
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            # Final fallback to memory cache
            cutoff_time = time.time() - (minutes * 60)
            with self.collection_lock:
                fallback_metrics = [m for m in self.recent_cache if m.get('timestamp', 0) > cutoff_time]
                logger.info(f"Final fallback: retrieved {len(fallback_metrics)} metrics from memory cache")
                return fallback_metrics
    
    def get_metrics_history_formatted(self, minutes=60, include_date=True):
        """Get metrics history with formatted timestamps"""
        metrics_list = self.get_metrics_history(minutes)
        
        # Enhance with formatted timestamps if requested
        enhanced_metrics = []
        for metric in metrics_list:
            timestamp = metric['timestamp']
            if include_date:
                formatted_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
            else:
                formatted_time = time.strftime('%H:%M:%S', time.localtime(timestamp))
            enhanced_metric = {**metric, 'formatted_time': formatted_time}
            enhanced_metrics.append(enhanced_metric)
        
        response = {
            'metrics': enhanced_metrics,
            'collection_status': {
                'active': self.is_collecting,
                'interval': int(self.collection_interval),
                'total_points': len(enhanced_metrics)
            },
            'database_info': {
                'source': 'database',
                'persistent': True,
                'survives_restart': True,
                'formatted': include_date
            }
        }
        
        return response
    
    def get_latest_metrics(self):
        """Get the most recent metrics"""
        try:
            # Try memory cache first for speed
            if self.recent_cache:
                return self.recent_cache[-1]
            
            # Fallback to database
            from database import MetricsDatabase
            db = MetricsDatabase()
            db_metrics = db.get_metrics_history(1, 1)  # Last 1 minute, 1 record
            return db_metrics[0] if db_metrics else None
        except Exception as e:
            logger.error(f"Failed to get latest metrics: {e}")
            return None
    
    def refresh(self):
        """Invalidate caches and trigger an immediate metrics sample"""
        try:
            # Force an immediate metrics read and append to history
            data = self._gather_current_metrics()
            if data and 'error' not in data:
                with self.collection_lock:
                    self.recent_cache.append(data)
            return {'success': True, 'message': 'Refreshed'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_stats(self):
        """Get collection statistics"""
        try:
            from database import MetricsDatabase
            db = MetricsDatabase()
            db_stats = db.get_database_stats()
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
