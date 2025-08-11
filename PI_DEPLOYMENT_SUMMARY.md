# Pi Monitor Deployment Summary for pi.cabhinav.com

## Your Configuration
- **Domain:** `pi.cabhinav.com`
- **Static IP:** `65.36.123.68`
- **Server:** Raspberry Pi (Linux)

## Quick Setup Steps

### 1. DNS Configuration
Add this A record to your domain registrar (cabhinav.com):

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | pi | 65.36.123.68 | 300 |

**Where to add this:**
- Go to your domain registrar's DNS management panel
- Add a new A record
- Name: `pi` (this creates pi.cabhinav.com)
- Value: `65.36.123.68`
- TTL: `300` seconds (5 minutes)

### 2. Deploy on Your Pi

SSH into your Pi and run these commands:

```bash
# Navigate to your project directory
cd /path/to/pi-mon

# Make scripts executable
chmod +x deploy_domain.sh setup_ssl.sh

# Set up SSL certificates (optional but recommended)
./setup_ssl.sh

# Deploy the application
./deploy_domain.sh
```

### 3. Verify Deployment

After deployment, test these URLs:

- **Frontend:** https://pi.cabhinav.com
- **Backend API:** https://pi.cabhinav.com/api
- **Health Check:** https://pi.cabhinav.com/health
- **Direct IP (for testing):** http://65.36.123.68

## File Structure Created

```
pi-mon/
├── nginx-pi-subdomain.conf          # Nginx configuration
├── docker-compose.prod-domain.yml   # Production Docker setup
├── deploy_domain.sh                 # Deployment script
├── setup_ssl.sh                     # SSL setup script
├── ssl/                             # SSL certificates directory
├── logs/                            # Application logs
├── frontend-logs/                   # Frontend logs
└── nginx-logs/                      # Nginx logs
```

## Ports Used

- **Port 80:** HTTP (redirects to HTTPS)
- **Port 443:** HTTPS (main application)
- **Port 5001:** Backend API (internal only)

## Services Running

1. **Backend:** Python HTTP server (port 5001 internal)
2. **Frontend:** React app with Apache (port 80 internal)
3. **Nginx:** Reverse proxy (ports 80 & 443 external)

## Troubleshooting

### If the domain doesn't work:
1. Check DNS propagation: `nslookup pi.cabhinav.com`
2. Verify DNS record is correct
3. Wait up to 48 hours for global propagation

### If the IP works but domain doesn't:
1. DNS is not set up correctly
2. DNS hasn't propagated yet
3. Check your domain registrar's DNS settings

### If nothing works:
1. Check if Docker containers are running: `docker ps`
2. Check container logs: `docker-compose -f docker-compose.prod-domain.yml logs`
3. Verify ports are open: `netstat -tuln | grep :80`

## Maintenance

### View logs:
```bash
docker-compose -f docker-compose.prod-domain.yml logs -f
```

### Restart services:
```bash
docker-compose -f docker-compose.prod-domain.yml restart
```

### Update application:
```bash
git pull
docker-compose -f docker-compose.prod-domain.yml up -d --build
```

### SSL renewal:
```bash
./renew_ssl.sh
```

## Security Notes

- Only ports 80 and 443 are exposed externally
- Backend and frontend are only accessible through Nginx
- SSL certificates auto-renew every 90 days
- All internal communication uses Docker networking

## Support

If you encounter issues:
1. Check the logs first
2. Verify DNS resolution
3. Ensure ports are accessible
4. Check Docker container status

---

**Your Pi Monitor will be accessible at: https://pi.cabhinav.com**
