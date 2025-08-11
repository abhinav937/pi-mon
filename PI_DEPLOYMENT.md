# Pi Monitor - Raspberry Pi Deployment Guide

This guide helps you deploy the Pi Monitor backend on your Raspberry Pi.

## Prerequisites

- Raspberry Pi (any model) running Raspberry Pi OS
- Docker installed and running
- Internet connection for initial setup

## Quick Deployment

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd pi-mon

# Make scripts executable
chmod +x deploy_pi.sh
chmod +x test_pi_backend.py
```

### 2. Deploy Backend

```bash
# Deploy the backend
./deploy_pi.sh
```

This script will:
- Build the Docker image
- Start the backend container
- Test the endpoints
- Show you the access URLs

### 3. Test the Backend

```bash
# Test locally
python3 test_pi_backend.py

# Or test manually
curl http://localhost:5001/health
curl http://localhost:5001/
```

## Manual Deployment

If you prefer manual deployment:

```bash
# Build the image
docker build -t pi-monitor-backend -f backend/Dockerfile .

# Run the container
docker run -d \
    --name pi-monitor-backend \
    --restart unless-stopped \
    -p 5001:5001 \
    --privileged \
    -v /proc:/host/proc:ro \
    -v /sys:/host/sys:ro \
    -v /var/run:/var/run:ro \
    pi-monitor-backend
```

## Configuration

### Port Configuration

Edit `config.json` to change the backend port:

```json
{
  "ports": {
    "backend": 5001
  }
}
```

### Authentication

Default credentials:
- Username: `abhinav`
- Password: `kavachi`

**⚠️ Change these in production!**

## API Endpoints

### Public Endpoints
- `GET /` - Root endpoint with server info
- `GET /health` - Health check
- `POST /api/auth/token` - Authentication

### Protected Endpoints (require Bearer token)
- `GET /api/system` - System statistics
- `GET /api/system/enhanced` - Enhanced system stats
- `GET /api/metrics` - Historical metrics
- `GET /api/services` - Service status
- `GET /api/power` - Power management
- `GET /api/status` - Quick status overview

## Testing

### Get Authentication Token

```bash
curl -X POST http://localhost:5001/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"abhinav","password":"kavachi"}'
```

### Test Protected Endpoint

```bash
# Use the token from the previous response
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:5001/api/system
```

## Troubleshooting

### Check Container Status

```bash
docker ps -f name=pi-monitor-backend
```

### View Logs

```bash
docker logs pi-monitor-backend
docker logs pi-monitor-backend --tail 50
```

### Restart Container

```bash
docker restart pi-monitor-backend
```

### Common Issues

1. **Port already in use**: Change the port in `config.json`
2. **Permission denied**: Make sure Docker is running and you have permissions
3. **Container won't start**: Check logs with `docker logs pi-monitor-backend`

## System Service (Optional)

To run as a system service:

1. Copy the service file:
```bash
sudo cp pi-monitor.service /etc/systemd/system/
```

2. Edit the service file to point to your actual path:
```bash
sudo nano /etc/systemd/system/pi-monitor.service
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pi-monitor
sudo systemctl start pi-monitor
```

## Monitoring Commands

### View Real-time Stats

```bash
# CPU, Memory, Disk usage
curl -H "Authorization: Bearer <token>" \
  http://localhost:5001/api/system/enhanced

# Quick status
curl -H "Authorization: Bearer <token>" \
  http://localhost:5001/api/status
```

### View Historical Data

```bash
# Last 60 minutes of metrics
curl -H "Authorization: Bearer <token>" \
  "http://localhost:5001/api/metrics?minutes=60"
```

## Security Notes

- The backend runs with `--privileged` to access system information
- Default credentials are hardcoded - change them for production
- Consider using HTTPS in production
- Restrict network access if needed

## Performance

- Metrics are collected every 5 seconds
- History is limited to 1000 data points
- Container uses minimal resources (~50MB RAM)
- Suitable for continuous monitoring

## Support

If you encounter issues:

1. Check the container logs
2. Verify Docker is running
3. Check port availability
4. Ensure proper permissions

The backend is designed to be lightweight and reliable for Pi deployment.
