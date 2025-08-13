// Production Configuration
// This configuration uses HTTP on port 80 instead of HTTPS
export const PRODUCTION_CONFIG = {
  API_BASE_URL: 'http://65.36.123.68',
  BACKEND_PORT: 80, // Use nginx HTTP proxy port
  FRONTEND_PORT: 80,
  ENDPOINTS: {
    HEALTH: 'http://65.36.123.68/health',
    AUTH: 'http://65.36.123.68/api/auth/token',
    SYSTEM: 'http://65.36.123.68/api/system',
    SYSTEM_ENHANCED: 'http://65.36.123.68/api/system/enhanced',
    METRICS: 'http://65.36.123.68/api/metrics',
    SERVICES: 'http://65.36.123.68/api/services',
    POWER: 'http://65.36.123.68/api/power',
    POWER_SHUTDOWN: 'http://65.36.123.68/api/power/shutdown',
    POWER_RESTART: 'http://65.36.123.68/api/power/restart',
    POWER_SLEEP: 'http://65.36.123.68/api/power/sleep',
    NETWORK: 'http://65.36.123.68/api/network',
    NETWORK_STATS: 'http://65.36.123.68/api/network/stats',
    LOGS: 'http://65.36.123.68/api/logs',
    REFRESH: 'http://65.36.123.68/api/refresh'
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
