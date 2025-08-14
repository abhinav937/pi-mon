#!/usr/bin/env python3
"""
Pi Monitor - Database Management
Handles SQLite database operations for metrics storage
"""

import sqlite3
import os
import time
import logging

logger = logging.getLogger(__name__)

class MetricsDatabase:
    """SQLite database for storing metrics data"""
    
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
                        voltage REAL,
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
                        timestamp, cpu_percent, memory_percent, disk_percent, temperature, voltage,
                        network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                        disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics_data.get('timestamp', time.time()),
                    metrics_data.get('cpu_percent'),
                    metrics_data.get('memory_percent'),
                    metrics_data.get('disk_percent'),
                    metrics_data.get('temperature'),
                    metrics_data.get('voltage'),
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
            
            logger.info(f"Database query: minutes={minutes}, cutoff_time={cutoff_time}, limit={limit}")
            
            # Increase limit for longer time ranges to get more data points
            if minutes >= 1440:  # 24 hours or more
                effective_limit = min(limit * 4, 50000)  # Allow up to 50k records for 24hr+ views
            elif minutes >= 720:  # 12 hours or more
                effective_limit = min(limit * 2, 25000)  # Allow up to 25k records for 12hr+ views
            else:
                effective_limit = limit
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT timestamp, cpu_percent, memory_percent, disk_percent, temperature, voltage,
                           network_bytes_sent, network_bytes_recv, network_packets_sent, network_packets_recv,
                           disk_read_bytes, disk_write_bytes, disk_read_count, disk_write_count
                    FROM metrics 
                    WHERE timestamp > ? 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                ''', (cutoff_time, effective_limit))
                
                rows = cursor.fetchall()
                logger.info(f"Database returned {len(rows)} rows (requested: {effective_limit})")
                
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
                        'network': {
                            'bytes_sent': row[6],
                            'bytes_recv': row[7],
                            'packets_sent': row[8],
                            'packets_recv': row[9]
                        },
                        'disk_io': {
                            'read_bytes': row[10],
                            'write_bytes': row[11],
                            'read_count': row[12],
                            'write_count': row[13]
                        }
                    })
                
                logger.info(f"Converted {len(metrics)} metrics for frontend")
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get metrics history: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep=7):
        """Clean up old metrics data to prevent database bloat"""
        try:
            cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
            
            with sqlite3.connect(self.db_path) as conn:
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

    def clear_all_metrics(self):
        """Delete all records from metrics table and return count"""
        try:
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT value FROM system_info WHERE key = ?', (key,))
                result = cursor.fetchone()
                
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return None
