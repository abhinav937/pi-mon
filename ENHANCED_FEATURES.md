# Pi Monitor Enhanced Features

This document describes the enhanced features that have been added to make Pi Monitor work similarly to [RPi-Monitor](https://github.com/XavierBerger/RPi-Monitor/tree/develop).

## 🚀 New Backend Features

### 1. Real-time Metrics Collection
- **Background Metrics Collection**: Continuous data collection every 5 seconds
- **Historical Data Storage**: Keeps up to 1000 data points in memory
- **Multiple Metrics**: CPU, Memory, Disk, Temperature, Network I/O, Disk I/O

### 2. Enhanced System Monitoring
- **Temperature Monitoring**: Multiple methods (Raspberry Pi thermal zones, sensors command)
- **Disk I/O Monitoring**: Read/write bytes and operations count
- **Network Monitoring**: Detailed packet and byte statistics
- **CPU Frequency**: Current, min, and max frequency detection

### 3. New API Endpoints

#### `/api/metrics`
- **Purpose**: Retrieve historical metrics data
- **Parameters**: `minutes` (default: 60)
- **Response**: Metrics history with collection status
- **Authentication**: Required

#### `/api/system/info`
- **Purpose**: Detailed system information
- **Response**: CPU details, memory info, network interfaces, system logs
- **Authentication**: Not required (public endpoint)

#### Enhanced `/api/system`
- **New Features**: Historical data aggregation
- **Parameters**: `history` (minutes for historical view)
- **Response**: Real-time or aggregated metrics

### 4. Improved Data Collection
- **Smart Temperature Detection**: Automatically detects available thermal sensors
- **Error Handling**: Graceful fallbacks for unavailable metrics
- **Data Validation**: Ensures data integrity and format consistency

## 🎨 Enhanced Frontend Features

### 1. Real-time Metrics Dashboard
- **Live Updates**: Real-time data visualization
- **Metrics Overview**: Collection status, update intervals, data point counts
- **Performance Trends**: Current vs. historical performance indicators

### 2. Enhanced Resource Charts
- **Time Range Selection**: 15m, 30m, 60m, 120m views
- **Multiple Metrics**: CPU, Memory, Temperature, Disk Usage
- **Historical Data**: Backend-powered historical charts
- **Responsive Design**: Mobile-friendly chart layouts

### 3. Detailed System Information
- **CPU Details**: Model, frequency, performance metrics
- **Memory Breakdown**: Total, available, used, swap information
- **Network Interfaces**: IP addresses, netmasks, broadcast info
- **System Logs**: Recent system log entries

### 4. Improved User Experience
- **Status Indicators**: Visual health status for all metrics
- **Real-time Updates**: Live data without page refresh
- **Error Handling**: Graceful fallbacks and user notifications
- **Responsive Layout**: Works on all device sizes

## 🔧 Technical Improvements

### 1. Backend Architecture
- **MetricsCollector Class**: Dedicated metrics collection and storage
- **Background Threading**: Non-blocking data collection
- **Memory Management**: Efficient data storage with automatic cleanup
- **Error Resilience**: Robust error handling and recovery

### 2. Frontend Architecture
- **React Query Integration**: Efficient data fetching and caching
- **Real-time Updates**: WebSocket-like real-time data flow
- **Component Modularity**: Reusable, maintainable components
- **State Management**: Centralized application state

### 3. Data Flow
```
Backend Metrics Collection → Historical Storage → API Endpoints → Frontend Queries → Real-time Updates
```

## 📊 Monitoring Capabilities

### System Metrics
- **CPU Usage**: Real-time percentage with historical trends
- **Memory Usage**: RAM utilization and swap information
- **Disk Usage**: Storage capacity and I/O statistics
- **Temperature**: System temperature monitoring
- **Network**: Traffic statistics and interface information

### Service Monitoring
- **Systemd Integration**: Service status and control
- **Health Checks**: Automatic service health monitoring
- **Service Control**: Start, stop, restart capabilities

### Power Management
- **Safe Operations**: Delayed shutdown/restart with confirmation
- **Status Monitoring**: Power state and uptime tracking
- **Action Logging**: All power operations are logged

## 🚀 Getting Started

### 1. Start the Enhanced Backend
```bash
cd backend
python3 simple_server.py
```

### 2. Start the Enhanced Frontend
```bash
cd frontend
npm start
```

### 3. Test the New Features
```bash
python3 test_enhanced_backend.py
```

## 🔐 Authentication

The enhanced system uses token-based authentication:
- **Username**: `abhinav`
- **Password**: `kavachi`
- **Token Expiration**: 24 hours
- **Storage**: In-memory (for demo purposes)

## 📈 Performance Features

### Real-time Updates
- **Collection Interval**: 5 seconds
- **Data Points**: Up to 1000 historical points
- **Memory Usage**: Efficient storage with automatic cleanup
- **Network Efficiency**: Minimal API calls with smart caching

### Historical Analysis
- **Time Ranges**: 15 minutes to 2 hours
- **Data Aggregation**: Smart averaging for historical views
- **Trend Analysis**: Performance pattern recognition
- **Export Capability**: JSON data export for external analysis

## 🛡️ Security Features

### CORS Support
- **Cross-Origin Requests**: Enabled for development
- **Header Management**: Proper security headers
- **Authentication**: Token-based access control

### Input Validation
- **Data Sanitization**: All inputs are validated
- **Error Handling**: Secure error responses
- **Rate Limiting**: Built-in request throttling

## 🔍 Troubleshooting

### Common Issues
1. **Metrics Not Collecting**: Check backend logs for collection status
2. **Authentication Fails**: Verify username/password credentials
3. **Charts Not Loading**: Check browser console for API errors
4. **Temperature Not Showing**: Verify thermal sensor availability

### Debug Mode
Enable debug logging by setting environment variables:
```bash
export PI_MONITOR_DEBUG=1
export PI_MONITOR_LOG_LEVEL=DEBUG
```

## 📚 API Reference

### Endpoints Overview
- `GET /` - Root endpoint with system info
- `GET /health` - Health check and status
- `POST /api/auth/token` - Authentication
- `GET /api/system` - System metrics (with history support)
- `GET /api/metrics` - Historical metrics data
- `GET /api/system/info` - Detailed system information
- `GET /api/services` - Service status and control
- `GET /api/power` - Power management status

### Response Formats
All endpoints return JSON with consistent error handling and status codes.

## 🎯 Future Enhancements

### Planned Features
- **Database Integration**: Persistent metrics storage
- **Alert System**: Configurable thresholds and notifications
- **Mobile App**: Native mobile monitoring application
- **Plugin System**: Extensible monitoring capabilities
- **Multi-Device Support**: Monitor multiple Raspberry Pis

### Community Contributions
We welcome contributions to enhance the monitoring capabilities further!

## 📄 License

This project maintains the same license as the original Pi Monitor project.

---

**Note**: This enhanced version provides RPi-Monitor-like functionality while maintaining the simplicity and ease of use of the original Pi Monitor project.
