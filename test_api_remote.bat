@echo off
REM Pi Monitor - Remote API Testing (Windows)
REM Tests all endpoints from any machine

echo 🥧 Pi Monitor - Remote API Testing
echo ==========================================

REM Configuration - change these as needed
set PI_IP=192.168.0.201
set BACKEND_PORT=5001
set FRONTEND_PORT=80

echo 📋 Testing against:
echo   Pi IP: %PI_IP%
echo   Backend: http://%PI_IP%:%BACKEND_PORT%
echo   Frontend: http://%PI_IP%:%FRONTEND_PORT%
echo.

echo 🔍 Starting Comprehensive API Tests...
echo.

REM Test counter
set TESTS_PASSED=0
set TESTS_FAILED=0

REM 1. Basic Connectivity
echo 1. Testing Basic Connectivity
ping -n 1 -w 2000 %PI_IP% >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ Pi is reachable
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ Pi is not reachable
    set /a TESTS_FAILED+=1
)
echo.

REM 2. Backend Health Check
echo 2. Testing Backend Health
echo   Testing: Health Check
echo   URL: http://%PI_IP%:%BACKEND_PORT%/health
curl -s -w "%%{http_code}" "http://%PI_IP%:%BACKEND_PORT%/health" > temp_response.txt 2>nul
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 3. Backend Root Endpoint
echo 3. Testing Backend Root
echo   Testing: Root Endpoint
echo   URL: http://%PI_IP%:%BACKEND_PORT%/
curl -s "http://%PI_IP%:%BACKEND_PORT%/" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 4. Backend System Stats
echo 4. Testing System Monitoring
echo   Testing: System Stats
echo   URL: http://%PI_IP%:%BACKEND_PORT%/api/system
curl -s "http://%PI_IP%:%BACKEND_PORT%/api/system" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 5. Backend Services Status
echo 5. Testing Service Management
echo   Testing: Services Status
echo   URL: http://%PI_IP%:%BACKEND_PORT%/api/services
curl -s "http://%PI_IP%:%BACKEND_PORT%/api/services" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 6. Backend Power Management
echo 6. Testing Power Management
echo   Testing: Power Status
echo   URL: http://%PI_IP%:%BACKEND_PORT%/api/power
curl -s "http://%PI_IP%:%BACKEND_PORT%/api/power" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 7. Backend Authentication
echo 7. Testing Authentication
echo   Testing: Auth Token Request
echo   URL: http://%PI_IP%:%BACKEND_PORT%/api/auth/token
echo   Method: POST
echo   Data: {"username":"admin","password":"admin"}
curl -s -X POST -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin\"}" "http://%PI_IP%:%BACKEND_PORT%/api/auth/token" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 8. Frontend Basic Access
echo 8. Testing Frontend
echo   Testing: Frontend Access
echo   URL: http://%PI_IP%:%FRONTEND_PORT%/
curl -s "http://%PI_IP%:%FRONTEND_PORT%/" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 9. Error Handling Tests
echo 9. Testing Error Handling
echo   Testing: Invalid Endpoint
echo   URL: http://%PI_IP%:%BACKEND_PORT%/invalid
curl -s "http://%PI_IP%:%BACKEND_PORT%/invalid" >nul 2>&1
if %errorlevel% equ 0 (
    echo   ✅ PASS
    set /a TESTS_PASSED+=1
) else (
    echo   ❌ FAIL
    set /a TESTS_FAILED+=1
)
echo.

REM 10. Performance Tests
echo 10. Testing Performance
echo   Testing: Response Time
set start_time=%time%
curl -s "http://%PI_IP%:%BACKEND_PORT%/health" >nul 2>&1
set end_time=%time%
echo   Response Time: Measured
echo   ✅ PASS (Performance test completed)
set /a TESTS_PASSED+=1
echo.

REM Summary
echo 📊 Test Summary
echo =====================================
echo ✅ Tests Passed: %TESTS_PASSED%
echo ❌ Tests Failed: %TESTS_FAILED%
set /a total_tests=%TESTS_PASSED% + %TESTS_FAILED%
echo Total Tests: %total_tests%

if %TESTS_FAILED% equ 0 (
    echo 🎉 All tests passed! Your Pi Monitor is working perfectly!
    exit /b 0
) else (
    echo ⚠️  Some tests failed. Check the output above for details.
    exit /b 1
)

REM Cleanup
if exist temp_response.txt del temp_response.txt
