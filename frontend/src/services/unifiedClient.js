import axios from 'axios';
import PRODUCTION_CONFIG from '../config/production.js';

const CONNECTION_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

// Debug logging function
const logDebug = (message, data = null, type = 'info') => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    type,
    message,
    data
  };
  
  console.log(`[UnifiedClient Debug] ${message}`, logEntry);
  
  // Also log to localStorage for persistence across page reloads
  try {
    const existingLogs = JSON.parse(localStorage.getItem('pi-monitor-debug-logs') || '[]');
    existingLogs.push(logEntry);
    // Keep only last 100 logs
    if (existingLogs.length > 100) {
      existingLogs.splice(0, existingLogs.length - 100);
    }
    localStorage.setItem('pi-monitor-debug-logs', JSON.stringify(existingLogs));
  } catch (error) {
    console.warn('Failed to save debug log to localStorage:', error);
  }
};

class UnifiedClient {
  constructor(options = {}) {
    logDebug('Initializing UnifiedClient', { options });
    
    // Resolve API base URL. Prefer explicit env, else use Nginx proxy (port 80) in production
    const envUrl = process.env.REACT_APP_SERVER_URL || process.env.REACT_APP_API_BASE_URL;
    const inferredUrl = (() => {
      const host = window.location.hostname;
      const isHttps = window.location.protocol === 'https:';
      // If running under CRA dev server (localhost:3000), default backend 5001
      if (host === 'localhost' || host === '127.0.0.1') {
        return `http://${host}:5001`;
      }
      // In production, use Nginx proxy on port 80 (no port number needed)
      if (host !== 'localhost' && host !== '127.0.0.1') {
        return `${isHttps ? 'https' : 'http'}://${host}`;
      }
      // Fallback to same-origin
      return `${isHttps ? 'https' : 'http'}://${host}`;
    })();
    const domainUrl = envUrl || inferredUrl;
    this.serverUrl = options.serverUrl || domainUrl;
    this.onConnectionChange = options.onConnectionChange || (() => {});
    this.onDataUpdate = options.onDataUpdate || (() => {});
    this.onError = options.onError || (() => {});
    this.connectionState = CONNECTION_STATES.DISCONNECTED;
    this.apiKey = localStorage.getItem('pi-monitor-api-key');
    
    logDebug('Client configuration', {
      serverUrl: this.serverUrl,
      hasApiKey: !!this.apiKey,
      domainUrl,
      hostname: window.location.hostname
    });
    
    this.httpClient = axios.create({
      baseURL: this.serverUrl.replace(/\/$/, ''),
      timeout: 10000
    });
    
    // Add request interceptor to include auth token and log requests
    this.httpClient.interceptors.request.use(
      (config) => {
        logDebug('HTTP Request', {
          method: config.method?.toUpperCase(),
          url: config.url,
          baseURL: config.baseURL,
          fullURL: `${config.baseURL}${config.url}`,
          headers: config.headers,
          data: config.data,
          params: config.params
        });
        
        if (this.apiKey) {
          config.headers.Authorization = `Bearer ${this.apiKey}`;
          logDebug('Added api key to request', { hasApiKey: !!this.apiKey });
        }
        return config;
      },
      (error) => {
        logDebug('Request interceptor error', { error: error.message }, 'error');
        return Promise.reject(error);
      }
    );
    
    // Add response interceptor to handle auth errors and log responses
    this.httpClient.interceptors.response.use(
      (response) => {
        logDebug('HTTP Response Success', {
          status: response.status,
          statusText: response.statusText,
          url: response.config.url,
          method: response.config.method?.toUpperCase(),
          data: response.data,
          headers: response.headers
        });
        return response;
      },
      async (error) => {
        logDebug('HTTP Response Error', {
          message: error.message,
          status: error.response?.status,
          statusText: error.response?.statusText,
          url: error.config?.url,
          method: error.config?.method?.toUpperCase(),
          responseData: error.response?.data,
          responseHeaders: error.response?.headers,
          requestData: error.config?.data,
          requestHeaders: error.config?.headers
        }, 'error');
        
        if (error.response?.status === 401) {
          logDebug('Received 401 Unauthorized, attempting re-authentication');
          // Token expired or invalid, try to re-authenticate
          try {
            await this.authenticate();
            // Retry the original request
            const originalRequest = error.config;
            if (this.apiKey) {
              originalRequest.headers.Authorization = `Bearer ${this.apiKey}`;
            }
            logDebug('Retrying original request after re-authentication', {
              url: originalRequest.url,
              method: originalRequest.method
            });
            return this.httpClient(originalRequest);
          } catch (authError) {
            logDebug('Re-authentication failed', { error: authError.message }, 'error');
            // Re-authentication failed
            this.setConnectionState(CONNECTION_STATES.ERROR);
            this.onError(authError);
          }
        }
        return Promise.reject(error);
      }
    );
    
    this.initializeConnection();
  }

  async initializeConnection() {
    try {
      if (!this.apiKey) {
        await this.authenticate();
      }
      await this.checkHealth();
      this.setConnectionState(CONNECTION_STATES.CONNECTED);
      this.startPolling();
    } catch (error) {
      console.error('Failed to initialize connection:', error);
      this.setConnectionState(CONNECTION_STATES.ERROR);
      this.onError(error);
    }
  }

  async authenticate() {
    try {
      const response = await this.httpClient.post('/api/auth/token', {
        api_key: this.apiKey || 'pi-monitor-api-key-2024'  // Use stored key or default
      });
      
      if (response.data.success) {
        // Store the API key if not already stored
        if (!this.apiKey) {
          this.apiKey = 'pi-monitor-api-key-2024';  // Default key
          localStorage.setItem('pi-monitor-api-key', this.apiKey);
        }
      } else {
        throw new Error('Authentication failed');
      }
    } catch (error) {
      throw new Error('Failed to authenticate');
    }
  }

  setConnectionState(state) {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.onConnectionChange(state);
    }
  }

  startPolling() {
    this.pollingInterval = setInterval(async () => {
      try {
        if (this.connectionState === CONNECTION_STATES.CONNECTED) {
          const stats = await this.getSystemStats();
          this.onDataUpdate({ type: 'periodic_update', data: stats });
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 5000);
  }

  async getSystemStats() {
    try {
      const response = await this.httpClient.get('/api/system');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getEnhancedSystemStats() {
    try {
      const response = await this.httpClient.get('/api/system/enhanced');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async checkHealth() {
    try {
      const response = await this.httpClient.get('/health');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getServices() {
    try {
      const response = await this.httpClient.get('/api/services');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async controlService(serviceName, action) {
    try {
      const response = await this.httpClient.post('/api/services', {
        service_name: serviceName,
        action: action
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getMetricsHistory(minutes = 60) {
    try {
      const response = await this.httpClient.get(`/api/metrics/history?minutes=${minutes}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getDatabaseStats() {
    try {
      const response = await this.httpClient.get('/api/metrics/database');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Network monitoring methods
  async getNetworkInfo() {
    try {
      const response = await this.httpClient.get('/api/network');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getNetworkStats() {
    try {
      const response = await this.httpClient.get('/api/network/stats');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Log viewing methods
  async getAvailableLogs() {
    try {
      const response = await this.httpClient.get('/api/logs');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async getLogContent(logName, maxLines = 100) {
    try {
      const response = await this.httpClient.get(`/api/logs/${logName}?lines=${maxLines}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async downloadLog(logName) {
    try {
      const response = await this.httpClient.get(`/api/logs/${logName}/download`, {
        responseType: 'text'
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async clearLog(logName) {
    try {
      const response = await this.httpClient.post(`/api/logs/${logName}/clear`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Power management methods
  async getPowerStatus() {
    try {
      logDebug('Getting power status from backend');
      const response = await this.httpClient.get('/api/power');
      logDebug('Power status response received', { 
        status: response.status,
        data: response.data 
      });
      return response.data;
    } catch (error) {
      logDebug('Failed to get power status', { 
        error: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      }, 'error');
      throw error;
    }
  }

  async executePowerAction(action, delay = 0) {
    try {
      logDebug('Executing power action', { action, delay });
      
      let endpoint = '';
      let data = { action, delay };
      
      switch (action) {
        case 'shutdown':
          endpoint = '/api/power/shutdown';
          break;
        case 'restart':
          endpoint = '/api/power/restart';
          break;
        case 'sleep':
          endpoint = '/api/power/sleep';
          break;
        default:
          const error = `Unknown power action: ${action}`;
          logDebug('Unknown power action requested', { action }, 'error');
          throw new Error(error);
      }
      
      logDebug('Power action endpoint determined', { 
        action, 
        endpoint, 
        fullUrl: `${this.serverUrl}${endpoint}`,
        data 
      });
      
      const response = await this.httpClient.post(endpoint, data);
      logDebug('Power action executed successfully', { 
        action,
        response: {
          status: response.status,
          data: response.data
        }
      });
      return response.data;
    } catch (error) {
      logDebug('Power action execution failed', { 
        action,
        delay,
        error: error.message,
        errorStatus: error.response?.status,
        errorResponse: error.response?.data,
        errorStack: error.stack
      }, 'error');
      throw error;
    }
  }

  async shutdown() {
    try {
      logDebug('Executing shutdown via legacy method');
      const response = await this.httpClient.post('/api/power/shutdown');
      logDebug('Shutdown executed successfully via legacy method', { 
        status: response.status,
        data: response.data 
      });
      return response.data;
    } catch (error) {
      logDebug('Shutdown failed via legacy method', { 
        error: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      }, 'error');
      throw error;
    }
  }

  async restart() {
    try {
      logDebug('Executing restart via legacy method');
      const response = await this.httpClient.post('/api/power/restart');
      logDebug('Restart executed successfully via legacy method', { 
        status: response.status,
        data: response.data 
      });
      return response.data;
    } catch (error) {
      logDebug('Restart failed via legacy method', { 
        error: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      }, 'error');
      throw error;
    }
  }

  async sleep() {
    try {
      logDebug('Executing sleep via legacy method');
      const response = await this.httpClient.post('/api/power/sleep');
      logDebug('Sleep executed successfully via legacy method', { 
        status: response.status,
        data: response.data 
      });
      return response.data;
    } catch (error) {
      logDebug('Sleep failed via legacy method', { 
        error: error.message,
        status: error.response?.status,
        responseData: error.response?.data
      }, 'error');
      throw error;
    }
  }

  // Utility methods
  async refresh() {
    try {
      const response = await this.httpClient.get('/api/refresh');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  getConnectionState() {
    return this.connectionState;
  }

  // Debug utility methods
  getDebugLogs() {
    try {
      const logs = JSON.parse(localStorage.getItem('pi-monitor-debug-logs') || '[]');
      return logs;
    } catch (error) {
      logDebug('Failed to retrieve debug logs', { error: error.message }, 'error');
      return [];
    }
  }

  clearDebugLogs() {
    try {
      localStorage.removeItem('pi-monitor-debug-logs');
      logDebug('Debug logs cleared');
      return true;
    } catch (error) {
      logDebug('Failed to clear debug logs', { error: error.message }, 'error');
      return false;
    }
  }

  getDebugSummary() {
    const logs = this.getDebugLogs();
    const summary = {
      totalLogs: logs.length,
      errorLogs: logs.filter(log => log.type === 'error').length,
      infoLogs: logs.filter(log => log.type === 'info').length,
      recentErrors: logs.filter(log => log.type === 'error').slice(-5),
      recentRequests: logs.filter(log => log.message.includes('HTTP Request')).slice(-5),
      recentResponses: logs.filter(log => log.message.includes('HTTP Response')).slice(-5)
    };
    return summary;
  }

  disconnect() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
    this.setConnectionState(CONNECTION_STATES.DISCONNECTED);
  }
}

export { UnifiedClient, CONNECTION_STATES }; 
