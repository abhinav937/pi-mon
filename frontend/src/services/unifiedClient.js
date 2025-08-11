import axios from 'axios';

const CONNECTION_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

class UnifiedClient {
  constructor(options = {}) {
    this.serverUrl = options.serverUrl || `http://${window.location.hostname}:5001`;
    this.onConnectionChange = options.onConnectionChange || (() => {});
    this.onDataUpdate = options.onDataUpdate || (() => {});
    this.onError = options.onError || (() => {});
    this.connectionState = CONNECTION_STATES.DISCONNECTED;
    this.authToken = localStorage.getItem('pi-monitor-token');
    this.httpClient = axios.create({
      baseURL: this.serverUrl,
      timeout: 10000
    });
    this.initializeConnection();
  }

  async initializeConnection() {
    try {
      if (!this.authToken) {
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
        username: 'abhinav',
        password: 'kavachi'
      });
      this.authToken = response.data.access_token;
      localStorage.setItem('pi-monitor-token', this.authToken);
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
      const response = await this.httpClient.post(`/api/services/${serviceName}/${action}`);
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
      const response = await this.httpClient.delete(`/api/logs/${logName}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Power management methods
  async getPowerStatus() {
    try {
      const response = await this.httpClient.get('/api/power/status');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async shutdown() {
    try {
      const response = await this.httpClient.post('/api/power/shutdown');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async restart() {
    try {
      const response = await this.httpClient.post('/api/power/restart');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  async sleep() {
    try {
      const response = await this.httpClient.post('/api/power/sleep');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  // Utility methods
  async refresh() {
    try {
      const response = await this.httpClient.post('/api/refresh');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  getConnectionState() {
    return this.connectionState;
  }

  disconnect() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
    this.setConnectionState(CONNECTION_STATES.DISCONNECTED);
  }
}

export { UnifiedClient, CONNECTION_STATES }; 
