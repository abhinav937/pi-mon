#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Pi Monitor issues
Run this on your Raspberry Pi to diagnose all reported problems
"""

import asyncio
import os
import platform
import subprocess
import sys
import traceback
from datetime import datetime

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from system_monitor import SystemMonitor
from service_management import ServiceManager  
from power_management import PowerManager

def print_header(title):
    print()
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_section(title):
    print()
    print("-" * 40)
    print(f" {title}")
    print("-" * 40)

async def test_system_monitoring():
    """Test system monitoring functionality"""
    print_header("SYSTEM MONITORING DIAGNOSTICS")
    
    monitor = SystemMonitor()
    
    print_section("Testing psutil directly")
    try:
        import psutil
        print(f"✓ psutil version: {psutil.__version__}")
        
        # Test direct psutil calls
        cpu = psutil.cpu_percent(interval=1)
        print(f"✓ Direct CPU: {cpu}%")
        
        mem = psutil.virtual_memory()
        print(f"✓ Direct Memory: {mem.percent}% (total: {mem.total//1024//1024} MB)")
        
        disk = psutil.disk_usage('/')
        print(f"✓ Direct Disk: {(disk.used/disk.total)*100:.1f}% (total: {disk.total//1024//1024//1024} GB)")
        
        net = psutil.net_io_counters()
        print(f"✓ Direct Network: sent={net.bytes_sent}, recv={net.bytes_recv}")
        
    except Exception as e:
        print(f"✗ psutil direct test failed: {e}")
        traceback.print_exc()
    
    print_section("Testing SystemMonitor methods")
    
    # Test individual methods
    tests = [
        ("CPU", monitor.get_cpu_percent, 1.0),
        ("Memory", monitor.get_memory_stats, None),
        ("Disk", monitor.get_disk_usage, None),
        ("Temperature", monitor.get_temperature, None),
        ("Uptime", monitor.get_uptime, None),
        ("Network", monitor.get_network_stats, None),
    ]
    
    for name, method, arg in tests:
        try:
            if arg is not None:
                result = await method(arg)
            else:
                result = await method()
            print(f"✓ {name}: {result}")
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            traceback.print_exc()
    
    print_section("Testing complete system stats")
    try:
        stats = await monitor.get_system_stats()
        print(f"✓ Complete stats: {stats.dict()}")
        
        # Analyze results
        zero_values = []
        if stats.cpu_percent == 0.0:
            zero_values.append("CPU")
        if stats.memory_percent == 0.0:
            zero_values.append("Memory")
        if stats.disk_percent == 0.0:
            zero_values.append("Disk")
        if stats.temperature == 0.0:
            zero_values.append("Temperature")
            
        if zero_values:
            print(f"⚠️  Zero values detected: {', '.join(zero_values)}")
        else:
            print("✅ All metrics have non-zero values")
            
    except Exception as e:
        print(f"✗ Complete stats failed: {e}")
        traceback.print_exc()

async def test_service_management():
    """Test service management functionality"""
    print_header("SERVICE MANAGEMENT DIAGNOSTICS")
    
    service_manager = ServiceManager()
    
    print_section("Service Manager Configuration")
    print(f"OS Type: {service_manager.os_type}")
    print(f"Is Linux: {service_manager.is_linux}")
    print(f"Has systemctl: {service_manager.has_systemctl}")
    print(f"Has service commands: {service_manager.has_service_commands}")
    print(f"Has sudo privileges: {getattr(service_manager, 'has_sudo_privileges', 'Not checked')}")
    
    print_section("Testing systemctl availability")
    
    # Test systemctl without sudo
    try:
        result = subprocess.run(['systemctl', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ systemctl available (without sudo)")
            print(f"  Version info: {result.stdout.split()[1] if len(result.stdout.split()) > 1 else 'unknown'}")
        else:
            print(f"✗ systemctl not available: {result.stderr}")
    except Exception as e:
        print(f"✗ systemctl test failed: {e}")
    
    # Test systemctl with sudo
    try:
        result = subprocess.run(['sudo', '-n', 'systemctl', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ systemctl available with sudo (passwordless)")
        else:
            print(f"✗ systemctl with sudo failed: {result.stderr}")
            print("  This is why service management is disabled")
    except Exception as e:
        print(f"✗ systemctl sudo test failed: {e}")
    
    print_section("Testing service status (without sudo)")
    
    # Test a few key services without sudo
    test_services = ["ssh", "mosquitto", "pi-monitor"]
    for service in test_services:
        try:
            result = subprocess.run(['systemctl', 'status', service], 
                                  capture_output=True, text=True, timeout=5)
            if "Active: active" in result.stdout:
                print(f"✓ {service}: running")
            elif "Active: inactive" in result.stdout:
                print(f"○ {service}: stopped")
            elif "could not be found" in result.stdout:
                print(f"- {service}: not found")
            else:
                print(f"? {service}: unknown status")
        except Exception as e:
            print(f"✗ {service}: error - {e}")
    
    print_section("Testing service manager methods")
    
    # Test service manager methods
    try:
        status = await service_manager.get_service_status("ssh")
        print(f"✓ SSH service status: {status}")
    except Exception as e:
        print(f"✗ Service status test failed: {e}")
        traceback.print_exc()

async def test_power_management():
    """Test power management functionality"""
    print_header("POWER MANAGEMENT DIAGNOSTICS")
    
    power_manager = PowerManager()
    
    print_section("Power Manager Configuration")
    print(f"OS Type: {power_manager.os_type}")
    print(f"Is Linux: {power_manager.is_linux}")
    print(f"Has systemctl: {power_manager.has_systemctl}")
    print(f"Has power commands: {power_manager.has_power_commands}")
    print(f"Has sudo privileges: {getattr(power_manager, 'has_sudo_privileges', 'Not checked')}")
    print(f"Simulation mode: {power_manager.is_windows or not power_manager.has_power_commands}")
    
    print_section("Testing power commands")
    
    # Test power info
    try:
        power_info = await power_manager.get_system_power_info()
        print(f"✓ Power info: {power_info}")
    except Exception as e:
        print(f"✗ Power info failed: {e}")
        traceback.print_exc()

def test_environment():
    """Test environment and dependencies"""
    print_header("ENVIRONMENT DIAGNOSTICS")
    
    print_section("System Information")
    print(f"Platform: {platform.platform()}")
    print(f"System: {platform.system()}")
    print(f"Release: {platform.release()}")
    print(f"Version: {platform.version()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")
    
    print_section("Python Environment")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    
    print_section("Required Commands")
    
    commands = ['systemctl', 'sudo', 'vcgencmd', 'cat']
    for cmd in commands:
        try:
            result = subprocess.run(['which', cmd], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ {cmd}: {result.stdout.strip()}")
            else:
                print(f"✗ {cmd}: not found")
        except Exception as e:
            print(f"✗ {cmd}: error - {e}")
    
    print_section("File Access Tests")
    
    files = [
        '/sys/class/thermal/thermal_zone0/temp',
        '/proc/cpuinfo',
        '/sys/class/power_supply'
    ]
    
    for file_path in files:
        try:
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    with open(file_path, 'r') as f:
                        content = f.read().strip()[:100]  # First 100 chars
                    print(f"✓ {file_path}: accessible ({len(content)} chars)")
                else:
                    print(f"✓ {file_path}: directory exists")
            else:
                print(f"✗ {file_path}: not found")
        except Exception as e:
            print(f"✗ {file_path}: access error - {e}")

async def main():
    """Main diagnostic function"""
    print("Pi Monitor Comprehensive Diagnostics")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Run all diagnostic tests
    test_environment()
    await test_system_monitoring()
    await test_service_management()
    await test_power_management()
    
    print_header("SUMMARY AND RECOMMENDATIONS")
    
    print("Based on the diagnostics above:")
    print()
    print("1. If system monitoring shows zeros:")
    print("   → Run: python3 test_system_monitoring.py")
    print("   → Check if psutil is properly installed")
    print()
    print("2. If service management is disabled:")
    print("   → Run: sudo ./configure_sudo_permissions.sh")
    print("   → This grants necessary permissions to pimonitor user")
    print()
    print("3. If power management is in simulation mode:")
    print("   → Same fix as #2 - configure sudo permissions")
    print()
    print("4. After running sudo configuration:")
    print("   → Restart services: sudo systemctl restart pi-monitor")
    print("   → Test again with your API calls")

if __name__ == "__main__":
    asyncio.run(main())
