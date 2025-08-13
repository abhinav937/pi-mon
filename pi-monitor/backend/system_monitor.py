#!/usr/bin/env python3
"""
Pi Monitor - System Monitor Module
Collects system metrics using psutil and Raspberry Pi specific tools
"""

import asyncio
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

import psutil
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

class SystemStats(BaseModel):
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    temperature: float
    uptime: str
    network: Dict[str, int]

class SystemMonitor:
    """System monitoring class for collecting Pi metrics"""
    
    def __init__(self):
        self.boot_time = psutil.boot_time()
        self._last_network_stats = None
        self._network_interval = 1.0
        
    async def get_cpu_percent(self, interval: float = 1.0) -> float:
        """Get CPU usage percentage"""
        try:
            # Use psutil with a short interval for responsiveness
            return psutil.cpu_percent(interval=interval)
        except Exception as e:
            logger.warning("Error getting CPU percentage", error=str(e))
            return 0.0
    
    async def get_memory_stats(self) -> float:
        """Get memory usage percentage"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception as e:
            logger.warning("Error getting memory stats", error=str(e))
            return 0.0
    
    async def get_disk_usage(self, path: str = "/") -> float:
        """Get disk usage percentage"""
        try:
            disk = psutil.disk_usage(path)
            return (disk.used / disk.total) * 100
        except Exception as e:
            logger.warning("Error getting disk usage", error=str(e), path=path)
            return 0.0
    
    async def get_temperature(self) -> float:
        """Get CPU temperature using vcgencmd (Pi-specific)"""
        try:
            # Try vcgencmd first (Raspberry Pi specific)
            result = await asyncio.create_subprocess_exec(
                'vcgencmd', 'measure_temp',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                temp_str = stdout.decode().strip()
                # Parse "temp=XX.X'C" format
                if 'temp=' in temp_str:
                    temp_value = temp_str.split('=')[1].replace("'C", "")
                    return float(temp_value)
            
            # Fallback: try thermal zone
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_millicelsius = int(f.read().strip())
                return temp_millicelsius / 1000.0
                
        except Exception as e:
            logger.warning("Error getting temperature", error=str(e))
            # Try alternate methods
            try:
                # Try psutil sensors (may work on some systems)
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            return entries[0].current
                return 0.0
            except:
                return 0.0
    
    async def get_uptime(self) -> str:
        """Get system uptime as human-readable string"""
        try:
            uptime_seconds = time.time() - self.boot_time
            uptime_delta = timedelta(seconds=int(uptime_seconds))
            
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
                
        except Exception as e:
            logger.warning("Error getting uptime", error=str(e))
            return "Unknown"
    
    async def get_network_stats(self) -> Dict[str, int]:
        """Get network I/O statistics"""
        try:
            net_io = psutil.net_io_counters()
            if net_io is None:
                return {"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0}
            
            stats = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
            
            # Calculate rates if we have previous stats
            if self._last_network_stats:
                time_diff = time.time() - self._last_network_stats["timestamp"]
                if time_diff > 0:
                    stats["bytes_sent_rate"] = max(0, (stats["bytes_sent"] - self._last_network_stats["bytes_sent"]) / time_diff)
                    stats["bytes_recv_rate"] = max(0, (stats["bytes_recv"] - self._last_network_stats["bytes_recv"]) / time_diff)
            
            # Update last stats
            self._last_network_stats = {
                **stats,
                "timestamp": time.time()
            }
            
            return stats
            
        except Exception as e:
            logger.warning("Error getting network stats", error=str(e))
            return {"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0}
    
    async def get_system_stats(self) -> SystemStats:
        """Get comprehensive system statistics"""
        try:
            # Gather all metrics concurrently for better performance
            cpu_task = asyncio.create_task(self.get_cpu_percent(interval=0.1))
            memory_task = asyncio.create_task(self.get_memory_stats())
            disk_task = asyncio.create_task(self.get_disk_usage())
            temp_task = asyncio.create_task(self.get_temperature())
            uptime_task = asyncio.create_task(self.get_uptime())
            network_task = asyncio.create_task(self.get_network_stats())
            
            # Wait for all tasks to complete
            cpu_percent = await cpu_task
            memory_percent = await memory_task
            disk_percent = await disk_task
            temperature = await temp_task
            uptime = await uptime_task
            network = await network_task
            
            return SystemStats(
                timestamp=datetime.utcnow().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_percent=disk_percent,
                temperature=temperature,
                uptime=uptime,
                network=network
            )
            
        except Exception as e:
            logger.error("Error collecting system stats", error=str(e))
            # Return default stats in case of error
            return SystemStats(
                timestamp=datetime.utcnow().isoformat(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_percent=0.0,
                temperature=0.0,
                uptime="Unknown",
                network={"bytes_sent": 0, "bytes_recv": 0, "packets_sent": 0, "packets_recv": 0}
            )
    
    async def get_detailed_info(self) -> Dict:
        """Get detailed system information"""
        try:
            info = {
                "hostname": psutil.os.uname().nodename,
                "platform": psutil.os.uname().system,
                "architecture": psutil.os.uname().machine,
                "processor": psutil.os.uname().processor,
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage("/").total,
                "boot_time": datetime.fromtimestamp(self.boot_time).isoformat()
            }
            
            # Try to get Pi-specific info
            try:
                # Pi model info
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    for line in cpuinfo.split('\n'):
                        if line.startswith('Model'):
                            info["pi_model"] = line.split(':')[1].strip()
                            break
                
                # Pi revision
                result = await asyncio.create_subprocess_exec(
                    'cat', '/proc/cpuinfo',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()
                for line in stdout.decode().split('\n'):
                    if line.startswith('Revision'):
                        info["pi_revision"] = line.split(':')[1].strip()
                        break
                        
            except Exception as e:
                logger.debug("Could not get Pi-specific info", error=str(e))
            
            return info
            
        except Exception as e:
            logger.error("Error getting detailed system info", error=str(e))
            return {"error": "Unable to collect system information"}

# Helper function for standalone usage
async def get_current_stats() -> SystemStats:
    """Standalone function to get current system stats"""
    monitor = SystemMonitor()
    return await monitor.get_system_stats()

if __name__ == "__main__":
    # Test the system monitor
    async def test():
        monitor = SystemMonitor()
        stats = await monitor.get_system_stats()
        print(f"System Stats: {stats.json(indent=2)}")
        
        detailed = await monitor.get_detailed_info()
        print(f"Detailed Info: {detailed}")
    
    asyncio.run(test())