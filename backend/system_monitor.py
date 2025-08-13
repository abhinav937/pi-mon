#!/usr/bin/env python3
"""
Pi Monitor - System Monitoring
Handles system information gathering and monitoring
"""

import time
import platform
import logging
from collections import deque

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
        
        @staticmethod
        def net_if_addrs():
            return {}
        
        @staticmethod
        def net_if_stats():
            return {}
    
    psutil = MinimalPsutil()

logger = logging.getLogger(__name__)

# Network rate tracker for calculating upload/download speeds
net_rate_tracker = {
    'last_ts': 0.0,
    'pernic': {},  # name -> (bytes_recv, bytes_sent)
    'totals': {'bytes_recv': 0, 'bytes_sent': 0}
}

class SystemMonitor:
    """System monitoring and information gathering"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=5000)  # Keep last 5000 data points
    
    def get_system_info(self):
        """Get basic system information"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime = f"{uptime_hours}h {uptime_minutes}m"
            
            return {
                "uptime": uptime,
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "server_time": time.strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
            return {"error": f"Failed to get system info: {str(e)}"}
    
    def get_uptime(self):
        """Get system uptime"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            return f"{uptime_hours}h {uptime_minutes}m"
        except Exception as e:
            logger.error(f"Failed to get uptime: {e}")
            return {"error": f"Failed to get uptime: {str(e)}"}
    
    def get_system_stats(self):
        """Get current system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            temperature = self._get_temperature()
            network = psutil.net_io_counters()
            disk_io = psutil.disk_io_counters()
            uptime = self.get_uptime()
            
            # Ensure all numeric values are valid numbers, not None
            return {
                "timestamp": time.time(),
                "uptime": uptime,
                "cpu_percent": float(cpu_percent) if cpu_percent is not None else 0.0,
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
    
    def get_system_stats_with_history(self, minutes):
        """Get system statistics with history for the last N minutes"""
        try:
            cutoff_time = time.time() - (minutes * 60)
            recent_metrics = [m for m in self.metrics_history if m.get('timestamp', 0) > cutoff_time]
            
            if not recent_metrics:
                return {"message": f"No metrics data available for the last {minutes} minutes."}
            
            # Aggregate metrics for the last N minutes
            aggregated_metrics = {
                "timestamp": time.time(),
                "cpu_percent": sum(float(m['cpu_percent']) if m['cpu_percent'] is not None else 0.0 for m in recent_metrics) / len(recent_metrics),
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
    
    def get_enhanced_system_stats(self):
        """Get enhanced system statistics with formatted values and status indicators"""
        try:
            # Get basic stats
            basic_stats = self.get_system_stats()
            
            if "error" in basic_stats:
                return basic_stats
            
            # Get additional system information
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_freq = psutil.cpu_freq()
            
            # Format values for frontend display
            enhanced_stats = {
                "timestamp": basic_stats["timestamp"],
                "cpu": {
                    "percent": basic_stats["cpu_percent"],
                    "frequency_mhz": round(cpu_freq.current if cpu_freq else 0, 1),
                    "frequency_ghz": round((cpu_freq.current if cpu_freq else 0) / 1000, 2),
                    "status": self._get_cpu_status(basic_stats["cpu_percent"]),
                    "cores": psutil.cpu_count(),
                    "cores_logical": psutil.cpu_count(logical=True)
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
                    "status": self._get_temperature_status(basic_stats["temperature"])
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
                    "uptime": self.get_uptime(),
                    "boot_time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(psutil.boot_time())),
                    "platform": platform.platform(),
                    "python_version": platform.python_version()
                },
                "enhanced_monitoring": True
            }
            
            return enhanced_stats
            
        except Exception as e:
            logger.error(f"Failed to get enhanced system stats: {e}")
            return {"timestamp": time.time(), "error": f"Failed to get enhanced system stats: {str(e)}"}
    
    def get_system_info_detail(self):
        """Provide detailed system info used by frontend SystemStatus"""
        try:
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            net_if_addrs = psutil.net_if_addrs()
            network_interfaces = {}
            
            for name, addrs in net_if_addrs.items():
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
            return response
        except Exception as e:
            return {'error': str(e)}
    
    def get_network_info(self):
        """Return network interface details"""
        interfaces = []
        dns = {'primary': None, 'secondary': None}
        gateway = None
        route_status = None
        
        try:
            # Interfaces
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for name, addr_list in addrs.items():
                iface_type = 'ethernet' if name.lower().startswith(('eth', 'enp', 'eno')) else ('wifi' if name.lower().startswith(('wlan', 'wl')) else 'other')
                iface = {
                    'name': name,
                    'type': iface_type,
                    'status': 'up' if (stats.get(name).isup if stats.get(name) else True) else 'down',
                }
                
                for a in addr_list:
                    if getattr(a, 'family', None) and str(getattr(a, 'family')) in ('AddressFamily.AF_INET', '2'):
                        iface['ip'] = getattr(a, 'address', None)
                    if hasattr(a, 'address') and a.address and ':' in a.address and 'mac' not in iface:
                        iface['mac'] = a.address
                
                if stats.get(name):
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
                import subprocess
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
            logger.error(f"Failed to get network info: {e}")
            interfaces = []
        
        return {
            'interfaces': interfaces,
            'dns': dns,
            'gateway': gateway,
            'routeStatus': route_status
        }
    
    def get_network_stats(self):
        """Return instantaneous upload/download speeds per interface and totals"""
        try:
            now = time.time()
            pernic = psutil.net_io_counters(pernic=True)
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
            return response
            
        except Exception as e:
            logger.error(f"Failed to get network stats: {e}")
            return {'download': 0, 'upload': 0}
    
    def _get_temperature(self):
        """Get system temperature using multiple methods"""
        try:
            import os
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
