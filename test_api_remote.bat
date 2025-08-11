@echo off
REM Pi Monitor - Remote API Test Script for Windows
REM Test the API from any Windows machine

setlocal enabledelayedexpansion

REM Colors (Windows 10+ supports ANSI colors)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "NC=[0m"

REM Configuration - Change these for your setup
set "DEFAULT_PI_IP=192.168.0.201"
set "DEFAULT_BACKEND_PORT=5001"
set "DEFAULT_FRONTEND_PORT=80"

echo %BLUE%🥧 Pi Monitor - Remote API Testing (Windows)%NC%
echo ================================================
echo.

echo %YELLOW%Enter your Pi's IP address (or press Enter for default):%NC%
set /p "PI_IP=Pi IP [%DEFAULT_PI_IP%]: "
if "!PI_IP!"=="" set "PI_IP=%DEFAULT_PI_IP%"

echo %YELLOW%Enter backend port (or press Enter for default):%NC%
set /p "BACKEND_PORT=Backend Port [%DEFAULT_BACKEND_PORT%]: "
if "!BACKEND_PORT!"=="" set "BACKEND_PORT=%DEFAULT_BACKEND_PORT%"

echo %YELLOW%Enter frontend port (or press Enter for default):%NC%
set /p "FRONTEND_PORT=Frontend Port [%DEFAULT_FRONTEND_PORT%]: "
if "!FRONTEND_PORT!"=="" set "FRONTEND_PORT=%DEFAULT_FRONTEND_PORT%"

REM Set URLs
set "BACKEND_URL=http://!PI_IP!:!BACKEND_PORT!"
set "FRONTEND_URL=http://!PI_IP!:!FRONTEND_PORT!"

echo.
echo %CYAN%Testing against:%NC%
echo   Pi IP: !PI_IP!
echo   Backend: !BACKEND_URL!
echo   Frontend: !FRONTEND_URL!
echo.

REM Test tracking
set "TESTS_PASSED=0"
set "TESTS_FAILED=0"

REM Check if curl is available
curl --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Error: curl is not installed%NC%
    echo Please install curl to run this test script.
    echo.
    echo Download from: https://curl.se/windows/
    echo Or install via Chocolatey: choco install curl
    pause
    exit /b 1
)

echo %BLUE%🔍 Starting API Tests...%NC%
echo.

REM Test 1: Basic connectivity to Pi
echo %BLUE%1. Testing Basic Connectivity%NC%
ping -n 1 -w 2000 "!PI_IP!" >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ Pi is not reachable%NC%
    echo   Check if:
    echo     - Pi is powered on
    echo     - Pi is connected to network
    echo     - IP address is correct
    echo     - Firewall allows ping
    echo.
    echo   You can still test the API if the Pi blocks ping but allows HTTP
) else (
    echo %GREEN%✅ Pi is reachable%NC%
)
echo.

REM Test 2: Backend health check
echo %BLUE%2. Testing Backend Health%NC%
echo %YELLOW%Testing: Health Check%NC%
echo   URL: !BACKEND_URL!/health
for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" "!BACKEND_URL!/health" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
echo   Status: !HTTP_STATUS!
if "!HTTP_STATUS!"=="200" (
    echo   %GREEN%✅ PASS%NC%
    set /a TESTS_PASSED+=1
) else (
    echo   %RED%❌ FAIL - Expected 200, got !HTTP_STATUS!%NC%
    set /a TESTS_FAILED+=1
)
echo.

REM Test 3: Backend root endpoint
echo %BLUE%3. Testing Backend Root%NC%
echo %YELLOW%Testing: Root Endpoint%NC%
echo   URL: !BACKEND_URL!/
for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" "!BACKEND_URL!/" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
echo   Status: !HTTP_STATUS!
if "!HTTP_STATUS!"=="200" (
    echo   %GREEN%✅ PASS%NC%
    set /a TESTS_PASSED+=1
) else (
    echo   %RED%❌ FAIL - Expected 200, got !HTTP_STATUS!%NC%
    set /a TESTS_FAILED+=1
)
echo.

REM Test 4: Authentication
echo %BLUE%4. Testing Authentication%NC%
echo %YELLOW%Testing: Get Auth Token%NC%
echo   URL: !BACKEND_URL!/api/auth/token
for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" -X POST "!BACKEND_URL!/api/auth/token" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
echo   Status: !HTTP_STATUS!
if "!HTTP_STATUS!"=="200" (
    echo   %GREEN%✅ PASS%NC%
    set /a TESTS_PASSED+=1
) else (
    echo   %RED%❌ FAIL - Expected 200, got !HTTP_STATUS!%NC%
    set /a TESTS_FAILED+=1
)
echo.

REM Get the token for authenticated tests
echo %YELLOW%Getting authentication token...%NC%
for /f "tokens=2 delims=:," %%i in ('curl -s -X POST "!BACKEND_URL!/api/auth/token" ^| findstr "access_token"') do set "AUTH_TOKEN=%%i"
set "AUTH_TOKEN=!AUTH_TOKEN:"=!"

if not "!AUTH_TOKEN!"=="" (
    echo %GREEN%✅ Token received: !AUTH_TOKEN:~0,30!...%NC%
    echo.
) else (
    echo %RED%❌ Failed to get token%NC%
    echo Continuing with unauthenticated tests...
    echo.
    set "AUTH_TOKEN="
)

REM Test 5: System stats (requires auth)
echo %BLUE%5. Testing System Endpoints%NC%
if not "!AUTH_TOKEN!"=="" (
    echo %YELLOW%Testing: Get System Stats%NC%
    echo   URL: !BACKEND_URL!/api/system
    for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" -H "Authorization: Bearer !AUTH_TOKEN!" "!BACKEND_URL!/api/system" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
    echo   Status: !HTTP_STATUS!
    if "!HTTP_STATUS!"=="200" (
        echo   %GREEN%✅ PASS%NC%
        set /a TESTS_PASSED+=1
    ) else (
        echo   %RED%❌ FAIL - Expected 200, got !HTTP_STATUS!%NC%
        set /a TESTS_FAILED+=1
    )
) else (
    echo %YELLOW%Testing: Get System Stats (No Auth)%NC%
    echo   URL: !BACKEND_URL!/api/system
    for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" "!BACKEND_URL!/api/system" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
    echo   Status: !HTTP_STATUS!
    if "!HTTP_STATUS!"=="401" (
        echo   %GREEN%✅ PASS%NC%
        set /a TESTS_PASSED+=1
    ) else (
        echo   %RED%❌ FAIL - Expected 401, got !HTTP_STATUS!%NC%
        set /a TESTS_FAILED+=1
    )
)
echo.

REM Test 6: Frontend accessibility
echo %BLUE%6. Testing Frontend%NC%
echo %YELLOW%Testing: Frontend Access%NC%
echo   URL: !FRONTEND_URL!
for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" "!FRONTEND_URL!" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
echo   Status: !HTTP_STATUS!
if "!HTTP_STATUS!"=="200" (
    echo   %GREEN%✅ PASS%NC%
    set /a TESTS_PASSED+=1
) else (
    echo   %RED%❌ FAIL - Expected 200, got !HTTP_STATUS!%NC%
    set /a TESTS_FAILED+=1
)
echo.

REM Test 7: Invalid endpoints
echo %BLUE%7. Testing Error Handling%NC%
echo %YELLOW%Testing: Invalid Endpoint%NC%
echo   URL: !BACKEND_URL!/invalid
for /f "tokens=2 delims= " %%i in ('curl -s -w "HTTP_STATUS:%%{http_code}" "!BACKEND_URL!/invalid" 2^>nul ^| findstr "HTTP_STATUS:"') do set "HTTP_STATUS=%%i"
echo   Status: !HTTP_STATUS!
if "!HTTP_STATUS!"=="404" (
    echo   %GREEN%✅ PASS%NC%
    set /a TESTS_PASSED+=1
) else (
    echo   %RED%❌ FAIL - Expected 404, got !HTTP_STATUS!%NC%
    set /a TESTS_FAILED+=1
)
echo.

REM Summary
echo %BLUE%📊 Test Summary%NC%
echo ================
echo %GREEN%Tests Passed: !TESTS_PASSED!%NC%
echo %RED%Tests Failed: !TESTS_FAILED!%NC%
set /a TOTAL_TESTS=!TESTS_PASSED!+!TESTS_FAILED!
echo Total Tests: !TOTAL_TESTS!

if !TESTS_FAILED!==0 (
    echo.
    echo %GREEN%🎉 All tests passed! Your Pi Monitor is working perfectly.%NC%
) else (
    echo.
    echo %YELLOW%⚠️  Some tests failed. Check the output above for details.%NC%
)

echo.
echo %BLUE%🌐 Access URLs:%NC%
echo   Backend API: !BACKEND_URL!
echo   Frontend: !FRONTEND_URL!
echo   Health Check: !BACKEND_URL!/health

echo.
echo %BLUE%💡 Manual Testing Commands:%NC%
echo   # Test health
echo   curl !BACKEND_URL!/health
echo.
echo   # Get auth token
echo   curl -X POST !BACKEND_URL!/api/auth/token
echo.
if not "!AUTH_TOKEN!"=="" (
    echo   # Test with token
    echo   curl -H "Authorization: Bearer !AUTH_TOKEN!" !BACKEND_URL!/api/system
)

echo.
echo %CYAN%🔧 Troubleshooting:%NC%
echo   - If Pi is not reachable: Check network and IP address
echo   - If backend fails: Check if Docker containers are running
echo   - If auth fails: Check backend logs
echo   - If frontend fails: Check nginx configuration

echo.
pause
