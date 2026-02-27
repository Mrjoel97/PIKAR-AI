<#
.SYNOPSIS
    Starts backend+redis in Docker and runs the frontend natively for fast HMR.

.DESCRIPTION
    On Windows, Docker volume mounts can be slow, making frontend hot-reload laggy.
    This script starts only the backend and Redis in Docker, then runs the Next.js
    frontend natively on the host machine for instant hot module replacement (HMR).

.NOTES
    Prerequisites:
    - Docker Desktop running
    - Node.js installed (v18+)
    - npm dependencies installed (cd frontend && npm install)
#>

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $PSScriptRoot

Write-Host "`n[1/3] Starting backend + Redis in Docker..." -ForegroundColor Cyan
docker compose -f "$RootDir\docker-compose.yml" up -d backend redis

Write-Host "`n[2/3] Waiting for backend to be ready..." -ForegroundColor Cyan
$maxRetries = 30
$retryCount = 0
do {
    Start-Sleep -Seconds 3
    $retryCount++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health/cache" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  Backend is ready!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "  Waiting... ($retryCount/$maxRetries)" -ForegroundColor Yellow
    }
} while ($retryCount -lt $maxRetries)

if ($retryCount -ge $maxRetries) {
    Write-Host "  WARNING: Backend may not be fully ready yet. Starting frontend anyway..." -ForegroundColor Yellow
}

Write-Host "`n[3/3] Starting frontend natively (fast HMR)..." -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop the frontend (run 'docker compose down' to stop backend)`n" -ForegroundColor DarkGray

Set-Location "$RootDir\frontend"
& npm run dev
