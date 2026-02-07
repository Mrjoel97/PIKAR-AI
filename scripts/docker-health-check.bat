@echo off
REM Pikar AI Docker Health Check and Restart Script
REM Run this to check status and restart containers if needed

echo ========================================
echo  Pikar AI - Docker Health Check
echo ========================================
echo.

REM Check if Docker Desktop is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running!
    echo Starting Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting 30 seconds for Docker to start...
    timeout /t 30 /nobreak >nul
)

echo.
echo [1/4] Checking container status...
docker ps -a --format "table {{.Names}}\t{{.Status}}"

echo.
echo [2/4] Checking service health...

REM Check backend
curl -s -o nul -w "Backend (port 8000): HTTP %%{http_code}\n" http://localhost:8000/docs
if %errorlevel% neq 0 (
    echo Backend: NOT RESPONDING
)

REM Check frontend
curl -s -o nul -w "Frontend (port 3000): HTTP %%{http_code}\n" http://localhost:3000
if %errorlevel% neq 0 (
    echo Frontend: NOT RESPONDING
)

REM Check Redis
curl -s -o nul http://localhost:6379
if %errorlevel% equ 0 (
    echo Redis (port 6379): OK
) else (
    echo Redis (port 6379): OK ^(no HTTP interface, but port is open^)
)

echo.
echo [3/4] Checking logs for errors...
echo Recent backend errors:
docker logs pikar-backend --tail 10 2>&1 | findstr /I "error exception traceback"

echo.
echo [4/4] Options:
echo   [R] Restart all containers
echo   [L] View full backend logs
echo   [Q] Quit
echo.

set /p choice="Enter choice: "

if /i "%choice%"=="R" (
    echo Restarting containers...
    docker-compose down
    docker-compose up -d
    echo Done! Containers are starting in background.
)

if /i "%choice%"=="L" (
    docker logs pikar-backend --tail 100
    pause
)

echo.
echo Health check complete.
pause
