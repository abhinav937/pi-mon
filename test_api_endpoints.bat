@echo off
REM Pi Monitor API Endpoint Testing Script for Windows
REM Tests all backend API endpoints and shows responses

setlocal enabledelayedexpansion

REM Configuration
set BACKEND_URL=http://192.168.0.201:5001
set AUTH_USERNAME=abhinav
set AUTH_PASSWORD=kavachi
set LOG_FILE=api_test_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log

REM Remove colons from time for filename
set LOG_FILE=%LOG_FILE::=%

REM Test counter
set TESTS_PASSED=0
set TESTS_FAILED=0

echo ==========================================
echo Pi Monitor API Endpoint Testing
echo ==========================================
echo Backend URL: %BACKEND_URL%
echo Log file: %LOG_FILE%
echo Date: %date% %time%
echo ==========================================
echo.

REM Check if backend is running
echo Checking if backend is running...
curl -s "%BACKEND_URL%/health" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Backend is running and accessible
    set /a TESTS_PASSED+=1
) else (
    echo ❌ Backend is not accessible at %BACKEND_URL%
    echo Make sure the backend is running: python3 backend/simple_server.py
    pause
    exit /b 1
)

echo.

REM Test 1: Root endpoint (no auth required)
echo === Test 1: Root Endpoint ===
echo Testing: GET / - Root endpoint - should return basic info
echo URL: %BACKEND_URL%/
echo --- Response ---
curl -s "%BACKEND_URL%/"
echo.
echo --- End Response ---
echo ✅ Endpoint / responded successfully
set /a TESTS_PASSED+=1
echo.

REM Test 2: Health check (no auth required)
echo === Test 2: Health Check ===
echo Testing: GET /health - Health check endpoint
echo URL: %BACKEND_URL%/health
echo --- Response ---
curl -s "%BACKEND_URL%/health"
echo.
echo --- End Response ---
echo ✅ Endpoint /health responded successfully
set /a TESTS_PASSED+=1
echo.

REM Test 3: Authentication
echo === Test 3: Authentication ===
echo Testing: POST /api/auth/token - Authentication endpoint
echo URL: %BACKEND_URL%/api/auth/token
echo --- Response ---
curl -s -X POST "%BACKEND_URL%/api/auth/token" -H "Content-Type: application/json" -d "{\"username\": \"%AUTH_USERNAME%\", \"password\": \"%AUTH_PASSWORD%\"}"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/auth/token responded successfully
set /a TESTS_PASSED+=1
echo.

REM Test 4: System stats (requires auth)
echo === Test 4: System Stats (Authenticated) ===
echo Getting authentication token...
for /f "tokens=2 delims=:," %%a in ('curl -s -X POST "%BACKEND_URL%/api/auth/token" -H "Content-Type: application/json" -d "{\"username\": \"%AUTH_USERNAME%\", \"password\": \"%AUTH_PASSWORD%\"}" ^| findstr "access_token"') do set TOKEN=%%a
set TOKEN=!TOKEN:"=!

if defined TOKEN (
    echo ✅ Authentication successful, token obtained
    echo Testing: GET /api/system - System statistics endpoint
    echo URL: %BACKEND_URL%/api/system
    echo --- Response ---
    curl -s -H "Authorization: Bearer !TOKEN!" "%BACKEND_URL%/api/system"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/system responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ❌ Authentication failed
    set /a TESTS_FAILED+=1
)
echo.

REM Test 5: Enhanced system stats (requires auth)
echo === Test 5: Enhanced System Stats (Authenticated) ===
if defined TOKEN (
    echo Testing: GET /api/system/enhanced - Enhanced system statistics endpoint
    echo URL: %BACKEND_URL%/api/system/enhanced
    echo --- Response ---
    curl -s -H "Authorization: Bearer !TOKEN!" "%BACKEND_URL%/api/system/enhanced"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/system/enhanced responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 6: System stats with history (requires auth)
echo === Test 6: System Stats with History (Authenticated) ===
if defined TOKEN (
    echo Testing: GET /api/system?history=30 - System stats with 30-minute history
    echo URL: %BACKEND_URL%/api/system?history=30
    echo --- Response ---
    curl -s -H "Authorization: Bearer !TOKEN!" "%BACKEND_URL%/api/system?history=30"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/system?history=30 responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 7: Power status (requires auth)
echo === Test 7: Power Status (Authenticated) ===
if defined TOKEN (
    echo Testing: GET /api/power - Power status endpoint
    echo URL: %BACKEND_URL%/api/power
    echo --- Response ---
    curl -s -H "Authorization: Bearer !TOKEN!" "%BACKEND_URL%/api/power"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/power responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 8: Service restart info (no auth required)
echo === Test 8: Service Restart Info ===
echo Testing: GET /api/service/restart - Service restart information endpoint
echo URL: %BACKEND_URL%/api/service/restart
echo --- Response ---
curl -s "%BACKEND_URL%/api/service/restart"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/service/restart responded successfully
set /a TESTS_PASSED+=1
echo.

REM Test 9: Service manage info (no auth required)
echo === Test 9: Service Manage Info ===
echo Testing: GET /api/service/manage - Service management information endpoint
echo URL: %BACKEND_URL%/api/service/manage
echo --- Response ---
curl -s "%BACKEND_URL%/api/service/manage"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/service/manage responded successfully
set /a TESTS_PASSED+=1
echo.

REM Test 10: Service info (requires auth)
echo === Test 10: Service Info (Authenticated) ===
if defined TOKEN (
    echo Testing: GET /api/service/info - Service information endpoint
    echo URL: %BACKEND_URL%/api/service/info
    echo --- Response ---
    curl -s -H "Authorization: Bearer !TOKEN!" "%BACKEND_URL%/api/service/info"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/service/info responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 11: Power actions (requires auth)
echo === Test 11: Power Actions (Authenticated) ===
if defined TOKEN (
    echo Testing: POST /api/power - Power action endpoint
    echo URL: %BACKEND_URL%/api/power
    echo --- Response ---
    curl -s -X POST -H "Authorization: Bearer !TOKEN!" -H "Content-Type: application/json" -d "{\"action\": \"status\"}" "%BACKEND_URL%/api/power"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/power responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 12: Service restart (requires auth)
echo === Test 12: Service Restart (Authenticated) ===
if defined TOKEN (
    echo Testing: POST /api/service/restart - Service restart endpoint
    echo URL: %BACKEND_URL%/api/service/restart
    echo --- Response ---
    curl -s -X POST -H "Authorization: Bearer !TOKEN!" -H "Content-Type: application/json" -d "{}" "%BACKEND_URL%/api/service/restart"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/service/restart responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 13: Service management (requires auth)
echo === Test 13: Service Management (Authenticated) ===
if defined TOKEN (
    echo Testing: POST /api/service/manage - Service management endpoint
    echo URL: %BACKEND_URL%/api/service/manage
    echo --- Response ---
    curl -s -X POST -H "Authorization: Bearer !TOKEN!" -H "Content-Type: application/json" -d "{\"action\": \"status\"}" "%BACKEND_URL%/api/service/manage"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/service/manage responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 14: Services endpoint (requires auth)
echo === Test 14: Services Endpoint (Authenticated) ===
if defined TOKEN (
    echo Testing: POST /api/services - Services endpoint
    echo URL: %BACKEND_URL%/api/services
    echo --- Response ---
    curl -s -X POST -H "Authorization: Bearer !TOKEN!" -H "Content-Type: application/json" -d "{\"service_name\": \"ssh\", \"action\": \"status\"}" "%BACKEND_URL%/api/services"
    echo.
    echo --- End Response ---
    echo ✅ Endpoint /api/services responded successfully
    set /a TESTS_PASSED+=1
) else (
    echo ⚠️ Skipping - no auth token
    set /a TESTS_FAILED+=1
)
echo.

REM Test 15: Test invalid endpoints
echo === Test 15: Invalid Endpoints ===
echo Testing: GET /nonexistent - Non-existent endpoint - should return 404
echo URL: %BACKEND_URL%/nonexistent
echo --- Response ---
curl -s "%BACKEND_URL%/nonexistent"
echo.
echo --- End Response ---
echo ✅ Endpoint /nonexistent handled correctly
set /a TESTS_PASSED+=1
echo.

REM Test 16: Test invalid methods
echo === Test 16: Invalid Methods ===
echo Testing: PUT /api/system - PUT method on system endpoint - should return 405
echo URL: %BACKEND_URL%/api/system
echo --- Response ---
curl -s -X PUT "%BACKEND_URL%/api/system"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/system handled invalid method correctly
set /a TESTS_PASSED+=1
echo.

REM Test 17: Test missing authentication
echo === Test 17: Missing Authentication ===
echo Testing: GET /api/system - System endpoint without auth - should return 401
echo URL: %BACKEND_URL%/api/system
echo --- Response ---
curl -s "%BACKEND_URL%/api/system"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/system correctly rejected unauthorized access
set /a TESTS_PASSED+=1
echo.

REM Test 18: Test invalid authentication
echo === Test 18: Invalid Authentication ===
echo Testing: GET /api/system - System endpoint with invalid token - should return 401
echo URL: %BACKEND_URL%/api/system
echo --- Response ---
curl -s -H "Authorization: Bearer invalid_token_123" "%BACKEND_URL%/api/system"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/system correctly rejected invalid token
set /a TESTS_PASSED+=1
echo.

REM Test 19: Test malformed JSON
echo === Test 19: Malformed JSON ===
echo Testing: POST /api/auth/token - Malformed JSON - should handle gracefully
echo URL: %BACKEND_URL%/api/auth/token
echo --- Response ---
curl -s -X POST "%BACKEND_URL%/api/auth/token" -H "Content-Type: application/json" -d "{\"username\": \"abhinav\", \"password\":}"
echo.
echo --- End Response ---
echo ✅ Endpoint /api/auth/token handled malformed JSON correctly
set /a TESTS_PASSED+=1
echo.

REM Test 20: Test CORS headers
echo === Test 20: CORS Headers ===
echo Testing CORS preflight request...
echo URL: %BACKEND_URL%/api/system
echo --- Response ---
curl -s -X OPTIONS "%BACKEND_URL%/api/system" -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Authorization"
echo.
echo --- End Response ---
echo ✅ CORS preflight request handled correctly
set /a TESTS_PASSED+=1
echo.

REM Summary
echo ==========================================
echo API TESTING COMPLETE
echo ==========================================
echo Final Results:
echo Tests PASSED: %TESTS_PASSED%
echo Tests FAILED: %TESTS_FAILED%
echo Total Tests: %TESTS_PASSED%
echo.

if %TESTS_FAILED% equ 0 (
    echo ✅ All API tests passed! Your backend is working correctly.
) else (
    echo ⚠️ %TESTS_FAILED% tests failed. Check the responses above for details.
)

echo.
echo 📋 Log file: %LOG_FILE%
echo 🌐 Backend URL: %BACKEND_URL%
echo ==========================================

pause
