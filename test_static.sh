#!/bin/bash

echo "🧪 Testing static file serving..."

# Check if files exist
echo "📁 Checking if static files exist:"
if [ -f "/var/www/html/static/css/main.cef90d54.css" ]; then
    echo "✅ CSS file exists"
    ls -la /var/www/html/static/css/main.cef90d54.css
else
    echo "❌ CSS file missing"
    echo "Available CSS files:"
    ls -la /var/www/html/static/css/ 2>/dev/null || echo "No CSS directory found"
fi

if [ -f "/var/www/html/static/js/main.a36bbbf5.js" ]; then
    echo "✅ JS file exists"
    ls -la /var/www/html/static/js/main.a36bbbf5.js
else
    echo "❌ JS file missing"
    echo "Available JS files:"
    ls -la /var/www/html/static/js/ 2>/dev/null || echo "No JS directory found"
fi

echo ""
echo "🌐 Testing HTTP responses:"

# Test CSS file
echo "CSS file response:"
curl -I http://localhost/static/css/main.cef90d54.css 2>/dev/null | grep -E "(HTTP|Content-Type|Content-Length)"

# Test JS file  
echo "JS file response:"
curl -I http://localhost/static/js/main.a36bbbf5.js 2>/dev/null | grep -E "(HTTP|Content-Type|Content-Length)"

# Test actual content
echo ""
echo "📄 Testing file content (first 100 chars):"
echo "CSS content:"
curl -s http://localhost/static/css/main.cef90d54.css 2>/dev/null | head -c 100
echo ""

echo "JS content:"
curl -s http://localhost/static/js/main.a36bbbf5.js 2>/dev/null | head -c 100
echo ""

echo ""
echo "📋 Apache configuration check:"
echo "Current site config:"
sudo apache2ctl -S 2>/dev/null | grep "localhost"

echo ""
echo "🔍 Apache modules loaded:"
sudo apache2ctl -M 2>/dev/null | grep -E "(rewrite|headers|deflate|proxy)"
