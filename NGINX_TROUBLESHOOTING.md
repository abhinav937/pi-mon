# Nginx Proxy Troubleshooting Guide

## Problem
- ✅ Port 5001 (direct backend): `http://65.36.123.68:5001/health` works
- ❌ Port 80 (nginx proxy): `http://65.36.123.68/health` doesn't work

## Quick Diagnosis Steps

### 1. Check if Nginx is Running
```bash
sudo systemctl status nginx
```

**Expected Output:**
```
● nginx.service - A high performance web server and a reverse proxy server
   Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
   Active: active (running) since [timestamp]
```

**If not running:**
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 2. Check Nginx Configuration Syntax
```bash
sudo nginx -t
```

**Expected Output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**If syntax error:**
- Check the error message
- Fix the configuration file
- Test again: `sudo nginx -t`

### 3. Check if Port 80 is Listening
```bash
sudo netstat -tlnp | grep :80
# or
sudo ss -tlnp | grep :80
```

**Expected Output:**
```
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN      [pid]/nginx
```

**If port 80 is not listening:**
- Nginx is not running or not configured to listen on port 80
- Check nginx configuration files

### 4. Check Nginx Error Logs
```bash
sudo tail -f /var/log/nginx/error.log
```

**Look for:**
- Configuration errors
- Permission denied errors
- Connection refused errors

### 5. Check Nginx Access Logs
```bash
sudo tail -f /var/log/nginx/access.log
```

**Look for:**
- Incoming requests
- Response codes
- Request patterns

## Common Issues and Solutions

### Issue 1: Nginx Not Running
**Symptoms:** Port 80 not listening, `systemctl status nginx` shows inactive
**Solution:**
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Issue 2: Configuration Syntax Error
**Symptoms:** `nginx -t` fails
**Solution:**
- Check the configuration file for syntax errors
- Common issues: missing semicolons, unmatched braces, invalid directives
- Fix and test again: `sudo nginx -t`

### Issue 3: Permission Issues
**Symptoms:** Permission denied errors in logs
**Solution:**
```bash
# Check nginx user
sudo grep user /etc/nginx/nginx.conf

# Check file permissions
sudo chown -R www-data:www-data /var/www/pi-monitor
sudo chmod -R 755 /var/www/pi-monitor
```

### Issue 4: Port Already in Use
**Symptoms:** Port 80 already in use by another service
**Solution:**
```bash
# Check what's using port 80
sudo lsof -i :80

# Stop conflicting service or change nginx port
```

### Issue 5: Firewall Blocking Port 80
**Symptoms:** Port 80 not accessible from external
**Solution:**
```bash
# Check firewall status
sudo ufw status

# Allow port 80 if needed
sudo ufw allow 80
```

## Step-by-Step Fix

### Step 1: Verify Current Status
```bash
# Check nginx status
sudo systemctl status nginx

# Check port 80
sudo netstat -tlnp | grep :80

# Test configuration
sudo nginx -t
```

### Step 2: Start/Reload Nginx
```bash
# If not running, start it
sudo systemctl start nginx

# If running, reload configuration
sudo systemctl reload nginx

# Or restart completely
sudo systemctl restart nginx
```

### Step 3: Test the Proxy
```bash
# Test health endpoint
curl -v http://65.36.123.68/health

# Test API endpoint
curl -v http://65.36.123.68/api/system/enhanced
```

### Step 4: Check Logs for Errors
```bash
# Check error logs
sudo tail -f /var/log/nginx/error.log

# Check access logs
sudo tail -f /var/log/nginx/access.log
```

## Alternative Configuration

If the current configuration doesn't work, try this simplified version:

```nginx
server {
    listen 80;
    server_name _;

    # Simple health check
    location = /health {
        proxy_pass http://127.0.0.1:5001/health;
        proxy_set_header Host $host;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:5001/api/;
        proxy_set_header Host $host;
    }

    # Fallback for other endpoints
    location / {
        proxy_pass http://127.0.0.1:5001/;
        proxy_set_header Host $host;
    }
}
```

## Verification Commands

After fixing, verify with these commands:

```bash
# 1. Check nginx status
sudo systemctl status nginx

# 2. Test configuration
sudo nginx -t

# 3. Check ports
sudo netstat -tlnp | grep nginx

# 4. Test endpoints
curl http://65.36.123.68/health
curl http://65.36.123.68/api/system/enhanced

# 5. Check logs
sudo tail -f /var/log/nginx/error.log
```

## Expected Results

After successful configuration:
- ✅ `http://65.36.123.68/health` returns health data
- ✅ `http://65.36.123.68/api/system/enhanced` returns system data
- ✅ Port 80 is listening and accessible
- ✅ Nginx logs show successful requests
- ✅ No errors in nginx error logs
