@echo off
setlocal enabledelayedexpansion

REM =============================================================================
REM Pi Monitor HTTPS Testing & Debugging Script for Windows
REM This script tests HTTPS connectivity to your Raspberry Pi from Windows
REM =============================================================================

echo.
echo Pi Monitor HTTPS Testing & Debugging Script
echo ==============================================
echo.

REM Configuration
set PI_IP=65.36.123.68
set PI_DOMAIN=pi.cabhinav.com
set HTTP_PORT=80
set HTTPS_PORT=443
set BACKEND_PORT=5001

echo Target Raspberry Pi: %PI_IP%
echo Domain: %PI_DOMAIN%
echo HTTP Port: %HTTP_PORT%
echo HTTPS Port: %HTTPS_PORT%
echo Backend Port: %BACKEND_PORT%
echo.

REM Check if curl is available
curl --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: curl is not available
    echo    Please install curl or use Windows 10/11 (which includes curl)
    echo    Download: https://curl.se/windows/
    pause
    exit /b 1
)

echo curl is available
echo.

REM =============================================================================
REM 1. BASIC CONNECTIVITY TESTS
REM =============================================================================
echo 1. BASIC CONNECTIVITY TESTS
echo ------------------------------

echo Testing basic network connectivity...
ping -n 1 %PI_IP% >nul 2>&1
if errorlevel 1 (
    echo FAILED: Cannot ping %PI_IP%
    echo    Check if Raspberry Pi is online and accessible
) else (
    echo SUCCESS: Raspberry Pi is reachable
)

echo Testing port accessibility...
netstat -an | findstr ":%PI_IP%" >nul 2>&1
if errorlevel 1 (
    echo INFO: No active connections to %PI_IP% found
) else (
    echo INFO: Active connections to %PI_IP% found
)

echo.

REM =============================================================================
REM 2. HTTP TESTS (Port 80)
REM =============================================================================
echo 2. HTTP TESTS (Port %HTTP_PORT%)
echo ---------------------------------

echo Testing HTTP frontend access...
curl -s -o nul -w "HTTP Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes\n" "http://%PI_IP%/" 2>nul
if errorlevel 1 (
    echo FAILED: HTTP frontend access failed
) else (
    echo SUCCESS: HTTP frontend accessible
)

echo Testing HTTP health endpoint...
curl -s -o nul -w "HTTP Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes\n" "http://%PI_IP%/health" 2>nul
if errorlevel 1 (
    echo FAILED: HTTP health endpoint failed
) else (
    echo SUCCESS: HTTP health endpoint accessible
)

echo Testing HTTP API endpoint...
curl -s -o nul -w "HTTP Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes\n" "http://%PI_IP%/api/system" 2>nul
if errorlevel 1 (
    echo FAILED: HTTP API endpoint failed
) else (
    echo SUCCESS: HTTP API endpoint accessible
)

echo.

REM =============================================================================
REM 3. HTTPS TESTS (Port 443)
REM =============================================================================
echo 3. HTTPS TESTS (Port %HTTPS_PORT%)
echo ------------------------------------

echo Testing HTTPS frontend access (with SSL verification disabled)...
curl -s -k -o nul -w "HTTPS Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes, SSL: %%{ssl_verify_result}\n" "https://%PI_IP%/" 2>nul
if errorlevel 1 (
    echo FAILED: HTTPS frontend access failed
) else (
    echo SUCCESS: HTTPS frontend accessible
)

echo Testing HTTPS health endpoint (with SSL verification disabled)...
curl -s -k -o nul -w "HTTPS Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes, SSL: %%{ssl_verify_result}\n" "https://%PI_IP%/health" 2>nul
if errorlevel 1 (
    echo FAILED: HTTPS health endpoint failed
) else (
    echo SUCCESS: HTTPS health endpoint accessible
)

echo Testing HTTPS API endpoint (with SSL verification disabled)...
curl -s -k -o nul -w "HTTPS Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes, SSL: %%{ssl_verify_result}\n" "https://%PI_IP%/api/system" 2>nul
if errorlevel 1 (
    echo FAILED: HTTPS API endpoint failed
) else (
    echo SUCCESS: HTTPS API endpoint accessible
)

echo.

REM =============================================================================
REM 4. BACKEND DIRECT TESTS (Port 5001)
REM =============================================================================
echo 4. BACKEND DIRECT TESTS (Port %BACKEND_PORT%)
echo ----------------------------------------------

echo Testing direct backend health endpoint...
curl -s -o nul -w "Backend Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes\n" "http://%PI_IP%:%BACKEND_PORT%/health" 2>nul
if errorlevel 1 (
    echo FAILED: Direct backend access failed
) else (
    echo SUCCESS: Direct backend accessible
)

echo Testing direct backend API endpoint...
curl -s -o nul -w "Backend Status: %%{http_code}, Response Time: %%{time_total}s, Size: %%{size_download} bytes\n" "http://%PI_IP%:%BACKEND_PORT%/api/system" 2>nul
if errorlevel 1 (
    echo FAILED: Direct backend API access failed
) else (
    echo SUCCESS: Direct backend API accessible
)

echo.

REM =============================================================================
REM 5. SSL CERTIFICATE TESTS
REM =============================================================================
echo 5. SSL CERTIFICATE TESTS
echo ---------------------------

echo Testing SSL certificate details...
curl -s -k -v "https://%PI_IP%/" 2>&1 | findstr /C:"* SSL connection" /C:"* ALPN" /C:"* TLS" /C:"* subject:" /C:"* issuer:" /C:"* expire date:" >nul 2>&1
if errorlevel 1 (
    echo FAILED: Could not retrieve SSL certificate details
) else (
    echo SUCCESS: SSL certificate details retrieved
)

echo Testing SSL handshake...
curl -s -k -w "SSL Handshake: %%{ssl_verify_result}, Protocol: %%{ssl_version}, Cipher: %%{ssl_cipher}\n" "https://%PI_IP%/" >nul 2>&1
if errorlevel 1 (
    echo FAILED: SSL handshake failed
) else (
    echo SUCCESS: SSL handshake successful
)

echo.

REM =============================================================================
REM 6. DOMAIN TESTS
REM =============================================================================
echo 6. DOMAIN TESTS
echo -----------------

echo Testing domain resolution...
nslookup %PI_DOMAIN% >nul 2>&1
if errorlevel 1 (
    echo FAILED: Domain %PI_DOMAIN% could not be resolved
) else (
    echo SUCCESS: Domain %PI_DOMAIN% resolved successfully
)

echo Testing domain HTTP access...
curl -s -o nul -w "Domain HTTP Status: %%{http_code}, Response Time: %%{time_total}s\n" "http://%PI_DOMAIN%/" 2>nul
if errorlevel 1 (
    echo FAILED: Domain HTTP access failed
) else (
    echo SUCCESS: Domain HTTP accessible
)

echo Testing domain HTTPS access...
curl -s -k -o nul -w "Domain HTTPS Status: %%{http_code}, Response Time: %%{time_total}s\n" "https://%PI_DOMAIN%/" 2>nul
if errorlevel 1 (
    echo FAILED: Domain HTTPS access failed
) else (
    echo SUCCESS: Domain HTTPS accessible
)

echo.

REM =============================================================================
REM 7. DETAILED CURL TESTS WITH VERBOSE OUTPUT
REM =============================================================================
echo 7. DETAILED CURL TESTS
echo -------------------------

echo Detailed HTTPS test with verbose output...
echo.
curl -v -k "https://%PI_IP%/health" 2>&1 | findstr /C:"*" /C:"<" /C:"{" /C:"}"
echo.

REM =============================================================================
REM 8. PERFORMANCE TESTS
REM =============================================================================
echo 8. PERFORMANCE TESTS
echo -----------------------

echo Testing response times (5 requests)...
for /l %%i in (1,1,5) do (
    curl -s -k -o nul -w "Request %%i: %%{time_total}s\n" "https://%PI_IP%/health" 2>nul
    if errorlevel 1 (
        echo Request %%i: FAILED
    )
)

echo.

REM =============================================================================
REM 9. TROUBLESHOOTING SUMMARY
REM =============================================================================
echo 9. TROUBLESHOOTING SUMMARY
echo ------------------------------

echo.
echo DIAGNOSIS RESULTS:
echo.

REM Test summary
echo HTTP Frontend (Port %HTTP_PORT%): 
curl -s -o nul -w "%%{http_code}" "http://%PI_IP%/" 2>nul
if errorlevel 1 (
    echo FAILED
) else (
    echo WORKING
)

echo HTTP Health (Port %HTTP_PORT%): 
curl -s -o nul -w "%%{http_code}" "http://%PI_IP%/health" 2>nul
if errorlevel 1 (
    echo FAILED
) else (
    echo WORKING
)

echo HTTPS Frontend (Port %HTTPS_PORT%): 
curl -s -k -o nul -w "%%{http_code}" "https://%PI_IP%/" 2>nul
if errorlevel 1 (
    echo FAILED
) else (
    echo WORKING
)

echo HTTPS Health (Port %HTTPS_PORT%): 
curl -s -k -o nul -w "%%{http_code}" "https://%PI_IP%/health" 2>nul
if errorlevel 1 (
    echo FAILED
) else (
    echo WORKING
)

echo Backend Direct (Port %BACKEND_PORT%): 
curl -s -o nul -w "%%{http_code}" "http://%PI_IP%:%BACKEND_PORT%/health" 2>nul
if errorlevel 1 (
    echo FAILED
) else (
    echo WORKING
)

echo.

REM =============================================================================
REM 10. RECOMMENDATIONS
REM =============================================================================
echo 10. RECOMMENDATIONS
echo ----------------------

echo.
echo If HTTPS is not working:
echo    1. Check if SSL certificates exist on Raspberry Pi
echo    2. Verify Nginx configuration has HTTPS server block
echo    3. Check if port 443 is open in firewall
echo    4. Ensure Nginx is running and configured correctly
echo.
echo If HTTP works but HTTPS doesn't:
echo    1. SSL certificates are missing or invalid
echo    2. Nginx HTTPS configuration is incorrect
echo    3. Port 443 is blocked by firewall
echo.
echo If backend works but frontend doesn't:
echo    1. Frontend files are not deployed to /var/www/pi-monitor
echo    2. Nginx is not serving static files correctly
echo.

REM =============================================================================
REM 11. COMMAND REFERENCE
REM =============================================================================
echo 11. COMMAND REFERENCE
echo -------------------------

echo.
echo Manual test commands you can run:
echo.
echo Test HTTP:
echo   curl -v http://%PI_IP%/
echo   curl -v http://%PI_IP%/health
echo.
echo Test HTTPS (ignore SSL errors):
echo   curl -v -k https://%PI_IP%/
echo   curl -v -k https://%PI_IP%/health
echo.
echo Test Backend directly:
echo   curl -v http://%PI_IP%:%BACKEND_PORT%/health
echo.
echo Test Domain:
echo   curl -v -k https://%PI_DOMAIN%/
echo.

echo ==============================================
echo HTTPS Testing Complete!
echo ==============================================
echo.
echo Review the results above to identify issues
echo Use the recommendations to fix problems
echo Run manual tests if needed
echo.
pause
