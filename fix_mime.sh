#!/bin/bash

echo "🔧 Quick fix for MIME type issues..."

# Rebuild frontend
echo "📦 Rebuilding frontend..."
cd frontend
npm run build
cd ..

# Clear and recopy files
echo "📁 Re-copying frontend files..."
sudo rm -rf /var/www/html/*
sudo cp -r frontend/build/* /var/www/html/
sudo chown -R www-data:www-data /var/www/html/
sudo chmod -R 755 /var/www/html/

# Update Apache config
echo "⚙️  Updating Apache configuration..."
sudo cp frontend/apache.conf /etc/apache2/sites-available/000-default.conf

# Restart Apache
echo "🔄 Restarting Apache..."
sudo systemctl restart apache2

# Test static files
echo "🧪 Testing static files..."
echo "CSS file:"
curl -I http://localhost/static/css/main.cef90d54.css 2>/dev/null | head -1
echo "JS file:"
curl -I http://localhost/static/js/main.43f08c5a.js 2>/dev/null | head -1

echo "✅ Fix applied! Try accessing your frontend now."
echo "If issues persist, check Apache logs: sudo tail -f /var/log/apache2/error.log"
