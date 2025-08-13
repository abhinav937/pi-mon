# 🔒 Pi Monitor Security Implementation Guide

This guide explains how to implement HTTP security for your Pi Monitor application, including HTTPS, security headers, rate limiting, and threat detection.

## 🚀 Quick Start

### 1. Generate SSL Certificates

#### On Windows:
```bash
cd scripts
generate_ssl_certs.bat
```

#### On Linux/macOS:
```bash
cd scripts
chmod +x generate_ssl_certs.sh
./generate_ssl_certs.sh
```

### 2. Run the Secure Server
```bash
cd backend
python secure_server.py
```

## 🔐 Security Features Implemented

### 1. **HTTPS/SSL Encryption**
- **Self-signed certificates** for development/testing
- **Production-ready SSL/TLS** support
- **Automatic certificate generation** if not present
- **Secure socket wrapping** with proper SSL context

### 2. **Security Headers**
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Strict-Transport-Security` - Enforces HTTPS
- `Content-Security-Policy` - Prevents XSS and injection attacks
- `Referrer-Policy` - Controls referrer information
- `Permissions-Policy` - Restricts browser features

### 3. **Rate Limiting**
- **Configurable limits**: 100 requests per minute by default
- **IP-based tracking** with sliding window
- **Automatic blocking** of abusive IPs
- **Configurable burst limits** and time windows

### 4. **Threat Detection**
- **XSS detection** in headers and paths
- **SQL injection pattern** detection
- **Path traversal** prevention
- **Header injection** protection
- **Suspicious activity** scoring and blocking

### 5. **Input Validation**
- **Content length limits** (1MB default)
- **File type restrictions**
- **Input sanitization** for XSS prevention
- **Suspicious header** blocking

### 6. **Authentication Security**
- **Failed attempt tracking**
- **IP lockout** after multiple failures
- **Configurable lockout duration**
- **CSRF token** generation and validation

## 📁 File Structure

```
backend/
├── secure_server.py          # Main secure HTTPS server
├── security_config.py        # Security configuration management
├── security_middleware.py    # Security validation and threat detection
├── certs/                    # SSL certificates directory
│   ├── server.crt           # SSL certificate
│   └── server.key           # Private key
└── security_config.json      # User-configurable security settings

scripts/
├── generate_ssl_certs.sh     # Linux/macOS SSL generation script
└── generate_ssl_certs.bat    # Windows SSL generation script
```

## ⚙️ Configuration

### Security Configuration File (`security_config.json`)

```json
{
  "ssl": {
    "enabled": true,
    "cert_file": "certs/server.crt",
    "key_file": "certs/server.key",
    "verify_mode": "none",
    "check_hostname": false
  },
  "security_headers": {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block"
  },
  "rate_limiting": {
    "enabled": true,
    "max_requests": 100,
    "window_seconds": 60,
    "burst_limit": 20
  },
  "authentication": {
    "enabled": true,
    "session_timeout": 3600,
    "max_login_attempts": 5,
    "lockout_duration": 900
  }
}
```

## 🛡️ Security Best Practices

### 1. **Production Deployment**
- Use **Let's Encrypt** or commercial CA certificates
- Enable **HSTS** with long max-age
- Implement **proper authentication** with secure sessions
- Use **environment variables** for sensitive configuration

### 2. **Network Security**
- **Firewall rules** to restrict access
- **VPN access** for remote management
- **IP whitelisting** for admin access
- **Regular security updates**

### 3. **Monitoring and Logging**
- **Security event logging** enabled
- **Failed attempt tracking**
- **Suspicious activity alerts**
- **Regular log analysis**

## 🔧 Customization

### Adding Custom Security Rules

```python
# In security_middleware.py
def _check_custom_threats(self, request_data):
    """Add your custom threat detection logic"""
    threats = []
    
    # Example: Check for specific attack patterns
    if 'malicious_pattern' in request_data:
        threats.append("Custom threat detected")
    
    return threats
```

### Custom Security Headers

```python
# In security_config.py
"security_headers": {
    "X-Custom-Header": "Custom-Value",
    "X-Content-Type-Options": "nosniff"
}
```

## 🚨 Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   - Ensure OpenSSL is installed
   - Check certificate file permissions
   - Verify certificate paths in config

2. **Rate Limiting Too Strict**
   - Adjust `max_requests` and `window_seconds`
   - Check for legitimate high-traffic scenarios

3. **False Positive Blocking**
   - Review security patterns
   - Adjust risk scoring thresholds
   - Whitelist trusted IPs

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Security Monitoring

### Security Statistics API

```python
# Get security statistics
stats = security_middleware.get_security_stats()
print(f"Blocked IPs: {stats['blocked_ips']}")
print(f"Suspicious IPs: {stats['suspicious_ips']}")
```

### Security Event Logging

```python
# Log security events
security_middleware._log_security_event(
    client_ip="192.168.1.100",
    event_type="threat_detected",
    details={"threat": "XSS attempt"}
)
```

## 🔄 Migration from HTTP to HTTPS

### 1. **Update Frontend URLs**
```javascript
// Change from http:// to https://
const API_BASE = 'https://your-pi-ip:port';
```

### 2. **Update Configuration**
```json
{
  "ssl": {
    "enabled": true
  }
}
```

### 3. **Test Security Features**
```bash
# Test HTTPS connection
curl -k https://your-pi-ip:port/health

# Test security headers
curl -I -k https://your-pi-ip:port/
```

## 📚 Additional Resources

- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [SSL/TLS Best Practices](https://ssl-config.mozilla.org/)

## 🆘 Support

For security-related issues:
1. Check the logs for detailed error messages
2. Verify configuration file syntax
3. Test with minimal configuration
4. Review security middleware logs

---

**⚠️ Important**: This implementation provides strong security for development and testing. For production use, ensure you:
- Use proper CA-signed certificates
- Implement strong authentication
- Regularly update security dependencies
- Monitor and audit security events
- Follow security best practices for your deployment environment
