@echo off
REM Deploy Secure Pi Monitor with SSL
REM This script sets up the secure HTTPS server with SSL certificates

echo 🔒 Deploying Secure Pi Monitor...

REM Configuration
set PI_MON_DIR=%~dp0..
set BACKEND_DIR=%PI_MON_DIR%\backend
set CERTS_DIR=%BACKEND_DIR%\certs

REM Check if pi-mon directory exists
if not exist "%PI_MON_DIR%" (
    echo ❌ Pi-mon directory not found: %PI_MON_DIR%
    pause
    exit /b 1
)

REM Check if backend directory exists
if not exist "%BACKEND_DIR%" (
    echo ❌ Backend directory not found: %BACKEND_DIR%
    pause
    exit /b 1
)

echo 📍 Pi-mon directory: %PI_MON_DIR%
echo 📍 Backend directory: %BACKEND_DIR%

REM 1. Generate SSL certificates if they don't exist
echo 🔒 Setting up SSL certificates...
if not exist "%CERTS_DIR%\server.crt" (
    echo 📝 Generating SSL certificates...
    
    REM Check if OpenSSL is available
    openssl version >nul 2>&1
    if errorlevel 1 (
        echo ❌ OpenSSL not found. Please install OpenSSL and add it to your PATH.
        echo    Download from: https://slproweb.com/products/Win32OpenSSL.html
        pause
        exit /b 1
    )
    
    REM Create certs directory
    if not exist "%CERTS_DIR%" mkdir "%CERTS_DIR%"
    
    REM Generate self-signed certificate
    cd /d "%CERTS_DIR%"
    
    echo 🔑 Generating private key...
    openssl genrsa -out server.key 4096
    
    echo 📄 Generating certificate signing request...
    openssl req -new -key server.key -out server.csr -subj "/C=US/ST=State/L=City/O=PiMonitor/CN=localhost"
    
    echo 📜 Generating self-signed certificate...
    openssl x509 -req -in server.csr -signkey server.key -out server.crt -days 365
    
    REM Clean up CSR file
    del server.csr
    
    echo ✅ SSL certificates generated successfully
) else (
    echo ✅ SSL certificates already exist
)

REM 2. Install Python dependencies
echo 🐍 Installing Python dependencies...
if exist "%BACKEND_DIR%\requirements.txt" (
    cd /d "%BACKEND_DIR%"
    
    REM Check if virtual environment exists
    if exist ".venv" (
        echo 🔄 Using existing virtual environment
        call .venv\Scripts\activate.bat
    ) else (
        echo 📦 Creating virtual environment...
        python -m venv .venv
        call .venv\Scripts\activate.bat
    )
    
    echo 📦 Installing requirements...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    
    echo ✅ Dependencies installed
) else (
    echo ❌ requirements.txt not found
    pause
    exit /b 1
)

REM 3. Create security configuration
echo ⚙️ Setting up security configuration...
set SECURITY_CONFIG=%BACKEND_DIR%\security_config.json

if not exist "%SECURITY_CONFIG%" (
    echo 📝 Creating security configuration...
    (
        echo {
        echo   "ssl": {
        echo     "enabled": true,
        echo     "cert_file": "certs/server.crt",
        echo     "key_file": "certs/server.key",
        echo     "verify_mode": "none",
        echo     "check_hostname": false
        echo   },
        echo   "security_headers": {
        echo     "X-Content-Type-Options": "nosniff",
        echo     "X-Frame-Options": "DENY",
        echo     "X-XSS-Protection": "1; mode=block",
        echo     "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        echo     "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        echo     "Referrer-Policy": "strict-origin-when-cross-origin",
        echo     "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        echo   },
        echo   "rate_limiting": {
        echo     "enabled": true,
        echo     "max_requests": 100,
        echo     "window_seconds": 60,
        echo     "burst_limit": 20
        echo   },
        echo   "authentication": {
        echo     "enabled": true,
        echo     "session_timeout": 3600,
        echo     "max_login_attempts": 5,
        echo     "lockout_duration": 900,
        echo     "require_https": true
        echo   }
        echo }
    ) > "%SECURITY_CONFIG%"
    echo ✅ Security configuration created
) else (
    echo ✅ Security configuration already exists
)

REM 4. Test the secure server
echo 🧪 Testing secure server...
cd /d "%BACKEND_DIR%"

REM Check if secure_server.py exists
if not exist "secure_server.py" (
    echo ❌ secure_server.py not found
    pause
    exit /b 1
)

REM Test Python imports
echo 🔍 Testing Python imports...
python -c "import ssl; import security_config; import security_middleware; print('✅ All security modules imported successfully')"
if errorlevel 1 (
    echo ❌ Import test failed
    pause
    exit /b 1
)

REM 5. Show deployment summary
echo.
echo 🎉 Secure Pi Monitor deployment complete!
echo.
echo 📁 Files created/updated:
echo   📄 SSL Certificate: %CERTS_DIR%\server.crt
echo   🔑 Private Key: %CERTS_DIR%\server.key
echo   ⚙️  Security Config: %SECURITY_CONFIG%
echo.
echo 🚀 To run the secure server:
echo   cd %BACKEND_DIR%
echo   python secure_server.py
echo.
echo 🔒 Security features enabled:
echo   ✅ HTTPS/SSL encryption
echo   ✅ Security headers
echo   ✅ Rate limiting
echo   ✅ Threat detection
echo   ✅ Input validation
echo.
echo ⚠️  Note: This uses self-signed certificates for development/testing.
echo    For production, use certificates from a trusted Certificate Authority.
echo.
echo 🌐 The server will be accessible at:
echo   https://localhost:5001 (or your configured port)
echo.
echo 📚 For more information, see: SECURITY_README.md
echo.
pause
