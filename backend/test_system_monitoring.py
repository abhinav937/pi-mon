#!/usr/bin/env python3
"""
Test script to diagnose system monitoring issues
Run this on your Raspberry Pi to test the monitoring functions
"""

import asyncio
import sys
import traceback
from system_monitor import SystemMonitor

async def test_individual_functions():
    """Test each monitoring function individually"""
    monitor = SystemMonitor()
    
    print("=== Testing Individual System Monitoring Functions ===")
    print()
    
    # Test CPU
    print("1. Testing CPU monitoring...")
    try:
        cpu = await monitor.get_cpu_percent(interval=1.0)
        print(f"   ✓ CPU: {cpu}%")
    except Exception as e:
        print(f"   ✗ CPU Error: {e}")
        traceback.print_exc()
    print()
    
    # Test Memory
    print("2. Testing Memory monitoring...")
    try:
        memory = await monitor.get_memory_stats()
        print(f"   ✓ Memory: {memory}%")
    except Exception as e:
        print(f"   ✗ Memory Error: {e}")
        traceback.print_exc()
    print()
    
    # Test Disk
    print("3. Testing Disk monitoring...")
    try:
        disk = await monitor.get_disk_usage()
        print(f"   ✓ Disk: {disk}%")
    except Exception as e:
        print(f"   ✗ Disk Error: {e}")
        traceback.print_exc()
    print()
    
    # Test Temperature
    print("4. Testing Temperature monitoring...")
    try:
        temp = await monitor.get_temperature()
        print(f"   ✓ Temperature: {temp}°C")
    except Exception as e:
        print(f"   ✗ Temperature Error: {e}")
        traceback.print_exc()
    print()
    
    # Test Uptime
    print("5. Testing Uptime monitoring...")
    try:
        uptime = await monitor.get_uptime()
        print(f"   ✓ Uptime: {uptime}")
    except Exception as e:
        print(f"   ✗ Uptime Error: {e}")
        traceback.print_exc()
    print()
    
    # Test Network
    print("6. Testing Network monitoring...")
    try:
        network = await monitor.get_network_stats()
        print(f"   ✓ Network: {network}")
    except Exception as e:
        print(f"   ✗ Network Error: {e}")
        traceback.print_exc()
    print()

async def test_complete_stats():
    """Test the complete system stats function"""
    print("=== Testing Complete System Stats ===")
    monitor = SystemMonitor()
    
    try:
        stats = await monitor.get_system_stats()
        print(f"Complete stats: {stats}")
        
        # Check if any values are zero
        issues = []
        if stats.cpu_percent == 0.0:
            issues.append("CPU is 0.0")
        if stats.memory_percent == 0.0:
            issues.append("Memory is 0.0")
        if stats.disk_percent == 0.0:
            issues.append("Disk is 0.0")
        if stats.temperature == 0.0:
            issues.append("Temperature is 0.0")
            
        if issues:
            print(f"\n⚠️ Issues found: {', '.join(issues)}")
        else:
            print("\n✅ All metrics have non-zero values")
            
    except Exception as e:
        print(f"✗ Complete stats error: {e}")
        traceback.print_exc()

async def test_psutil_directly():
    """Test psutil functions directly"""
    print("=== Testing psutil directly ===")
    
    try:
        import psutil
        print(f"psutil version: {psutil.__version__}")
        
        # Test CPU
        cpu = psutil.cpu_percent(interval=1)
        print(f"Direct CPU: {cpu}%")
        
        # Test Memory
        mem = psutil.virtual_memory()
        print(f"Direct Memory: {mem.percent}% (total: {mem.total}, used: {mem.used})")
        
        # Test Disk
        disk = psutil.disk_usage('/')
        print(f"Direct Disk: {(disk.used/disk.total)*100:.1f}% (total: {disk.total}, used: {disk.used})")
        
        # Test Network
        net = psutil.net_io_counters()
        print(f"Direct Network: {net}")
        
        # Test Boot time
        boot_time = psutil.boot_time()
        print(f"Boot time: {boot_time}")
        
    except Exception as e:
        print(f"✗ psutil direct test error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Pi Monitor System Monitoring Diagnostic Tool")
    print("=" * 50)
    print()
    
    asyncio.run(test_psutil_directly())
    print()
    asyncio.run(test_individual_functions())
    print()
    asyncio.run(test_complete_stats())
