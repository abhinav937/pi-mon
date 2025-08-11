# Enhanced Pi Monitor Backend - System Monitoring Commands

## Overview

The Pi Monitor backend has been enhanced with comprehensive system monitoring capabilities, providing access to 50+ system commands for real-time monitoring and diagnostics of Raspberry Pi systems.

## New Features

### 🔧 Enhanced Metrics Collection
- **Real-time monitoring** with 5-second intervals
- **Command caching** for efficiency (30-second cache duration)
- **Enhanced temperature detection** using multiple methods
- **Raspberry Pi specific metrics** (vcgencmd integration)

### 🖥️ New API Endpoints

#### `/api/commands` - System Commands Management
- **GET** `/api/commands` - List all available commands
- **GET** `/api/commands?command=<name>` - Execute specific command

#### Enhanced `/api/system/enhanced`
- **Enhanced CPU data** with temperature, clock speed, and voltage
- **Command integration** for real-time hardware metrics
- **Status indicators** for system health

## System Monitoring Commands

### 📊 System Information Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `kernel_info` | Kernel version and architecture | `Linux raspberrypi 5.15.0...` |
| `cpu_info` | CPU details and model | `Model: ARMv7...` |
| `memory_info` | Detailed memory information | `MemTotal: 948MB...` |
| `disk_partitions` | Disk partition information | `major minor...` |
| `os_release` | Linux distribution details | `Distributor ID: Raspbian...` |
| `kernel_messages` | Recent kernel messages | `[0.000000] Booting Linux...` |
| `system_version` | System version information | `Linux version 5.15.0...` |
| `hostname_info` | System hostname and OS info | `Operating System: Raspbian...` |

### 🔧 Hardware Detection Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `arm_memory` | ARM memory allocation | `arm=948M` |
| `gpu_memory` | GPU memory allocation | `gpu=76M` |
| `device_model` | Device model information | `Raspberry Pi 4 Model B...` |
| `cpu_architecture` | CPU architecture details | `Architecture: armv7l...` |
| `usb_devices` | USB device list | `Bus 001 Device 001...` |
| `pci_devices` | PCI device list | `00:00.0 PCI bridge...` |

### 📈 Resource Usage Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `system_load` | System load averages | `load average: 0.52, 0.58...` |
| `load_average` | Raw load average data | `0.52 0.58 0.59 1/89 1234` |
| `memory_usage` | Memory usage summary | `total used free shared...` |
| `memory_detailed` | Detailed memory stats | `MemTotal: 948MB...` |
| `disk_usage` | Disk space usage | `Filesystem Size Used Avail...` |
| `disk_io_stats` | Disk I/O statistics | `1 0 ram0 0 0 0 0 0...` |
| `process_list` | Top CPU processes | `PID %CPU %MEM COMMAND...` |
| `top_processes` | Top processes by resource | `PID PPID CMD %MEM %CPU...` |

### 🌐 Network Information Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `network_interfaces` | Network interface info | `1: lo: <LOOPBACK...` |
| `network_stats` | Network device statistics | `Inter-| Receive | Transmit...` |
| `network_connections` | Active network connections | `tcp LISTEN 0 128...` |
| `routing_table` | Network routing table | `default via 192.168.1.1...` |
| `dns_servers` | DNS server configuration | `nameserver 8.8.8.8...` |

### 🍓 Raspberry Pi Specific Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `cpu_temperature` | CPU temperature | `temp=45.1'C` |
| `arm_clock` | ARM processor clock speed | `frequency(45)=1400000000` |
| `core_clock` | Core clock speed | `frequency(1)=250000000` |
| `gpu_clock` | H.264 clock speed | `frequency(28)=300000000` |
| `core_voltage` | Core voltage | `volt=1.2000V` |
| `throttling_status` | Throttling status | `throttled=0x0` |
| `pi_config` | Pi configuration values | `arm_freq=1400...` |

### 🚀 System Services Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `service_status` | Running services | `UNIT LOAD ACTIVE SUB...` |
| `docker_status` | Docker container status | `NAMES STATUS PORTS...` |
| `ssh_status` | SSH service status | `● ssh.service - OpenBSD...` |

### 📝 System Logs Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `recent_logs` | Recent system logs | `Jan 1 00:00:00...` |
| `auth_logs` | Authentication logs | `Jan 1 00:00:00...` |
| `kernel_logs` | Kernel logs | `-- Logs begin at...` |

### 📊 Performance Monitoring Commands

| Command | Description | Example Output |
|---------|-------------|----------------|
| `cpu_stats` | CPU statistics | `Linux 5.15.0...` |
| `memory_stats` | Memory statistics | `procs -----------memory...` |
| `disk_stats` | Disk I/O statistics | `Linux 5.15.0...` |
| `network_stats` | Network protocol stats | `Ip: Forwarding...` |

## API Usage Examples

### Get All Available Commands

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/commands
```

### Execute Specific Command

```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/commands?command=cpu_temperature"
```

### Get Enhanced System Stats

```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/system/enhanced
```

### Get Metrics with Enhanced Data

```bash
curl -H "Authorization: Bearer <token>" \
     "http://localhost:8000/api/metrics?minutes=60"
```

## Command Categories

### System Information (8 commands)
- Kernel and OS details
- Version information
- System configuration

### Hardware (6 commands)
- CPU and memory details
- Device detection
- Hardware specifications

### Resource Usage (8 commands)
- System load and performance
- Memory and disk usage
- Process monitoring

### Network (5 commands)
- Interface information
- Connection status
- Network configuration

### Raspberry Pi (7 commands)
- Temperature monitoring
- Clock speeds
- Voltage readings
- Throttling status

### Services (3 commands)
- Service status
- Docker containers
- SSH service

### Logs (3 commands)
- System logs
- Authentication logs
- Kernel logs

### Performance (4 commands)
- CPU statistics
- Memory statistics
- Disk I/O
- Network statistics

## Command Caching

The system implements intelligent command caching to improve performance:

- **Cache duration**: 30 seconds
- **Automatic invalidation**: Commands are re-executed after cache expires
- **Efficient monitoring**: Reduces system load during continuous monitoring
- **Real-time updates**: Critical metrics are updated every 5 seconds

## Error Handling

Commands are executed safely with:

- **Timeout protection**: 10-second command timeout
- **Error reporting**: Detailed error messages for failed commands
- **Graceful degradation**: System continues working even if some commands fail
- **Fallback methods**: Multiple approaches for critical metrics like temperature

## Security Features

- **Authentication required**: All command endpoints require valid tokens
- **Command validation**: Only predefined commands can be executed
- **Input sanitization**: Command parameters are validated
- **Rate limiting**: Built-in caching prevents command abuse

## Performance Considerations

- **Background collection**: Metrics are collected in background threads
- **Efficient caching**: Reduces repeated command execution
- **Resource monitoring**: System tracks its own resource usage
- **Scalable architecture**: Can handle multiple concurrent requests

## Testing

Use the provided test script to verify functionality:

```bash
python3 test_enhanced_monitoring.py
```

This will test all endpoints and demonstrate the enhanced monitoring capabilities.

## Troubleshooting

### Common Issues

1. **Command not found**: Some commands may not be available on all systems
2. **Permission denied**: Some commands require root privileges
3. **Timeout errors**: Commands may take longer on slower systems
4. **Missing packages**: Some commands require additional software packages

### Solutions

1. **Install missing packages**: `sudo apt install sysstat iotop htop`
2. **Check permissions**: Ensure the backend has necessary access
3. **Adjust timeouts**: Modify timeout values in the code if needed
4. **Verify system compatibility**: Some commands are Raspberry Pi specific

## Future Enhancements

- **Custom command support**: Allow users to define custom monitoring commands
- **Alert system**: Threshold-based alerts for critical metrics
- **Historical data**: Long-term storage of command outputs
- **WebSocket support**: Real-time command output streaming
- **Command scheduling**: Automated command execution at specified intervals

## Conclusion

The enhanced Pi Monitor backend provides comprehensive system monitoring capabilities through 50+ system commands, making it a powerful tool for Raspberry Pi system administration and monitoring. The intelligent caching system and error handling ensure reliable operation while maintaining system performance.
