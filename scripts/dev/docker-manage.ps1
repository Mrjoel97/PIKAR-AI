# Pikar AI - Docker Management Script
param([string]$Action = 'status')

$ErrorActionPreference = "Continue"

Write-Host "`n========================================"
Write-Host "  Pikar AI - Docker Management"
Write-Host "========================================`n"

# Check Docker
$dockerRunning = $false
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerRunning = $true }
} catch { }

if (-not $dockerRunning) {
    Write-Host "[!] Docker Desktop is not running!" -ForegroundColor Red
    Write-Host "    Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "    Please wait for Docker to start, then run this script again."
    exit 1
}

Write-Host "[OK] Docker Desktop is running" -ForegroundColor Green

switch ($Action) {
    'start' {
        Write-Host "`n[*] Starting all services..."
        Set-Location $PSScriptRoot\..
        docker-compose up -d
        Start-Sleep -Seconds 5
        docker ps --format "table {{.Names}}`t{{.Status}}"
    }
    'stop' {
        Write-Host "`n[*] Stopping all services..."
        Set-Location $PSScriptRoot\..
        docker-compose down
        Write-Host "[OK] Services stopped" -ForegroundColor Green
    }
    'restart' {
        Write-Host "`n[*] Restarting all services..."
        Set-Location $PSScriptRoot\..
        docker-compose down
        docker-compose up -d
        Start-Sleep -Seconds 5
        docker ps --format "table {{.Names}}`t{{.Status}}"
    }
    'status' {
        Write-Host "`n[*] Container Status:"
        docker ps --format "table {{.Names}}`t{{.Status}}`t{{.Ports}}"
        
        Write-Host "`n[*] Service Health:"
        
        # Backend
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Host "    Backend  (8000): HEALTHY" -ForegroundColor Green
        } catch {
            Write-Host "    Backend  (8000): UNHEALTHY" -ForegroundColor Red
        }
        
        # Frontend
        try {
            $r = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            Write-Host "    Frontend (3000): HEALTHY" -ForegroundColor Green
        } catch {
            Write-Host "    Frontend (3000): UNHEALTHY" -ForegroundColor Red
        }
        
        # Redis
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient("localhost", 6379)
            $tcp.Close()
            Write-Host "    Redis    (6379): HEALTHY" -ForegroundColor Green
        } catch {
            Write-Host "    Redis    (6379): UNHEALTHY" -ForegroundColor Red
        }
    }
    'logs' {
        Write-Host "`n[*] Backend logs (Ctrl+C to exit):"
        docker logs -f pikar-backend --tail 50
    }
    'rebuild' {
        Write-Host "`n[*] Rebuilding all services..."
        Set-Location $PSScriptRoot\..
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
    }
    default {
        Write-Host "Usage: .\docker-manage.ps1 [start|stop|restart|status|logs|rebuild]"
    }
}

Write-Host ""
