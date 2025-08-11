#!/bin/bash

# Domain Test Script for pi.cabhinav.com
# This script tests your domain setup and provides diagnostics

set -e

echo "🔍 Testing Pi Monitor Domain Setup..."

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

# Test DNS resolution
print_status "Testing DNS resolution for pi.cabhinav.com..."
if nslookup pi.cabhinav.com > /dev/null 2>&1; then
    print_success "DNS resolution successful"
    
    # Get the resolved IP
    RESOLVED_IP=$(nslookup pi.cabhinav.com | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
    if [ "$RESOLVED_IP" = "65.36.123.68" ]; then
        print_success "Domain resolves to correct IP: $RESOLVED_IP"
    else
        print_warning "Domain resolves to: $RESOLVED_IP (expected: 65.36.123.68)"
    fi
else
    print_error "DNS resolution failed"
    echo "Make sure you've added the A record: pi → 65.36.123.68"
fi

echo ""

# Test HTTP connectivity
print_status "Testing HTTP connectivity..."
if curl -s -I http://65.36.123.68 > /dev/null 2>&1; then
    print_success "HTTP connection to IP successful"
else
    print_error "HTTP connection to IP failed"
    echo "Check if your Pi is running and accessible"
fi

echo ""

# Test domain HTTP (should redirect to HTTPS)
print_status "Testing domain HTTP (should redirect to HTTPS)..."
HTTP_RESPONSE=$(curl -s -I http://pi.cabhinav.com 2>/dev/null | head -1 || echo "Failed")
if echo "$HTTP_RESPONSE" | grep -q "301\|302"; then
    print_success "HTTP redirect working correctly"
elif echo "$HTTP_RESPONSE" | grep -q "200"; then
    print_warning "HTTP returning 200 (no redirect)"
else
    print_error "HTTP test failed: $HTTP_RESPONSE"
fi

echo ""

# Test domain HTTPS
print_status "Testing domain HTTPS..."
if curl -s -I https://pi.cabhinav.com > /dev/null 2>&1; then
    print_success "HTTPS connection successful"
else
    print_warning "HTTPS connection failed"
    echo "This is normal if SSL certificates aren't set up yet"
fi

echo ""

# Test API endpoints
print_status "Testing API endpoints..."

# Test health endpoint via IP
if curl -s http://65.36.123.68:5001/health > /dev/null 2>&1; then
    print_success "Backend health check via IP successful"
else
    print_warning "Backend health check via IP failed"
fi

# Test health endpoint via domain
if curl -s https://pi.cabhinav.com/health > /dev/null 2>&1; then
    print_success "Backend health check via domain successful"
else
    print_warning "Backend health check via domain failed"
fi

echo ""

# Test Docker containers
print_status "Checking Docker containers..."
if command -v docker &> /dev/null; then
    if docker ps | grep -q "pi-monitor"; then
        print_success "Pi Monitor containers are running"
        
        # Show container status
        echo "Container Status:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "pi-monitor"
    else
        print_warning "Pi Monitor containers not found"
        echo "Run: docker-compose -f docker-compose.prod-domain.yml up -d"
    fi
else
    print_warning "Docker not available"
fi

echo ""

# Test port availability
print_status "Checking port availability..."
if netstat -tuln 2>/dev/null | grep -q ":80 "; then
    print_success "Port 80 is listening"
else
    print_warning "Port 80 is not listening"
fi

if netstat -tuln 2>/dev/null | grep -q ":443 "; then
    print_success "Port 443 is listening"
else
    print_warning "Port 443 is not listening"
fi

echo ""

# Summary
echo "📋 Test Summary:"
echo "=================="

if nslookup pi.cabhinav.com > /dev/null 2>&1; then
    echo "✅ DNS: pi.cabhinav.com resolves"
else
    echo "❌ DNS: pi.cabhinav.com does not resolve"
fi

if curl -s -I http://65.36.123.68 > /dev/null 2>&1; then
    echo "✅ IP: http://65.36.123.68 accessible"
else
    echo "❌ IP: http://65.36.123.68 not accessible"
fi

if curl -s -I https://pi.cabhinav.com > /dev/null 2>&1; then
    echo "✅ Domain: https://pi.cabhinav.com accessible"
else
    echo "❌ Domain: https://pi.cabhinav.com not accessible"
fi

echo ""
echo "🌐 Your Pi Monitor should be accessible at:"
echo "   - IP: http://65.36.123.68"
echo "   - Domain: https://pi.cabhinav.com"
echo ""
echo "🔧 If tests fail, check:"
echo "   1. DNS records are set correctly"
echo "   2. Docker containers are running"
echo "   3. Ports 80 and 443 are open"
echo "   4. SSL certificates are configured (for HTTPS)"
