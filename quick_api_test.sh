#!/bin/bash

# Quick API Test - Copy-paste this on your Pi
echo "🚀 Testing Pi Monitor API Endpoints..." && echo && \
echo "1️⃣ Testing root endpoint:" && curl -s http://192.168.0.201:5001/ | jq . 2>/dev/null || curl -s http://192.168.0.201:5001/ && echo && \
echo "2️⃣ Testing health endpoint:" && curl -s http://192.168.0.201:5001/health | jq . 2>/dev/null || curl -s http://192.168.0.201:5001/health && echo && \
echo "3️⃣ Testing auth endpoint:" && curl -s -X POST http://192.168.0.201:5001/api/auth/token -H "Content-Type: application/json" -d '{"username": "abhinav", "password": "kavachi"}' | jq . 2>/dev/null || curl -s -X POST http://192.168.0.201:5001/api/auth/token -H "Content-Type: application/json" -d '{"username": "abhinav", "password": "kavachi"}' && echo && \
echo "4️⃣ Testing system endpoint (no auth - should fail):" && curl -s http://192.168.0.201:5001/api/system | jq . 2>/dev/null || curl -s http://192.168.0.201:5001/api/system && echo && \
echo "5️⃣ Testing service info endpoints:" && curl -s http://192.168.0.201:5001/api/service/restart | jq . 2>/dev/null || curl -s http://192.168.0.201:5001/api/service/restart && echo && \
echo "✅ Quick API test complete! Check responses above."
