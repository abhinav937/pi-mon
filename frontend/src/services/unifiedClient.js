/* eslint-disable no-console */
import axios from 'axios';

const CONNECTION_STATES = {
  DISCONNECTED: 'disconnected',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  ERROR: 'error'
};

const DEBUG_ENABLED = process.env.NODE_ENV !== 'production' || (typeof window !== 'undefined' && localStorage.getItem('pi-monitor-debug') === '1');

const logDebug = (message, data = null, type = 'info') => {
  if (!DEBUG_ENABLED && type !== 'error') return;
  const timestamp = new Date().toISOString();
  const logEntry = { timestamp, type, message, data };
  try { if (DEBUG_ENABLED || type === 'error') console.log(`[UnifiedClient Debug] ${message}`, logEntry); } catch (_) {}
  try {
    if (!DEBUG_ENABLED && type !== 'error') return;
    const existingLogs = JSON.parse(localStorage.getItem('pi-monitor-debug-logs') || '[]');
    existingLogs.push(logEntry);
    if (existingLogs.length > 100) existingLogs.splice(0, existingLogs.length - 100);
    localStorage.setItem('pi-monitor-debug-logs', JSON.stringify(existingLogs));
  } catch (_) {}
};

class UnifiedClient {
  constructor(options = {}) {
    logDebug('Initializing UnifiedClient', { options });
    
    // Always prefer same-origin to avoid mixed content when served over HTTPS through Nginx
    const sameOrigin = `${window.location.protocol}//${window.location.host}`; // includes port if present
    const envUrl = process.env.REACT_APP_SERVER_URL || process.env.REACT_APP_API_BASE_URL;
    const serverBase = options.serverUrl || envUrl || sameOrigin;

    this.serverUrl = serverBase.replace(/\/$/, '');
    this.onConnectionChange = options.onConnectionChange || (() => {});
    this.onDataUpdate = options.onDataUpdate || (() => {});
    this.onError = options.onError || (() => {});
    this.connectionState = CONNECTION_STATES.DISCONNECTED;
    this.apiKey = localStorage.getItem('pi-monitor-api-key');
    this.dataListeners = new Set();
    this.latestStats = null;
    
    logDebug('Client configuration', {
      serverUrl: this.serverUrl,
      hasApiKey: !!this.apiKey,
      hostname: window.location.hostname,
      protocol: window.location.protocol
    });
    
    this.httpClient = axios.create({
      baseURL: this.serverUrl,
      timeout: 10000,
      headers: {
        'Cache-Control': 'no-cache, no-store, max-age=0, must-revalidate',
        Pragma: 'no-cache',
        Expires: '0'
      }
    });
    
    this.httpClient.interceptors.request.use(
      (config) => {
        if (this.apiKey) config.headers.Authorization = `Bearer ${this.apiKey}`;
        return config;
      },
      (error) => Promise.reject(error)
    );
    
    this.httpClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          try {
            await this.authenticate();
            const originalRequest = error.config;
            if (this.apiKey) originalRequest.headers.Authorization = `Bearer ${this.apiKey}`;
            return this.httpClient(originalRequest);
          } catch (authError) {
            this.setConnectionState(CONNECTION_STATES.ERROR);
            this.onError(authError);
          }
        } else if (error.response?.status === 429) {
          // Rate limited - increase polling interval temporarily
          logDebug('Rate limited (429), increasing polling interval', { status: error.response.status });
          this.frontendPollMs = Math.max(this.frontendPollMs * 2, 30000); // Double the interval, max 30 seconds
          this.schedulePolling();
          // Don't throw error, just log it
          return Promise.resolve({ data: null, status: 429 });
        }
        return Promise.reject(error);
      }
    );
    
    this.backendInfo = null;
    this.backendHeaders = {};

    try {
      const savedSettingsRaw = localStorage.getItem('pi-monitor-settings');
      const savedSettings = savedSettingsRaw ? JSON.parse(savedSettingsRaw) : null;
      this.frontendPollMs = Math.max(1000, Number(savedSettings?.refreshInterval) || 5000);
    } catch (_) {
      this.frontendPollMs = 5000;
    }

    this.initializeConnection();
  }

  async initializeConnection() {
    try {
      if (!this.apiKey) {
        await this.authenticate();
      }
      
      // Add delay between requests to avoid overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const health = await this.checkHealth();
      try { if (health && health.__headers) this.backendHeaders = health.__headers; } catch (_) {}
      
      // Add delay between requests
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try { this.backendInfo = await this.getVersion(); } catch (_) {}
      this.setConnectionState(CONNECTION_STATES.CONNECTED);
      
      // Add delay before getting initial stats
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      try { const initialStats = await this.getSystemStats(); this.emitDataUpdate({ type: 'initial_stats', data: initialStats }); } catch (_) {}
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
        api_key: this.apiKey || 'pi-monitor-api-key-2024'
      });
      if (response.data?.success) {
        if (!this.apiKey) {
          this.apiKey = 'pi-monitor-api-key-2024';
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

  startPolling() { this.schedulePolling(); }
  schedulePolling() {
    if (this.pollingInterval) clearInterval(this.pollingInterval);
    const intervalMs = Math.max(1000, Number(this.frontendPollMs) || 15000); // Increased from 5000ms to 15000ms
    this.pollingInterval = setInterval(async () => {
      try {
        if (this.connectionState === CONNECTION_STATES.CONNECTED) {
          const stats = await this.getSystemStats();
          this.emitDataUpdate({ type: 'periodic_update', data: stats });
        }
      } catch (_) {}
    }, intervalMs);
  }

  setFrontendPollingInterval(intervalMs) {
    try { this.frontendPollMs = Math.max(5000, Number(intervalMs) || 15000); this.schedulePolling(); return true; } catch { return false; }
  }

  async getSystemStats() { const r = await this.httpClient.get('/api/system', { params: { _ts: Date.now() } }); return r.data; }
  async getSystemInfo() { const r = await this.httpClient.get('/api/system/info'); return r.data; }
  async getEnhancedSystemStats() { const r = await this.httpClient.get('/api/system/enhanced', { params: { _ts: Date.now() } }); return r.data; }
  async checkHealth() { const r = await this.httpClient.get('/health'); const d = r.data || {}; d.__headers = r.headers || {}; return d; }
  async getVersion() { const r = await this.httpClient.get('/api/version'); this.backendHeaders = r.headers || {}; return r.data; }
  getBackendInfo() { return { info: this.backendInfo, headers: this.backendHeaders }; }
  async getServices() { const r = await this.httpClient.get('/api/services'); return r.data; }
  async controlService(serviceName, action) { const r = await this.httpClient.post('/api/services', { service_name: serviceName, action }); return r.data; }
  async getMetricsHistory(minutes=60) { const r = await this.httpClient.get(`/api/metrics/history?minutes=${minutes}`, { params: { _ts: Date.now() } }); return r.data; }
  async getMetricsRange({ start, end, limit, offset } = {}) {
      const params = new URLSearchParams();
      if (start != null) params.set('start', String(start));
      if (end != null) params.set('end', String(end));
      if (limit != null) params.set('limit', String(limit));
      if (offset != null) params.set('offset', String(offset));
      const qs = params.toString();
      const url = `/api/metrics/range${qs ? `?${qs}` : ''}`;
    const r = await this.httpClient.get(url); return r.data;
  }
  async getDatabaseStats() { const r = await this.httpClient.get('/api/metrics/database'); return r.data; }
  async exportMetrics() { const r = await this.httpClient.get('/api/metrics/export'); return r.data; }
  async clearMetrics() { const r = await this.httpClient.post('/api/metrics/clear'); return r.data; }
  async updateMetricsInterval(intervalSeconds) { const r = await this.httpClient.post('/api/metrics/interval', { interval: intervalSeconds }); return r.data; }
  async getMetricsInterval() { const r = await this.httpClient.get('/api/metrics/interval'); return r.data; }
  async updateDataRetention(retentionHours) { const r = await this.httpClient.post('/api/metrics/retention', { retention_hours: retentionHours }); return r.data; }
  async getDataRetention() { const r = await this.httpClient.get('/api/metrics/retention'); return r.data; }
  async getNetworkInfo() { const r = await this.httpClient.get('/api/network'); return r.data; }
  async getNetworkStats() { const r = await this.httpClient.get('/api/network/stats'); return r.data; }
  async getAvailableLogs() { const r = await this.httpClient.get('/api/logs'); return r.data; }
  async getLogContent(logName, maxLines=100) { const r = await this.httpClient.get(`/api/logs/${logName}?lines=${maxLines}`); return r.data; }
  async downloadLog(logName) { const r = await this.httpClient.get(`/api/logs/${logName}/download`, { responseType: 'text' }); return r.data; }
  async clearLog(logName) { const r = await this.httpClient.post(`/api/logs/${logName}/clear`); return r.data; }
  async getPowerStatus() { const r = await this.httpClient.get('/api/power'); return r.data; }
  async executePowerAction(action, delay=0) { const map = { shutdown:'/api/power/shutdown', restart:'/api/power/restart', sleep:'/api/power/sleep' }; const endpoint = map[action]; if (!endpoint) throw new Error(`Unknown power action: ${action}`); const r = await this.httpClient.post(endpoint, { action, delay }); return r.data; }
  async shutdown() { const r = await this.httpClient.post('/api/power/shutdown'); return r.data; }
  async restart() { const r = await this.httpClient.post('/api/power/restart'); return r.data; }
  async sleep() { const r = await this.httpClient.post('/api/power/sleep'); return r.data; }
  async refresh() { const r = await this.httpClient.get('/api/refresh'); return r.data; }
  getConnectionState() { return this.connectionState; }

  addDataListener(listener) { if (typeof listener !== 'function') return () => {}; this.dataListeners.add(listener); return () => { try { this.dataListeners.delete(listener); } catch {} }; }
  emitDataUpdate(payload) { try { const data = payload?.data ?? payload; if (data && typeof data === 'object') this.latestStats = data; } catch {} this.dataListeners.forEach((l)=>{ try{ l(payload);}catch{} }); if (this.onDataUpdate && typeof this.onDataUpdate === 'function') { try { this.onDataUpdate(payload); } catch {} } }
  getLatestStats() { return this.latestStats; }
}

export { UnifiedClient, CONNECTION_STATES }; 
