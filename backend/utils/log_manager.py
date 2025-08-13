#!/usr/bin/env python3
"""
Pi Monitor - Log Management
Handles log file operations like reading, downloading, and clearing
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class LogManager:
    """Manages log file operations"""
    
    def __init__(self):
        pass
    
    def get_logs_list(self):
        """Return a list of available log files"""
        results = []
        
        for base in ['/var/log', './logs', 'logs']:
            try:
                if os.path.isdir(base):
                    for name in os.listdir(base):
                        # Include common logs
                        if any(name.startswith(prefix) for prefix in ('syslog', 'auth', 'kern', 'daemon')) or name.endswith('.log'):
                            full = os.path.join(base, name)
                            try:
                                size_bytes = os.path.getsize(full)
                            except Exception:
                                size_bytes = 0
                            results.append({'name': name, 'path': base, 'size': size_bytes})
            except Exception:
                continue
        
        # Include backend log if present
        if os.path.exists('pi_monitor.log'):
            try:
                size_bytes = os.path.getsize('pi_monitor.log')
            except Exception:
                size_bytes = 0
            results.append({'name': 'pi_monitor.log', 'path': '.', 'size': size_bytes})
        
        return results
    
    def read_log(self, log_name, lines=100):
        """Return last N lines of a specific log file"""
        try:
            log_file = self._find_log_file(log_name) or ('pi_monitor.log' if log_name == 'pi_monitor.log' and os.path.exists('pi_monitor.log') else None)
            
            if not log_file:
                return {'error': 'Log not found'}
            
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
            
            return {
                'name': log_name,
                'entries': entries,
                'totalEntries': len(entries),
                'errorCount': error_count,
                'warningCount': warn_count,
                'size': size_bytes
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def download_log(self, request_handler, log_name):
        """Download a log file"""
        try:
            # Find the log file
            log_file = self._find_log_file(log_name)
            
            if not log_file:
                request_handler._send_not_found(f"Log file {log_name} not found")
                return
            
            # Read log content with streaming for large files
            self._stream_log_file(request_handler, log_file, log_name)
            
        except Exception as e:
            logger.error(f"Log download failed: {e}")
            request_handler._send_internal_error(f"Failed to download log: {str(e)}")
    
    def clear_log(self, log_name):
        """Clear a log file"""
        try:
            # Find the log file
            log_file = self._find_log_file(log_name)
            
            if not log_file:
                return {'error': f"Log file {log_name} not found"}
            
            # Clear log file (truncate to 0 bytes)
            with open(log_file, 'w') as f:
                pass  # This truncates the file
            
            return {
                "success": True,
                "message": f"Log {log_name} cleared successfully",
                "log_name": log_name
            }
            
        except Exception as e:
            logger.error(f"Log clear failed: {e}")
            return {"error": f"Failed to clear log: {str(e)}"}
    
    def _find_log_file(self, log_name):
        """Find log file in available directories"""
        log_dirs = ['/var/log', '/tmp', './logs', 'logs']
        
        for log_dir in log_dirs:
            potential_path = os.path.join(log_dir, log_name)
            if os.path.exists(potential_path):
                return potential_path
        return None
    
    def _stream_log_file(self, request_handler, log_file, log_name):
        """Stream log file content for better memory efficiency"""
        file_size = os.path.getsize(log_file)
        
        request_handler.send_response(200)
        request_handler.send_header('Content-type', 'text/plain')
        request_handler.send_header('Content-Disposition', f'attachment; filename="{log_name}"')
        request_handler.send_header('Content-Length', str(file_size))
        request_handler._set_common_headers()
        
        # Stream file in chunks
        chunk_size = 8192
        with open(log_file, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                request_handler.wfile.write(chunk)
    
    def _tail_file(self, filepath, num_lines):
        """Get last N lines of a file efficiently"""
        try:
            result = subprocess.run(['sudo', 'tail', '-n', str(num_lines), filepath], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Failed to tail file {filepath}: {result.stderr}")
                return ''
        except Exception as e:
            logger.error(f"Error tailing file {filepath}: {str(e)}")
            return ''
