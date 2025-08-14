# Pi Monitor

Simple Raspberry Pi monitoring with a lightweight Python HTTP server, systemd, and nginx. No heavy frameworks or Docker required.

## Overview

- **Backend**: Python HTTP server (modularized under `backend/`)
- **Frontend**: React single-page app (served by nginx in production)
- **Config**: Central `config.json` for ports and service names
- **Deploy**: One command via `./deploy.sh`

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

- Frontend: `http://localhost/`
- Backend API: `http://localhost:5001`
- Health: `http://localhost:5001/health`

On a Raspberry Pi you can also use the helper script to set up a virtualenv, nginx, and the systemd service in one shot:

```bash
sudo bash scripts/setup_venv_systemd.sh
```

## Configuration

Core settings live in `config.json`.

```json
{
  "ports": {
    "backend": 5001,
    "frontend": 80,
    "frontend_dev": 3000
  },
  "services": {
    "backend": { "name": "pi-monitor-backend" },
    "frontend": { "name": "pi-monitor-frontend" }
  }
}
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
  sudo lsof -i:5001 || sudo fuser -k 5001/tcp
  ```
- Service not starting:
  ```bash
  sudo systemctl status pi-monitor-backend
  sudo journalctl -u pi-monitor-backend -n 200 -f
  ```
- Health check:
  ```bash
  curl -v http://localhost:5001/health
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


