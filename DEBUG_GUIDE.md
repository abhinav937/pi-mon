# 🔍 Power Management Debugging Guide

This guide explains how to use the comprehensive debugging features added to troubleshoot the shutdown/restart functionality.

## 🚀 Quick Start

1. **Open Chrome DevTools**: Press `F12` or right-click and select "Inspect"
2. **Go to Console Tab**: This is where all debug logs will appear
3. **Use the Debug Panel**: In the Power Management section, click "Show Debug" to see real-time status
4. **Test Connection**: Use the "Test Connection" button to verify backend connectivity

## 📋 Debug Features Added

### 1. Frontend Debug Panel
- **Location**: Power Management section (click "Show Debug")
- **Features**:
  - Real-time client status
  - Connection state monitoring
  - Debug logs summary
  - Recent error display
  - Clear logs functionality

### 2. Console Logging
- **Format**: `🔍 [PowerManagement Debug]` and `🔍 [UnifiedClient Debug]`
- **Information Logged**:
  - All HTTP requests and responses
  - Power action execution details
  - Error details with stack traces
  - Authentication status
  - Connection state changes

### 3. Standalone Debug Page
- **File**: `frontend/public/debug.html`
- **Access**: Navigate to `http://your-domain/debug.html`
- **Features**:
  - Direct API endpoint testing
  - No React dependencies
  - Real-time request/response logging
  - Connection testing

## 🔧 How to Debug Power Management Issues

### Step 1: Check Console Logs
1. Open Chrome DevTools (F12)
2. Go to Console tab
3. Look for logs starting with `🔍 [PowerManagement Debug]` or `🔍 [UnifiedClient Debug]`
4. Check for any error messages or failed requests

### Step 2: Use the Debug Panel
1. Navigate to Power Management in your app
2. Click "Show Debug" button
3. Check client status and connection state
4. Look for recent errors in the debug logs summary

### Step 3: Test Connection
1. In the debug panel, click "Test Connection"
2. This will test both health check and power status endpoints
3. Check the results for any connection issues

### Step 4: Use Standalone Debug Page
1. Navigate to `http://your-domain/debug.html`
2. Set the server URL to your backend
3. Test individual endpoints:
   - `/health` - Basic connectivity
   - `/api/power` - Power status
   - `/api/power/shutdown` - Shutdown endpoint
   - `/api/power/restart` - Restart endpoint

## 📊 What to Look For

### Common Issues and Solutions

#### 1. Connection Failed
- **Symptoms**: "Connection test failed" errors
- **Possible Causes**:
  - Backend server not running
  - Wrong server URL
  - Network/firewall issues
- **Solutions**:
  - Verify backend is running
  - Check server URL configuration
  - Test network connectivity

#### 2. Authentication Errors
- **Symptoms**: 401 Unauthorized responses
- **Possible Causes**:
  - Invalid or expired auth token
  - Backend auth configuration issues
- **Solutions**:
  - Check auth token in localStorage
  - Verify backend auth settings
  - Clear and re-authenticate

#### 3. Permission Denied
- **Symptoms**: Backend returns permission errors
- **Possible Causes**:
  - Backend running without sufficient privileges
  - Missing sudo access on Linux/Pi
  - Windows not running as Administrator
- **Solutions**:
  - Run backend with appropriate privileges
  - Check system permissions
  - Use the `test_power_permissions.py` script

#### 4. Command Execution Failed
- **Symptoms**: Backend returns command execution errors
- **Possible Causes**:
  - Commands not available in PATH
  - System-specific command differences
  - Timeout issues
- **Solutions**:
  - Check command availability
  - Verify system compatibility
  - Check backend logs for detailed errors

## 🐛 Debug Log Examples

### Successful Request
```
🔍 [UnifiedClient Debug] HTTP Request {
  method: "POST",
  url: "/api/power/shutdown",
  data: { action: "shutdown", delay: 0 }
}

🔍 [UnifiedClient Debug] HTTP Response Success {
  status: 200,
  data: { success: true, message: "Shutdown initiated" }
}
```

### Failed Request
```
🔍 [UnifiedClient Debug] HTTP Response Error {
  message: "Request failed",
  status: 500,
  responseData: { error: "Permission denied" }
}
```

## 🛠️ Advanced Debugging

### 1. Check localStorage Debug Logs
```javascript
// In browser console
const logs = JSON.parse(localStorage.getItem('pi-monitor-debug-logs') || '[]');
console.table(logs);
```

### 2. Monitor Network Tab
1. Open Chrome DevTools
2. Go to Network tab
3. Execute a power action
4. Look for the API request and response
5. Check request headers, body, and response

### 3. Backend Logs
- Check the Python backend console for any error messages
- Look for permission errors or command execution failures
- Verify the backend is receiving requests

## 📱 Mobile Debugging

### Chrome DevTools on Mobile
1. Connect your phone to computer
2. Enable USB debugging
3. Open Chrome DevTools
4. Use "Remote devices" to debug mobile

### Alternative: Standalone Debug Page
- The `debug.html` page works on mobile devices
- Use it to test API endpoints directly
- Check mobile browser console for errors

## 🔍 Troubleshooting Checklist

- [ ] Backend server is running
- [ ] Server URL is correct
- [ ] Authentication is working
- [ ] Network connectivity is good
- [ ] Backend has sufficient privileges
- [ ] Commands are available in system PATH
- [ ] No firewall/security blocking requests
- [ ] Console shows no JavaScript errors
- [ ] Network tab shows successful requests
- [ ] Backend logs show no errors

## 📞 Getting Help

If you're still experiencing issues:

1. **Collect Debug Information**:
   - Screenshots of console errors
   - Debug panel information
   - Backend error messages
   - Network request/response details

2. **Check Backend Status**:
   - Run `test_power_permissions.py` script
   - Verify backend is running with proper privileges
   - Check system permissions

3. **Test with Standalone Page**:
   - Use `debug.html` to isolate frontend vs backend issues
   - Test endpoints directly without React app

## 🎯 Expected Behavior

### Successful Shutdown/Restart
1. User clicks button
2. Confirmation modal appears
3. User confirms action
4. Backend receives request
5. System executes command
6. Frontend shows success message
7. System shuts down/restarts

### Debug Information Available
- Request details (URL, method, data)
- Response details (status, data)
- Error details (message, stack trace)
- Connection state changes
- Authentication status
- Command execution results

This debugging system provides comprehensive visibility into the power management functionality, making it easier to identify and resolve issues.
