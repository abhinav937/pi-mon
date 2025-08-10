# 🥧 Pi Monitor

A real-time Raspberry Pi monitoring dashboard with beautiful web interface, featuring MQTT communication, WebSocket real-time updates, and comprehensive system management.

![Pi Monitor Dashboard](https://img.shields.io/badge/Status-Production%20Ready-brightgreen) ![ARM64](https://img.shields.io/badge/ARM64-Compatible-blue) ![Docker](https://img.shields.io/badge/Docker-Supported-2496ED) ![React](https://img.shields.io/badge/React-18.2.0-61DAFB) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688)

## 🌟 Features

### Real-Time Monitoring
- **CPU Usage**: Live processor utilization tracking
- **Memory Usage**: RAM consumption monitoring
- **Disk Space**: Storage utilization alerts
- **Temperature**: CPU temperature monitoring with alerts
- **Network Activity**: Real-time network I/O statistics
- **System Uptime**: Continuous uptime tracking

### System Management
- **Power Management**: Safe shutdown and restart with delays
- **Service Control**: Start, stop, and restart system services
- **Real-time Updates**: WebSocket and MQTT-based live data
- **Historical Charts**: Resource usage over time with Chart.js

### Modern Architecture
- **Backend**: FastAPI with Python 3.11+
- **Frontend**: React 18 with Tailwind CSS
- **Communication**: MQTT + WebSocket + REST API
- **Caching**: Redis for performance
- **Deployment**: Docker + systemd service options

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React SPA     │    │   FastAPI       │    │   Pi Agent      │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (MQTT Pub)    │
│                 │    │                 │    │                 │
│ • Dashboard     │    │ • REST API      │    │ • System Stats  │
│ • Real-time UI  │    │ • WebSocket     │    │ • MQTT Client   │
│ • Charts        │    │ • MQTT Sub      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │     Redis       │              │
         └──────────────│   (Caching)     │──────────────┘
                        └─────────────────┘
                                │
                        ┌─────────────────┐
                        │   Mosquitto     │
                        │  (MQTT Broker)  │
                        └─────────────────┘
```

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Clone or download the pi-monitor project
git clone <your-repo-url> pi-monitor
cd pi-monitor

# Run the automated setup (installs Docker, MQTT, Redis, etc.)
sudo ./setup.sh

# Deploy using Docker Compose (easiest)
docker-compose up -d

# Access the dashboard
open http://localhost
```

### Option 2: Manual Deployment

```bash
# 1. Setup environment
sudo ./setup.sh

# 2. Deploy backend as systemd service
cd backend
sudo ./deploy_backend.sh

# 3. Deploy frontend in Docker
cd ../frontend
./deploy_frontend.sh

# 4. Access dashboard
open http://localhost
```

## 📁 Project Structure

```
pi-monitor/
├── backend/                    # Python FastAPI backend
│   ├── main_server.py         # Main FastAPI application
│   ├── system_monitor.py      # System metrics collection
│   ├── power_management.py    # Shutdown/restart functionality
│   ├── service_management.py  # Service control
│   ├── agent.py              # MQTT publishing agent
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Backend container
│   └── deploy_backend.sh    # Systemd deployment script
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.js           # Main React application
│   │   ├── components/      # React components
│   │   │   ├── Dashboard.js
│   │   │   ├── SystemStatus.js
│   │   │   ├── ResourceChart.js
│   │   │   ├── PowerManagement.js
│   │   │   └── ServiceManagement.js
│   │   └── services/
│   │       └── unifiedClient.js # WebSocket/REST client
│   ├── package.json         # Node dependencies
│   ├── Dockerfile          # Frontend container
│   ├── nginx.conf          # Nginx configuration
│   └── deploy_frontend.sh  # Docker deployment script
├── docker-compose.yml        # Full stack orchestration
├── .env                     # Environment configuration
├── setup.sh                # System setup script
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production-please
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=pimonitor
MQTT_PASSWORD=pimonitor123

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=pimonitor123

# Backend Configuration
BACKEND_PORT=5000

# Agent Configuration
PUBLISH_INTERVAL=5.0
DEVICE_NAME=raspberry-pi

# Frontend Configuration
REACT_APP_SERVER_URL=http://localhost:5000
```

### Customization

1. **Update credentials**: Change default passwords in `.env`
2. **Modify intervals**: Adjust `PUBLISH_INTERVAL` for data frequency
3. **Add services**: Extend `default_services` list in `service_management.py`
4. **Custom themes**: Modify Tailwind CSS classes in components

## 📊 API Endpoints

### REST API

```
GET  /health                    # Health check
POST /api/auth/token           # Authentication
GET  /api/system              # System statistics
POST /api/power               # Power management
GET  /api/services            # List services
POST /api/services            # Control services
```

### WebSocket

```
/ws/system-stats               # Real-time system updates
```

### MQTT Topics

```
/pi/cpu                        # CPU usage
/pi/memory                     # Memory usage
/pi/disk                       # Disk usage
/pi/temperature               # Temperature
/pi/network                   # Network stats
/pi/status                    # Device status
```

## 🛠️ Development

### Backend Development

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main_server:combined_app --reload --host 0.0.0.0 --port 5000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

### Testing

```bash
# Test backend health
curl http://localhost:5000/health

# Test MQTT
mosquitto_pub -h localhost -t test -m "hello world"

# Test Redis
redis-cli -a pimonitor123 ping

# Test system stats API
curl -H "Authorization: Bearer <token>" http://localhost:5000/api/system
```

## 🐳 Docker Deployment

### Full Stack with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

### Individual Services

```bash
# Backend only
docker-compose up -d backend redis mosquitto

# Frontend only
docker-compose up -d frontend

# Scale services
docker-compose up -d --scale backend=2
```

## 🔐 Security

### Production Hardening

1. **Change Default Credentials**
   ```bash
   # Generate secure JWT secret
   openssl rand -base64 32

   # Update MQTT passwords
   mosquitto_passwd -c /etc/mosquitto/passwd pimonitor
   ```

2. **Enable SSL/TLS**
   ```bash
   # Add SSL certificates to nginx.conf
   # Configure MQTT with TLS
   # Use HTTPS URLs in frontend
   ```

3. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS (if using SSL)
   sudo ufw enable
   ```

## 📱 Mobile Responsive

The dashboard is fully responsive and works great on:
- 📱 Mobile phones (iOS/Android)
- 📱 Tablets (iPad, Android tablets)
- 💻 Desktop browsers
- 🖥️ Large screens

## 🚨 Troubleshooting

### Common Issues

1. **Backend not starting**
   ```bash
   # Check logs
   journalctl -u pi-monitor -f
   
   # Verify dependencies
   systemctl status redis-server
   systemctl status mosquitto
   ```

2. **Frontend not loading**
   ```bash
   # Check Docker container
   docker logs pi-monitor-frontend
   
   # Verify backend connection
   curl http://localhost:5000/health
   ```

3. **No real-time updates**
   ```bash
   # Test MQTT broker
   mosquitto_pub -h localhost -t test -m hello
   mosquitto_sub -h localhost -t "#"
   
   # Check WebSocket connection in browser dev tools
   ```

4. **Permission issues**
   ```bash
   # Add user to docker group
   sudo usermod -aG docker $USER
   newgrp docker
   
   # Fix file permissions
   sudo chown -R $USER:$USER /opt/pi-monitor
   ```

### Performance Optimization

1. **For older Pi models**:
   - Reduce `PUBLISH_INTERVAL` to 10+ seconds
   - Limit chart data points in frontend
   - Use single Docker Compose worker

2. **For Pi 4/5**:
   - Increase workers in docker-compose
   - Enable more detailed logging
   - Add more monitoring metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - Frontend UI library
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [Chart.js](https://www.chartjs.org/) - Beautiful charts
- [Mosquitto](https://mosquitto.org/) - MQTT broker
- [Redis](https://redis.io/) - In-memory data store

## 📈 Roadmap

- [ ] Email/SMS alerts for critical thresholds
- [ ] Multi-Pi support (monitoring multiple Raspberry Pis)
- [ ] Plugin system for custom metrics
- [ ] Mobile app with push notifications
- [ ] Grafana integration
- [ ] Docker Swarm / Kubernetes support
- [ ] Historical data export (CSV/JSON)
- [ ] System backup and restore functionality

---

**Made with ❤️ for the Raspberry Pi community**

For support, please create an issue on GitHub or join our community discussions.
