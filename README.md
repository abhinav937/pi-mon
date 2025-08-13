# Pi Monitor - Simple Raspberry Pi Monitoring

A dead simple Raspberry Pi monitoring system that replaces complex frameworks with a basic Python HTTP server, systemd, and nginx.

## ✨ What's New in v2.0

- **No FastAPI** - Just basic Python HTTP server
- **No Docker required** - systemd service + nginx (Docker optional in legacy branch)
- **JSON configuration** - All settings in one file
- **Minimal dependencies** - Only psutil for system monitoring
- **Simple deployment** - One script to rule them all
- **Subdomain support** - Easy custom domain setup
- **🔒 Enhanced Security** - HTTPS/SSL, security headers, threat detection

## 🚀 Enhanced Features (RPi-Monitor Inspired)

- **Real-time Metrics Collection** - Continuous data collection every 5 seconds
- **Historical Data Storage** - Up to 1000 data points with smart aggregation
- **Enhanced System Monitoring** - Temperature, disk I/O, network statistics
- **Advanced Charts** - Time-range selectable historical charts
- **Detailed System Information** - CPU details, memory breakdown, network interfaces
- **Live Dashboard Updates** - Real-time metrics without page refresh

## 🔒 Security Features

Pi Monitor now includes enterprise-grade security features:

- **HTTPS/SSL Encryption** - Self-signed certificates for development, production-ready for CA certificates
- **Security Headers** - XSS protection, clickjacking prevention, content security policy
- **Rate Limiting** - Configurable request limits with IP-based tracking
- **Threat Detection** - XSS, SQL injection, path traversal, and header injection protection
- **Input Validation** - Content length limits, file type restrictions, input sanitization
- **Authentication Security** - Failed attempt tracking, IP lockouts, CSRF protection

### Running the Secure Server

```bash
# Quick deployment with SSL certificates
cd scripts
./deploy_secure.sh          # Linux/macOS
deploy_secure.bat           # Windows

# Or manual setup
cd backend
python secure_server.py
```

### Security Configuration

```bash
# View security settings
cat backend/security_config.json

# Test security features
python test_security.py
```

For detailed security information, see [SECURITY_README.md](SECURITY_README.md).

## 🚀 Quick Start

### 1. Check Configuration

```bash
# View current configuration
python config.py

# Edit configuration
nano config.json
```

### 2. Deploy Everything (No Docker)

```bash
# Deploy backend, frontend, and subdomain
./deploy.sh

# Or deploy with enhanced security
./scripts/deploy_secure.sh
```

### 3. Access Your System

- **Backend API**: http://localhost:5001 (or https://localhost:5001 for secure server)
- **Frontend Dashboard**: http://localhost:80 (or https://localhost:443 for secure deployment)
- **Health Check**: http://localhost:5001/health

## 🌐 Subdomain Configuration

Pi Monitor automatically configures your custom subdomain `pi.cabhinav.com` to point to your Raspberry Pi's static IP `65.36.123.68:80`.

### What the Deploy Script Does

The `./deploy.sh` script automatically:
- ✅ Sets up Nginx configuration for `pi.cabhinav.com`
- ✅ Builds and deploys your React frontend
- ✅ Configures API proxying to your backend
- ✅ Sets up firewall rules (port 80 open)
- ✅ Creates systemd services
- ✅ Tests the configuration

**Enhanced Security Deployment** (`./scripts/deploy_secure.sh`):
- ✅ Generates SSL certificates
- ✅ Configures HTTPS with security headers
- ✅ Sets up threat detection and rate limiting
- ✅ Creates secure backend service

### DNS Setup Required

**You still need to configure DNS manually:**

1. **Log into your domain registrar** (e.g., Namecheap, GoDaddy, Cloudflare)
2. **Navigate to DNS management** for `cabhinav.com`
3. **Add an A record**:
   ```
   Type: A
   Name: pi
   Value: 65.36.123.68
   TTL: 300
   ```

### After DNS Configuration

Once DNS propagates (usually 15 minutes to 2 hours), your site will be accessible at:
- **HTTP**: http://pi.cabhinav.com
- **HTTPS**: https://pi.cabhinav.com (with secure deployment)

### Testing Your Setup

```bash
# Test local access
curl -I http://localhost

# Test HTTPS (secure deployment)
curl -I -k https://localhost

# Test subdomain locally
curl -H "Host: pi.cabhinav.com" http://127.0.0.1

# Test from external network
curl -I http://pi.cabhinav.com
curl -I -k https://pi.cabhinav.com
```

### Useful Commands

```bash
# View Nginx logs
sudo tail -f /var/log/nginx/pi.cabhinav.com.access.log

# Check Nginx status
sudo systemctl status nginx

# Restart services
sudo systemctl restart nginx
sudo systemctl restart pi-monitor-backend.service
```

## 📁 Project Structure

```
pi-mon/
├── config.json               # All configuration settings
├── config.py                 # Configuration loader
├── deploy.sh                 # One-shot deploy (venv + systemd + nginx)
├── deploy_pi.sh              # Backend-only deploy (venv + systemd)
├── deploy_domain.sh          # Domain + SSL (nginx + certbot)
├── scripts/
│   └── setup_venv_systemd.sh # Helper for no-Docker setup
├── nginx/
│   └── pi-monitor.conf       # nginx site config (HTTP)
├── backend/
│   ├── simple_server.py      # Simple HTTP server
│   ├── env.example           # Example env (.env)
│   └── requirements.txt      # Python dependencies
└── frontend/                 # React frontend
```

## ⚙️ Configuration

All settings are in `config.json`:

```json
{
  "ports": {
    "backend": 5001,
    "frontend": 80,
    "frontend_dev": 3000
  },
  "services": {
    "backend": {
      "name": "pi-monitor-backend",
      "image": "pi-monitor-backend"
    }
  }
}
```

## 🔐 Authentication

Pi Monitor now uses **API Key authentication** for secure access to protected endpoints.

### Setting Up Your API Key

1. **Generate a secure API key:**
   ```bash
   python generate_api_key.py
   ```

2. **Set the API key as an environment variable:**
   ```bash
   export PI_MONITOR_API_KEY='your-generated-api-key'
   ```

3. **Or create a .env file in the backend directory:**
   ```bash
   cd backend
   cp env.example .env
   # Edit .env and set your API key
   ```

### Default API Key (Development Only)
For development/testing, the system uses a default API key: `pi-monitor-api-key-2024`

⚠️ **Security Warning**: Change this default key in production!

## 🔧 Available Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/` | GET | Basic status | No |
| `/health` | GET | Health check | No |
| `/api/auth/token` | POST | Validate API key | No |
| `/api/system` | GET | System stats | Yes |
| `/api/system/enhanced` | GET | Enhanced system stats | Yes |
| `/api/system` | GET | System stats with history | Yes |
| `/api/services` | GET | Services status | Yes |
| `/api/services` | POST | Control services | Yes |
| `/api/power` | GET | Power status | Yes |
| `/api/power` | POST | Power actions | Yes |

## 🔄 Managing Services

```bash
# Backend service
sudo systemctl status pi-monitor-backend
sudo systemctl restart pi-monitor-backend
sudo journalctl -u pi-monitor-backend -n 100 -f

# nginx
sudo systemctl status nginx
sudo systemctl restart nginx
```

## 🧪 Testing

```bash
# Test all endpoints
./test_api.sh

# Test specific endpoint
curl http://localhost:5001/health
curl -X POST http://localhost:5001/api/auth/token
```

## 🔄 Updates

```bash
# Pull latest changes and redeploy
git pull
./deploy.sh
```

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   sudo lsof -i:5001
   sudo fuser -k 5001/tcp
   ```

2. **Service won't start**
   ```bash
   sudo systemctl status pi-monitor-backend
   sudo journalctl -u pi-monitor-backend -n 200 -f
   ```

3. **Health check failing**
   ```bash
   curl -v http://localhost:5001/health
   ```

### Logs

```bash
# Follow backend logs in real-time
sudo journalctl -u pi-monitor-backend -f
```

## 🏗️ Development

### Local Development

```bash
# Run backend locally
cd backend
pip install -r requirements.txt
python simple_server.py

# Run frontend locally
cd frontend
npm install
npm start
```

### Frontend Development

```bash
cd frontend
npm start
```

## 🔒 Security Notes

- **Demo authentication** - Always succeeds for demo purposes
- **In-memory tokens** - Tokens lost on restart
- **No HTTPS** - HTTP only (add reverse proxy for production)
- **No rate limiting** - Add if needed for production

## 🚀 Production Considerations

- Add HTTPS with reverse proxy (nginx/traefik)
- Implement proper authentication
- Add rate limiting
- Use external token storage
- Add monitoring and alerting
- Implement proper logging

## 📊 System Monitoring

The backend provides real-time system information:

- **CPU usage** - Current CPU percentage
- **Memory usage** - RAM usage percentage
- **Disk usage** - Storage usage percentage
- **Temperature** - System temperature (if available)
- **Uptime** - System uptime
- **Network stats** - Bytes sent/received, packets

## 🎯 Service Management

Control system services via systemctl:

- **Start/stop/restart** services
- **Check status** of services
- **Common services**: ssh, nginx, apache2, mosquitto

## ⚡ Power Management

Safe power control with delay options:

- **Shutdown** with configurable delay
- **Restart** with configurable delay
- **Safety**: Always use delay > 0 in production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with Python's built-in `http.server`
- Served with nginx
- Frontend powered by React
- System monitoring with psutil

---

**Why Simple?**

- **No FastAPI complexity** - Just basic HTTP handlers
- **No external dependencies** - Only psutil for system monitoring
- **No Redis/MQTT** - Simple in-memory token storage
- **No virtual environments** - Direct Python execution
- **Easy debugging** - Simple code, clear flow
- **Fast startup** - No heavy framework initialization

## 🧰 Running Without Docker (venv + systemd + nginx)

You can run the backend and frontend without containers. A helper script sets up a Python venv, builds the React app, installs nginx, and creates a systemd service.

### One‑shot setup

```bash
cd /home/pi/pi-mon
sudo bash scripts/setup_venv_systemd.sh
```

What it does:
- Creates venv in `.venv` and installs `backend/requirements.txt`
- Builds the frontend and deploys it to `/var/www/pi-monitor`
- Installs nginx, serves the static site, and proxies `/api` to `127.0.0.1:5001`
- Installs and enables `pi-monitor-backend.service` using the venv

### Manual steps (if you prefer)

1. Backend venv:
```bash
cd backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -r requirements.txt
cp env.example .env  # set PI_MONITOR_API_KEY
```

2. Systemd service (edit paths/user as needed):
Place `pi-monitor.service` in `/etc/systemd/system/pi-monitor-backend.service` and run:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pi-monitor-backend.service
```

3. Frontend build and nginx:
```bash
cd frontend
npm ci && npm run build
sudo mkdir -p /var/www/pi-monitor
sudo rsync -a build/ /var/www/pi-monitor/
sudo cp nginx/pi-monitor.conf /etc/nginx/sites-available/pi-monitor
sudo ln -sf /etc/nginx/sites-available/pi-monitor /etc/nginx/sites-enabled/pi-monitor
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx && sudo systemctl enable nginx
```

Access: `http://<host>/` (frontend), API proxied at `http://<host>/api/*`.

