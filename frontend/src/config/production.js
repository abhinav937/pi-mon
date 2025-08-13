// Production Configuration
// This configuration uses the nginx proxy on port 443 (HTTPS) instead of HTTP on port 80
export const PRODUCTION_CONFIG = {
  API_BASE_URL: 'https://65.36.123.68',
  BACKEND_PORT: 443, // Use nginx HTTPS proxy port
  FRONTEND_PORT: 443,
  ENDPOINTS: {
    HEALTH: 'https://65.36.123.68/health',
    AUTH: 'https://65.36.123.68/api/auth/token',
    SYSTEM: 'https://65.36.123.68/api/system',
    SYSTEM_ENHANCED: 'https://65.36.123.68/api/system/enhanced',
    METRICS: 'https://65.36.123.68/api/metrics',
    SERVICES: 'https://65.36.123.68/api/services',
    POWER: 'https://65.36.123.68/api/power',
    POWER_SHUTDOWN: 'https://65.36.123.68/api/power/shutdown',
    POWER_RESTART: 'https://65.36.123.68/api/power/restart',
    POWER_SLEEP: 'https://65.36.123.68/api/power/sleep',
    NETWORK: 'https://65.36.123.68/api/network',
    NETWORK_STATS: 'https://65.36.123.68/api/network/stats',
    LOGS: 'https://65.36.123.68/api/logs',
    REFRESH: 'https://65.36.123.68/api/refresh'
  },
  POLLING_INTERVAL: 5000,
  TIMEOUT: 10000,
  // Debug configuration
  DEBUG: {
    LOG_REQUESTS: true,
    LOG_RESPONSES: true,
    LOG_ERRORS: true
  }
};

export default PRODUCTION_CONFIG;
