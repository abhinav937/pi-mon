# Pi Monitor

Simple Raspberry Pi monitoring with a lightweight Python HTTP server, systemd, and nginx. No heavy frameworks or Docker required

## Overview

- **Backend**: Python HTTP server (modularized under `backend/`)
- **Frontend**: React single-page app (served by nginx in production)
- **Config**: Central `config.json` for ports and service names
- **Deploy**: One command via `./deploy.sh`
- **Monitoring**: 24-hour historical data with smart time range options

## Quick start

### 1) Configure

```bash
python config.py     # print current configuration summary
nano config.json     # edit as needed
```

### 2) Deploy (backend + frontend + nginx + systemd)

```bash
./deploy.sh
```

After deployment:

- Frontend: `http://localhost:3000/`
- Backend API: `http://localhost:80`
- Health: `http://localhost:80/health`

On a Raspberry Pi you can also use the helper script to set up a virtualenv, nginx, and the systemd service in one shot:

```bash
sudo bash scripts/setup_venv_systemd.sh
```

## Configuration

Core settings live in `config.json`.

```json
{
  "ports": {
             "backend": 80,
    "frontend": 3000,
    "frontend_dev": 3000
  },
  "services": {
    "backend": { "name": "pi-monitor-backend" },
    "frontend": { "name": "pi-monitor-frontend" }
  },
  "monitoring": {
    "update_interval": "5.0",
    "data_retention_days": 7,
    "max_history_points": 20000,
    "time_ranges": [
      "1 hour (30-min intervals)",
      "6 hours (3-hour intervals)", 
      "12 hours (3-hour intervals)",
      "24 hours (6-hour intervals)"
    ]
  }
}
```

## Resource Charts & Time Ranges

The system now supports enhanced time range monitoring with proper x-axis formatting:

### Time Range Options
- **1 Hour**: Shows last hour with 30-minute intervals
- **6 Hours**: Shows last 6 hours with 3-hour intervals  
- **12 Hours**: Shows last 12 hours with 3-hour intervals
- **24 Hours**: Shows last 24 hours with 6-hour intervals

### X-Axis Formatting
- **24-hour view**: Date + Time (e.g., "12/25/2024 14:30")
- **12-hour view**: Time only (e.g., "14:30")
- **1-hour view**: Time with seconds (e.g., "14:30:45")

### Data Retention
- **Memory cache**: 20,000 data points (24+ hours at 5-second intervals)
- **Database**: 7 days of historical data
- **Real-time updates**: Every 5 seconds (configurable via Settings)

### Configurable Refresh Intervals
The system now supports dynamic refresh interval configuration:
- **2 seconds**: High-frequency monitoring for critical systems
- **5 seconds**: Default interval for balanced performance
- **10 seconds**: Moderate monitoring for stable systems  
- **30 seconds**: Low-frequency monitoring for long-term trends
- **1 minute**: Minimal monitoring for background systems

**Settings Integration**: Refresh intervals can be changed in real-time through the Settings panel and are immediately applied to both frontend and backend systems.

## Checksum Generation

The deployment system uses a unified approach to generate checksums for all components, determining when redeployment is needed:

### Frontend Checksum
- **Files**: JavaScript, TypeScript, CSS, JSON, HTML, and configuration files
- **Excludes**: `node_modules/` and `build/` directories
- **Method**: SHA256 hash of all source files, sorted alphabetically

### Backend Checksum  
- **Files**: Python files (`.py`), `requirements.txt`, and shell scripts (`.sh`)
- **Method**: SHA256 hash of all relevant files, sorted alphabetically

### Nginx Checksum
- **Files**: Generated configuration files
- **Method**: SHA256 hash of the final nginx config

### Benefits
- **Efficient**: Only rebuilds/restarts when source files actually change
- **Consistent**: Same hashing algorithm (SHA256) for all components
- **Testable**: Use `--test-checksums` flag to verify checksum generation
- **Stored**: Checksums saved in `$STATE_DIR/` for comparison across deployments

### Testing Checksums
```bash
./deploy.sh --test-checksums
```

Authentication uses an API key. For development a default key is used. For production set a secure key via environment or `.env` in `backend/`:

```bash
# option 1: environment variable
export PI_MONITOR_API_KEY="your-secure-key"

# option 2: .env file in backend/
cd backend && cp env.example .env && edit .env
```

## Development

### Backend

```bash
cd backend
pip install -r requirements.txt
python simple_server.py    # or: python main.py
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## API endpoints (short list)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/` | GET | Basic status |
| `/health` | GET | Health check |
| `/api/auth/token` | POST | Validate API key |
| `/api/system` | GET | System stats (may include history) |
| `/api/services` | GET/POST | List and control system services |
| `/api/power` | GET/POST | Power status and actions |

## Common operations

```bash
# backend service
sudo systemctl status pi-monitor-backend
sudo systemctl restart pi-monitor-backend
sudo journalctl -u pi-monitor-backend -n 100 -f

# nginx
sudo systemctl status nginx
sudo systemctl restart nginx
```

## Troubleshooting

- Port in use:
  ```bash
  sudo lsof -i:80 || sudo fuser -k 80/tcp
  ```
- Service not starting:
  ```bash
  sudo systemctl status pi-monitor-backend
  sudo journalctl -u pi-monitor-backend -n 200 -f
  ```
- Health check:
  ```bash
  curl -v http://localhost/health
  ```

## Project structure (brief)

```
pi-mon/
├─ config.json
├─ config.py
├─ deploy.sh
├─ scripts/
│  └─ setup_venv_systemd.sh
├─ nginx/
├─ backend/
└─ frontend/
```

## License

MIT


