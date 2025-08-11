import { io } from 'socket.io-client';
import axios from 'axios';
import { z } from 'zod';

// Validation schemas using Zod
const SystemStatsSchema = z.object({
  timestamp: z.string(),
  cpu_percent: z.number(),
  memory_percent: z.number(),
  disk_percent: z.number(),
  temperature: z.number(),
  uptime: z.string(),
  network: z.object({
    bytes_sent: z.number(),
    bytes_recv: z.number(),
    packets_sent: z.number(),
    packets_recv: z.number(),
  }),
});

const ServiceSchema = z.object({
  name: z.string(),
  status: z.string(),
  active: z.boolean().optional(),
  enabled: z.boolean().optional(),
  description: z.string().optional(),
});

// Connection states
const CONNECTION_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error',
};

class UnifiedClient {
  constructor(options = {}) {
    this.serverUrl = options.serverUrl || `http://${window.location.hostname}:5001`;
    this.onConnectionChange = options.onConnectionChange || (() => {});
    this.onDataUpdate = options.onDataUpdate || (() => {});
    
    // Connection state
    this.connectionState = CONNECTION_STATES.DISCONNECTED;
    this.socket = null;
    this.authToken = localStorage.getItem('pi-monitor-token');
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1000; // Start with 1 second
    
    // Data cache
    this.dataCache = {
      systemStats: JSON.parse(localStorage.getItem('pi-monitor-cache-systemStats') || 'null'),
      services: JSON.parse(localStorage.getItem('pi-monitor-cache-services') || '[]'),
      lastUpdate: localStorage.getItem('pi-monitor-cache-lastUpdate'),
    };
    
    // Axios instance with interceptors
    this.httpClient = axios.create({
      baseURL: this.serverUrl,
      timeout: 10000,
    });
    
    this.setupHttpInterceptors();
    this.initializeConnection();
  }

  setupHttpInterceptors() {
    // Request interceptor to add auth token
    this.httpClient.interceptors.request.use(
      (config) => {
        if (this.authToken) {
          config.headers.Authorization = `Bearer ${this.authToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.httpClient.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.handleAuthError();
        }
        return Promise.reject(error);
      }
    );
  }

  async initializeConnection() {
    // First, try to authenticate if no token exists
    if (!this.authToken) {
      await this.authenticate();
    }
    
    // Initialize WebSocket connection
    this.connectWebSocket();
  }

  async authenticate() {
    try {
      const response = await this.httpClient.post('/api/auth/token');
      this.authToken = response.data.access_token;
      localStorage.setItem('pi-monitor-token', this.authToken);
      console.log('Authentication successful');
    } catch (error) {
      console.error('Authentication failed:', error);
      throw new Error('Failed to authenticate with server');
    }
  }

  handleAuthError() {
    this.authToken = null;
    localStorage.removeItem('pi-monitor-token');
    this.authenticate().catch(console.error);
  }

  connectWebSocket() {
    if (this.socket) {
      this.socket.disconnect();
    }

    this.setConnectionState(CONNECTION_STATES.CONNECTING);

    try {
      this.socket = io(this.serverUrl, {
        auth: {
          token: this.authToken,
        },
        transports: ['websocket', 'polling'],
        upgrade: true,
        rememberUpgrade: true,
        timeout: 10000,
        reconnection: true,
        reconnectionDelay: this.reconnectDelay,
        reconnectionAttempts: this.maxReconnectAttempts,
      });

      this.setupWebSocketListeners();
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.setConnectionState(CONNECTION_STATES.ERROR);
      this.scheduleReconnect();
    }
  }

  setupWebSocketListeners() {
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.setConnectionState(CONNECTION_STATES.CONNECTED);
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.setConnectionState(CONNECTION_STATES.DISCONNECTED);
      
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, try to reconnect
        this.scheduleReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.setConnectionState(CONNECTION_STATES.ERROR);
      this.scheduleReconnect();
    });

    this.socket.on('system_update', (data) => {
      this.handleSystemUpdate(data);
    });

    // Heartbeat to keep connection alive
    this.socket.on('pong', () => {
      console.debug('Received pong from server');
    });

    // Send periodic ping
    setInterval(() => {
      if (this.socket && this.socket.connected) {
        this.socket.emit('ping');
      }
    }, 30000); // Every 30 seconds
  }

  scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.setConnectionState(CONNECTION_STATES.ERROR);
      return;
    }

    setTimeout(() => {
      console.log(`Attempting to reconnect (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
      this.reconnectAttempts++;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000); // Exponential backoff, max 30s
      this.connectWebSocket();
    }, this.reconnectDelay);
  }

  handleSystemUpdate(data) {
    try {
      // Validate and cache the data
      if (data.type === 'initial_stats' || data.type === 'periodic_update') {
        const validatedStats = SystemStatsSchema.parse(data.data);
        this.dataCache.systemStats = validatedStats;
        this.dataCache.lastUpdate = new Date().toISOString();
        
        // Update localStorage cache
        localStorage.setItem('pi-monitor-cache-systemStats', JSON.stringify(validatedStats));
        localStorage.setItem('pi-monitor-cache-lastUpdate', this.dataCache.lastUpdate);
      }
      
      // Notify listeners
      this.onDataUpdate(data);
    } catch (error) {
      console.error('Error handling system update:', error);
    }
  }

  setConnectionState(state) {
    if (this.connectionState !== state) {
      this.connectionState = state;
      this.onConnectionChange(state);
    }
  }

  // Public API methods

  /**
   * Get system statistics
   * @returns {Promise<Object>} System stats
   */
  async getSystemStats() {
    try {
      // Try WebSocket first if connected
      if (this.connectionState === CONNECTION_STATES.CONNECTED && this.dataCache.systemStats) {
        return this.dataCache.systemStats;
      }

      // Fallback to REST API
      const response = await this.httpClient.get('/api/system');
      const validatedStats = SystemStatsSchema.parse(response.data);
      
      // Update cache
      this.dataCache.systemStats = validatedStats;
      this.dataCache.lastUpdate = new Date().toISOString();
      localStorage.setItem('pi-monitor-cache-systemStats', JSON.stringify(validatedStats));
      localStorage.setItem('pi-monitor-cache-lastUpdate', this.dataCache.lastUpdate);
      
      return validatedStats;
    } catch (error) {
      console.error('Error fetching system stats:', error);
      
      // Return cached data if available
      if (this.dataCache.systemStats) {
        console.warn('Returning cached system stats due to error');
        return this.dataCache.systemStats;
      }
      
      throw error;
    }
  }

  /**
   * Get services list
   * @returns {Promise<Array>} Services list
   */
  async getServices() {
    try {
      const response = await this.httpClient.get('/api/services');
      const services = response.data.services;
      
      // Validate each service
      const validatedServices = services.map(service => ServiceSchema.parse(service));
      
      // Update cache
      this.dataCache.services = validatedServices;
      localStorage.setItem('pi-monitor-cache-services', JSON.stringify(validatedServices));
      
      return validatedServices;
    } catch (error) {
      console.error('Error fetching services:', error);
      
      // Return cached data if available
      if (this.dataCache.services.length > 0) {
        console.warn('Returning cached services due to error');
        return this.dataCache.services;
      }
      
      throw error;
    }
  }

  /**
   * Control a service
   * @param {string} serviceName - Name of the service
   * @param {string} action - Action to perform (start, stop, restart, etc.)
   * @returns {Promise<Object>} Action result
   */
  async controlService(serviceName, action) {
    try {
      const response = await this.httpClient.post('/api/services', {
        service_name: serviceName,
        action: action,
      });
      return response.data;
    } catch (error) {
      console.error(`Error controlling service ${serviceName}:`, error);
      throw error;
    }
  }

  /**
   * Execute power action
   * @param {string} action - Power action (shutdown, restart)
   * @param {number} delay - Delay in seconds
   * @returns {Promise<Object>} Action result
   */
  async executePowerAction(action, delay = 0) {
    try {
      const response = await this.httpClient.post('/api/power', {
        action: action,
        delay: delay,
      });
      return response.data;
    } catch (error) {
      console.error(`Error executing power action ${action}:`, error);
      throw error;
    }
  }

  /**
   * Check server health
   * @returns {Promise<Object>} Health status
   */
  async checkHealth() {
    try {
      const response = await this.httpClient.get('/health');
      return response.data;
    } catch (error) {
      console.error('Error checking server health:', error);
      throw error;
    }
  }

  /**
   * Get cached data
   * @param {string} key - Cache key
   * @returns {any} Cached data
   */
  getCachedData(key) {
    return this.dataCache[key];
  }

  /**
   * Get connection state
   * @returns {string} Current connection state
   */
  getConnectionState() {
    return this.connectionState;
  }

  /**
   * Get last update timestamp
   * @returns {string|null} Last update timestamp
   */
  getLastUpdate() {
    return this.dataCache.lastUpdate;
  }

  /**
   * Manually trigger reconnection
   */
  reconnect() {
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
    this.connectWebSocket();
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.setConnectionState(CONNECTION_STATES.DISCONNECTED);
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.dataCache = {
      systemStats: null,
      services: [],
      lastUpdate: null,
    };
    localStorage.removeItem('pi-monitor-cache-systemStats');
    localStorage.removeItem('pi-monitor-cache-services');
    localStorage.removeItem('pi-monitor-cache-lastUpdate');
  }
}

export { UnifiedClient, CONNECTION_STATES };
