// Production Configuration
export const PRODUCTION_CONFIG = {
  API_BASE_URL: 'http://65.36.123.68',
  BACKEND_PORT: 5001,
  FRONTEND_PORT: 80,
  ENDPOINTS: {
    HEALTH: 'http://65.36.123.68:5001/health',
    AUTH: 'http://65.36.123.68:5001/api/auth/token',
    SYSTEM: 'http://65.36.123.68:5001/api/system',
    METRICS: 'http://65.36.123.68:5001/api/metrics',
    SERVICES: 'http://65.36.123.68:5001/api/services',
    POWER: 'http://65.36.123.68:5001/api/power',
    NETWORK: 'http://65.36.123.68:5001/api/network',
    LOGS: 'http://65.36.123.68:5001/api/logs'
  },
  POLLING_INTERVAL: 5000,
  TIMEOUT: 10000
};

export default PRODUCTION_CONFIG;
