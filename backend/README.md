# Pi Monitor Backend - Modular Structure

This directory contains the modularized Pi Monitor backend, broken down from the original 3,000+ line `simple_server.py` into logical, maintainable components.

## File Structure

### Core Files
- **`main.py`** - Main entry point that creates and runs the server
- **`server.py`** - Main HTTP server class and request handler
- **`simple_server.py`** - Backward compatibility launcher

### Service Modules
- **`metrics.py`** - System metrics collection and management
- **`database.py`** - SQLite database operations for metrics storage
- **`system_monitor.py`** - System information gathering and monitoring
- **`service_manager.py`** - System service control and management
- **`power_manager.py`** - System power operations (shutdown, restart, sleep)
- **`log_manager.py`** - Log file operations (read, download, clear)
- **`auth.py`** - API key authentication and validation

### Utilities
- **`utils.py`** - Common decorators and utility functions

## Benefits of Modularization

1. **Maintainability** - Each module has a single responsibility
2. **Readability** - Much easier to understand and navigate
3. **Testability** - Individual modules can be tested in isolation
4. **Reusability** - Modules can be imported and used independently
5. **Collaboration** - Multiple developers can work on different modules
6. **Debugging** - Easier to locate and fix issues

## Module Responsibilities

### `MetricsCollector` (metrics.py)
- Background metrics collection
- System performance monitoring
- Data caching and history management

### `MetricsDatabase` (database.py)
- SQLite database operations
- Metrics storage and retrieval
- Data cleanup and maintenance

### `SystemMonitor` (system_monitor.py)
- CPU, memory, disk monitoring
- Network interface information
- Temperature and hardware stats

### `ServiceManager` (service_manager.py)
- System service control (start/stop/restart)
- Service status monitoring
- Safe service restart operations

### `PowerManager` (power_manager.py)
- System shutdown and restart
- Permission checking
- Cross-platform power operations

### `LogManager` (log_manager.py)
- Log file discovery and listing
- Log content reading and parsing
- Log download and clearing

### `AuthManager` (auth.py)
- API key validation
- Request authentication
- Security management

## Usage

### Running the Server
```bash
# Using the main entry point
python main.py

# Using backward compatibility launcher
python simple_server.py
```

### Importing Individual Modules
```python
from metrics import MetricsCollector
from system_monitor import SystemMonitor
from service_manager import ServiceManager

# Use individual components
collector = MetricsCollector()
monitor = SystemMonitor()
service_mgr = ServiceManager()
```

## Configuration

The server uses the existing `config.py` file for configuration. All modules import from this central configuration.

## Dependencies

- **psutil** - System and process utilities
- **sqlite3** - Database operations (built-in)
- **subprocess** - System command execution (built-in)
- **threading** - Background operations (built-in)

## Migration Notes

- The original `simple_server.py` functionality is preserved
- All existing API endpoints work exactly the same
- The modular structure is internal and doesn't affect the external API
- Backward compatibility is maintained through the launcher file

## Future Enhancements

With this modular structure, it's now much easier to:
- Add new monitoring capabilities
- Implement additional service types
- Create new authentication methods
- Add database backends
- Implement caching strategies
- Add monitoring plugins
