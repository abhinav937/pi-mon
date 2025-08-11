# Pi Monitor - Simple Raspberry Pi Monitoring

A **dead simple** Raspberry Pi monitoring system that replaces complex FastAPI setups with basic Python HTTP servers and Docker containers.

## ✨ What's New in v2.0

- **No FastAPI** - Just basic Python HTTP server
- **No system services** - Docker containers only
- **JSON configuration** - All settings in one file
- **Minimal dependencies** - Only psutil for system monitoring
- **Simple deployment** - One script to rule them all

## 🚀 Quick Start

### 1. Check Configuration

```bash
# View current configuration
python config.py

# Edit configuration
nano config.json
```

### 2. Deploy Everything

```bash
# Deploy backend and frontend
./deploy.sh

# Or use Docker Compose
docker-compose up -d
```

### 3. Access Your System

- **Backend API**: http://localhost:5001
- **Frontend Dashboard**: http://localhost:80
- **Health Check**: http://localhost:5001/health

## 📁 Project Structure

```
pi-mon/
├── config.json              # All configuration settings
├── config.py                # Configuration loader
├── deploy.sh                # Simple deployment script
├── docker-compose.yml       # Production setup
├── docker-compose.dev.yml   # Development setup
├── backend/
│   ├── simple_server.py     # Simple HTTP server
│   ├── Dockerfile          # Backend container
│   └── requirements.txt    # Python dependencies
└── frontend/               # React frontend
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

## 🔧 Available Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/` | GET | Basic status | No |
| `/health` | GET | Health check | No |
| `/api/auth/token` | POST | Get auth token | No |
| `/api/system` | GET | System stats | Yes |
| `/api/services` | GET | Services status | Yes |
| `/api/services` | POST | Control services | Yes |
| `/api/power` | POST | Power actions | Yes |

## 🐳 Docker Commands

```bash
# View running containers
docker ps

# View logs
docker logs pi-monitor-backend
docker logs pi-monitor-frontend

# Stop all
docker stop pi-monitor-backend pi-monitor-frontend

# Start all
docker start pi-monitor-backend pi-monitor-frontend

# Restart all
docker restart pi-monitor-backend pi-monitor-frontend
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
# Update backend only
./update_backend_docker.sh

# Full redeploy
./deploy.sh
```

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   sudo lsof -i:5001
   sudo fuser -k 5001/tcp
   ```

2. **Container won't start**
   ```bash
   docker logs pi-monitor-backend
   docker run --rm pi-monitor-backend
   ```

3. **Health check failing**
   ```bash
   curl -v http://localhost:5001/health
   ```

### Logs

```bash
# Follow logs in real-time
docker logs -f pi-monitor-backend

# View last 50 lines
docker logs --tail 50 pi-monitor-backend
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

### Docker Development

```bash
# Development mode
docker-compose -f docker-compose.dev.yml up -d

# Production mode
docker-compose -f docker-compose.prod.yml up -d
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
- Containerized with Docker
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
