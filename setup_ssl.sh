#!/bin/bash

# SSL Certificate Setup Script for pi.cabhinav.com
# This script helps you obtain SSL certificates using Let's Encrypt

set -e

echo "🔒 Setting up SSL certificates for pi.cabhinav.com..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    print_warning "Certbot is not installed. Installing now..."
    
    # Detect OS and install certbot
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        print_status "Installing certbot on Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y certbot
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        print_status "Installing certbot on CentOS/RHEL..."
        sudo yum install -y epel-release
        sudo yum install -y certbot
    elif command -v dnf &> /dev/null; then
        # Fedora
        print_status "Installing certbot on Fedora..."
        sudo dnf install -y certbot
    else
        print_error "Could not detect package manager. Please install certbot manually:"
        echo "Visit: https://certbot.eff.org/instructions"
        exit 1
    fi
fi

print_success "Certbot is available"

# Check if domain resolves
print_status "Checking if pi.cabhinav.com resolves..."
if nslookup pi.cabhinav.com > /dev/null 2>&1; then
    print_success "Domain pi.cabhinav.com resolves successfully"
else
    print_error "Domain pi.cabhinav.com does not resolve"
    print_status "Please set up DNS records first (see DNS_SETUP_GUIDE.md)"
    exit 1
fi

# Check if ports 80 and 443 are available
print_status "Checking if ports 80 and 443 are available..."

# Check port 80
if netstat -tuln 2>/dev/null | grep ":80 " > /dev/null; then
    print_warning "Port 80 is already in use. Stopping existing services..."
    # Try to stop common web servers
    sudo systemctl stop nginx 2>/dev/null || true
    sudo systemctl stop apache2 2>/dev/null || true
    sudo systemctl stop httpd 2>/dev/null || true
fi

# Check port 443
if netstat -tuln 2>/dev/null | grep ":443 " > /dev/null; then
    print_warning "Port 443 is already in use. Stopping existing services..."
    sudo systemctl stop nginx 2>/dev/null || true
    sudo systemctl stop apache2 2>/dev/null || true
    sudo systemctl stop httpd 2>/dev/null || true
fi

# Create ssl directory
mkdir -p ssl

print_status "Obtaining SSL certificate using Let's Encrypt..."

# Stop any running containers that might use ports 80/443
print_status "Stopping Docker containers that might use ports 80/443..."
docker-compose down 2>/dev/null || true

# Obtain certificate
print_status "Running certbot to obtain certificate..."
sudo certbot certonly --standalone \
    --pre-hook "echo 'Stopping services on ports 80 and 443...'" \
    --post-hook "echo 'Certificate obtained successfully!'" \
    -d pi.cabhinav.com \
    --email admin@cabhinav.com \
    --agree-tos \
    --non-interactive

if [ $? -eq 0 ]; then
    print_success "SSL certificate obtained successfully!"
    
    # Copy certificates to ssl directory
    print_status "Copying certificates to ssl/ directory..."
    sudo cp /etc/letsencrypt/live/pi.cabhinav.com/fullchain.pem ssl/cert.pem
    sudo cp /etc/letsencrypt/live/pi.cabhinav.com/privkey.pem ssl/key.pem
    
    # Set proper permissions
    sudo chown $USER:$USER ssl/*.pem
    chmod 600 ssl/*.pem
    
    print_success "Certificates copied to ssl/ directory"
    
    # Update Nginx configuration
    print_status "Updating Nginx configuration with SSL certificate paths..."
    if [ -f "nginx-pi-subdomain.conf" ]; then
        sed -i 's|ssl_certificate /etc/letsencrypt/live/pi.cabhinav.com/fullchain.pem|ssl_certificate /etc/nginx/ssl/cert.pem|g' nginx-pi-subdomain.conf
        sed -i 's|ssl_certificate_key /etc/letsencrypt/live/pi.cabhinav.com/privkey.pem|ssl_certificate_key /etc/nginx/ssl/key.pem|g' nginx-pi-subdomain.conf
        print_success "Nginx configuration updated"
    fi
    
    # Create renewal script
    print_status "Creating SSL renewal script..."
    cat > renew_ssl.sh << 'EOF'
#!/bin/bash
# SSL Certificate Renewal Script

echo "🔄 Renewing SSL certificates..."

# Stop containers
docker-compose -f docker-compose.prod-domain.yml down

# Renew certificates
sudo certbot renew --quiet

# Copy renewed certificates
sudo cp /etc/letsencrypt/live/pi.cabhinav.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/pi.cabhinav.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem
chmod 600 ssl/*.pem

# Restart containers
docker-compose -f docker-compose.prod-domain.yml up -d

echo "✅ SSL certificates renewed and services restarted"
EOF

    chmod +x renew_ssl.sh
    print_success "SSL renewal script created: renew_ssl.sh"
    
    # Set up automatic renewal
    print_status "Setting up automatic SSL renewal..."
    if ! crontab -l 2>/dev/null | grep -q "renew_ssl.sh"; then
        (crontab -l 2>/dev/null; echo "0 12 * * * cd $(pwd) && ./renew_ssl.sh") | crontab -
        print_success "Automatic renewal scheduled for daily at 12:00 PM"
    else
        print_warning "Automatic renewal already scheduled"
    fi
    
    echo ""
    print_success "SSL setup completed successfully!"
    echo ""
    echo "🔐 Your SSL certificates are now ready"
    echo "📁 Certificates are stored in: ssl/"
    echo "🔄 Automatic renewal is scheduled daily at 12:00 PM"
    echo "📋 Next step: Run ./deploy_domain.sh to deploy your application"
    echo ""
    
else
    print_error "Failed to obtain SSL certificate"
    echo ""
    echo "Common issues and solutions:"
    echo "1. Make sure pi.cabhinav.com resolves to this server"
    echo "2. Ensure ports 80 and 443 are not blocked by firewall"
    echo "3. Check that your domain registrar allows external DNS management"
    echo ""
    echo "You can also try running certbot manually:"
    echo "sudo certbot certonly --standalone -d pi.cabhinav.com"
    exit 1
fi
