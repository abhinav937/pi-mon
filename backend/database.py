#!/usr/bin/env python3
"""
Pi Monitor - Database Management
Handles SQLite database operations for metrics storage
"""

import sqlite3
import os
import time
import logging
import math

logger = logging.getLogger(__name__)

class MetricsDatabase:
    """SQLite database for storing metrics data"""
    
    def __init__(self, db_path=None):
        if db_path is None:
            # Use absolute path in backend directory to prevent database resets
            import os
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            self.db_path = os.path.join(backend_dir, 'pi_monitor.db')
        else:
            self.db_path = db_path
        self.init_database()
    
    def _connect(self):
        """Create a SQLite connection with performance PRAGMAs enabled."""
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        try:
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA synchronous=NORMAL;')
            conn.execute('PRAGMA busy_timeout=5000;')
            conn.execute('PRAGMA temp_store=MEMORY;')
            conn.execute('PRAGMA cache_size=-20000;')  # ~20MB
            conn.execute('PRAGMA mmap_size=268435456;')  # 256MB
            conn.execute('PRAGMA foreign_keys=ON;')
        except Exception:
            pass
        return conn
    
    def init_database(self):
        """Initialize the database with required tables"""
        try:
            with self._connect() as conn:
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
                        voltage REAL,
                        core_current REAL,
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
            with self._connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO metrics (
                        timestamp, cpu_percent, memory_percent, disk_percent, temperature, voltage, core_current,
                        network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                        disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics_data.get('timestamp', time.time()),
                    metrics_data.get('cpu_percent'),
                    metrics_data.get('memory_percent'),
                    metrics_data.get('disk_percent'),
                    metrics_data.get('temperature'),
                    metrics_data.get('voltage'),
                    metrics_data.get('core_current'),
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
        """Get metrics history from database for the last N minutes.

        Returns the most recent points within the time window, ensuring latest data is included.
        """
        try:
            cutoff_time = time.time() - (minutes * 60)
            
            logger.info(f"Database query: minutes={minutes}, cutoff_time={cutoff_time}, limit={limit}")

            # Try to approximate the needed number of points based on stored collection interval
            try:
                from database import MetricsDatabase  # local import safe here
                # We are already inside MetricsDatabase; use self
                stored_interval = self.get_system_info('collection_interval_seconds')
                interval_seconds = float(stored_interval) if stored_interval is not None else 5.0
                if interval_seconds <= 0:
                    interval_seconds = 5.0
            except Exception:
                interval_seconds = 5.0

            estimated_points = int(math.ceil((minutes * 60.0) / interval_seconds))
            # Add a small buffer and cap
            desired_points = min(estimated_points + 50, 50000)
            # Ensure we request at least the caller-provided limit
            effective_limit = max(int(limit), desired_points)
            
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Fetch the most recent points within the window, then reverse to ascending for the frontend
                cursor.execute('''
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, temperature, voltage, core_current,
                           network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                           disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    FROM metrics 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (cutoff_time, effective_limit))
                
                rows_desc = cursor.fetchall()
                rows = list(reversed(rows_desc))
                logger.info(f"Database returned {len(rows)} rows (requested: {effective_limit}, interval={interval_seconds}s)")
                
                # Convert to the format expected by frontend
                metrics = []
                for row in rows:
                    metrics.append({
                        'timestamp': row[0],
                        'cpu_percent': row[1],
                        'memory_percent': row[2],
                        'disk_percent': row[3],
                        'temperature': row[4],
                        'voltage': row[5],
                        'core_current': row[6],
                        'network': {
                            'bytes_sent': row[7],
                            'bytes_recv': row[8],
                            'packets_sent': row[9],
                            'packets_recv': row[10]
                        },
                        'disk_io': {
                            'read_bytes': row[11],
                            'write_bytes': row[12],
                            'read_count': row[13],
                            'write_count': row[14]
                        }
                    })
                
                logger.info(f"Converted {len(metrics)} metrics for frontend")
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    def get_metrics_range(self, start_ts, end_ts, limit=None, offset=None):
        """Get metrics between start_ts and end_ts (inclusive start, exclusive end)."""
        try:
            params = [float(start_ts), float(end_ts)]
            limit_clause = ''
            if limit is not None:
                limit_clause = ' LIMIT ?'
                params.append(int(limit))
                if offset is not None:
                    limit_clause += ' OFFSET ?'
                    params.append(int(offset))
            with self._connect() as conn:
                cursor = conn.cursor()
                query = f'''
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, temperature, voltage, core_current,
                           network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                           disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    FROM metrics
                    WHERE timestamp >= ? AND timestamp < ?
                    ORDER BY timestamp ASC{limit_clause}
                '''
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                metrics = []
                for row in rows:
                    metrics.append({
                        'timestamp': row[0],
                        'cpu_percent': row[1],
                        'memory_percent': row[2],
                        'disk_percent': row[3],
                        'temperature': row[4],
                        'voltage': row[5],
                        'core_current': row[6],
                        'network': {
                            'bytes_sent': row[7],
                            'bytes_recv': row[8],
                            'packets_sent': row[9],
                            'packets_recv': row[10]
                        },
                        'disk_io': {
                            'read_bytes': row[11],
                            'write_bytes': row[12],
                            'read_count': row[13],
                            'write_count': row[14]
                        }
                    })
                return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics range: {e}")
            return []
    
    def get_latest(self, limit=1):
        """Return the most recent N metrics rows in ascending timestamp order."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, temperature, voltage, core_current,
                           network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                           disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    FROM metrics
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (int(limit),))
                rows = cursor.fetchall()
                metrics = []
                for row in rows:
                    metrics.append({
                        'timestamp': row[0],
                        'cpu_percent': row[1],
                        'memory_percent': row[2],
                        'disk_percent': row[3],
                        'temperature': row[4],
                        'voltage': row[5],
                        'core_current': row[6],
                        'network': {
                            'bytes_sent': row[7],
                            'bytes_recv': row[8],
                            'packets_sent': row[9],
                            'packets_recv': row[10]
                        },
                        'disk_io': {
                            'read_bytes': row[11],
                            'write_bytes': row[12],
                            'read_count': row[13],
                            'write_count': row[14]
                        }
                    })
                return list(reversed(metrics))
        except Exception as e:
            logger.error(f"Failed to get latest metrics: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep=7):
        """Clean up old metrics data to prevent database bloat"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            with self._connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff_time,))
                deleted_count = cursor.rowcount
                
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} old metrics records (keeping last {days_to_keep} days)")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            with self._connect() as conn:
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

    def clear_all_metrics(self):
        """Delete all records from metrics table and return count"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM metrics')
                total_before = cursor.fetchone()[0]
                cursor.execute('DELETE FROM metrics')
                deleted_count = cursor.rowcount if cursor.rowcount is not None else total_before
                conn.commit()
                logger.info(f"Cleared {deleted_count} metrics records")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to clear metrics: {e}")
            return 0
    
    def store_system_info(self, key, value):
        """Store system information in database"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO system_info (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store system info: {e}")
            return False
    
    def get_system_info(self, key):
        """Get system information from database"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT value FROM system_info WHERE key = ?', (key,))
                result = cursor.fetchone()
                
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return None
