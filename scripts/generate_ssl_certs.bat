@echo off
REM Generate SSL certificates for Pi Monitor
REM This script creates self-signed certificates for development/testing

echo 🔒 Generating SSL certificates for Pi Monitor...

REM Create certs directory
if not exist "..\backend\certs" mkdir "..\backend\certs"

REM Check if OpenSSL is available
openssl version >nul 2>&1
if errorlevel 1 (
    echo ❌ OpenSSL not found. Please install OpenSSL and add it to your PATH.
    echo    Download from: https://slproweb.com/products/Win32OpenSSL.html
    pause
    exit /b 1
)

REM Generate private key
echo 📝 Generating private key...
openssl genrsa -out "..\backend\certs\server.key" 4096

REM Generate certificate signing request
echo 📝 Generating certificate signing request...
openssl req -new -key "..\backend\certs\server.key" -out "..\backend\certs\server.csr" -subj "/C=US/ST=State/L=City/O=PiMonitor/CN=localhost"

REM Generate self-signed certificate
echo 📝 Generating self-signed certificate...
openssl x509 -req -in "..\backend\certs\server.csr" -signkey "..\backend\certs\server.key" -out "..\backend\certs\server.crt" -days 365

REM Clean up CSR file
del "..\backend\certs\server.csr"

echo ✅ SSL certificates generated successfully!
echo 📍 Certificate: ..\backend\certs\server.crt
echo 🔑 Private Key: ..\backend\certs\server.key
echo.
echo ⚠️  Note: These are self-signed certificates for development/testing only.
echo    For production, use certificates from a trusted Certificate Authority.
echo.
echo 🚀 You can now run the secure server with:
echo    cd ..\backend ^&^& python secure_server.py
echo.
pause
