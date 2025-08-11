#!/bin/bash

# Pi Monitor Domain Deployment Script
# This script sets up your pi-mon application with pi.cabhinav.com domain

set -e

echo "🚀 Starting Pi Monitor Domain Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Checking prerequisites..."

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs frontend-logs nginx-logs ssl

# Check if SSL certificates exist
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    print_warning "SSL certificates not found in ssl/ directory"
    print_status "You'll need to obtain SSL certificates for pi.cabhinav.com"
    print_status "You can use Let's Encrypt with the following command:"
    echo ""
    echo "sudo certbot certonly --standalone -d pi.cabhinav.com"
    echo ""
    print_status "After obtaining certificates, copy them to the ssl/ directory:"
    echo ""
    echo "sudo cp /etc/letsencrypt/live/pi.cabhinav.com/fullchain.pem ssl/cert.pem"
    echo "sudo cp /etc/letsencrypt/live/pi.cabhinav.com/privkey.pem ssl/key.pem"
    echo "sudo chown \$USER:\$USER ssl/*.pem"
    echo ""
    read -p "Press Enter to continue after setting up SSL certificates..."
fi

# Update Nginx configuration with correct SSL paths
if [ -f "ssl/cert.pem" ] && [ -f "ssl/key.pem" ]; then
    print_status "Updating Nginx configuration with SSL certificate paths..."
    sed -i 's|ssl_certificate /etc/letsencrypt/live/pi.cabhinav.com/fullchain.pem|ssl_certificate /etc/nginx/ssl/cert.pem|g' nginx-pi-subdomain.conf
    sed -i 's|ssl_certificate_key /etc/letsencrypt/live/pi.cabhinav.com/privkey.pem|ssl_certificate_key /etc/nginx/ssl/key.pem|g' nginx-pi-subdomain.conf
    print_success "SSL certificate paths updated in Nginx configuration"
fi

# Stop existing containers if running
print_status "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start the new domain-enabled stack
print_status "Building and starting domain-enabled stack..."
docker-compose -f docker-compose.prod-domain.yml up -d --build

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."

# Check backend
if curl -f http://localhost:5001/health > /dev/null 2>&1; then
    print_success "Backend is healthy"
else
    print_warning "Backend health check failed"
fi

# Check frontend
if curl -f http://localhost:80/ > /dev/null 2>&1; then
    print_success "Frontend is healthy"
else
    print_warning "Frontend health check failed"
fi

# Check nginx
if curl -f http://localhost:80/ > /dev/null 2>&1; then
    print_success "Nginx is healthy"
else
    print_warning "Nginx health check failed"
fi

# Display deployment information
echo ""
print_success "Pi Monitor Domain Deployment Complete!"
echo ""
echo "🌐 Your application is now accessible at:"
echo "   Frontend: https://pi.cabhinav.com"
echo "   Backend API: https://pi.cabhinav.com/api"
echo "   Health Check: https://pi.cabhinav.com/health"
echo ""
echo "📋 Next steps:"
echo "   1. Add DNS record: pi.cabhinav.com → 65.36.123.68 (your Pi's static IP)"
echo "   2. Ensure ports 80 and 443 are open on your server"
echo "   3. Test the application at https://pi.cabhinav.com"
echo ""
echo "🔧 Useful commands:"
echo "   View logs: docker-compose -f docker-compose.prod-domain.yml logs -f"
echo "   Stop services: docker-compose -f docker-compose.prod-domain.yml down"
echo "   Restart services: docker-compose -f docker-compose.prod-domain.yml restart"
echo ""

# Check if we can resolve the domain
print_status "Testing domain resolution..."
if nslookup pi.cabhinav.com > /dev/null 2>&1; then
    print_success "Domain pi.cabhinav.com resolves successfully"
else
    print_warning "Domain pi.cabhinav.com does not resolve yet"
    print_status "Make sure to add the DNS record: pi.cabhinav.com → 65.36.123.68"
fi

print_success "Deployment script completed!"
