#!/usr/bin/env powershell
<#
.SYNOPSIS
    Docker helper script for QR Registros development environment
.DESCRIPTION
    Simplifies common Docker operations
.EXAMPLE
    .\docker-dev.ps1 start
    .\docker-dev.ps1 logs app
    .\docker-dev.ps1 test
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'stop', 'restart', 'logs', 'test', 'migrate', 'shell', 'db-shell', 'status', 'clean', 'build')]
    [string]$Command = 'help',
    
    [Parameter(Position = 1)]
    [string]$Service = 'app'
)

$ErrorActionPreference = "Stop"
$compose_file = "docker-compose.dev.yml"
$compose_cmd = "docker-compose -f $compose_file"

function Start-Environment {
    Write-Host "=== Starting QR Registros Development Environment ===" -ForegroundColor Cyan
    Write-Host "Building and starting services..." -ForegroundColor Yellow
    
    & docker-compose -f $compose_file up --build -d
    
    Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    & docker-compose -f $compose_file ps
    
    Write-Host "`n[OK] Services started successfully!" -ForegroundColor Green
    Write-Host "- App:      http://localhost:8000" -ForegroundColor Cyan
    Write-Host "- Database: localhost:5432" -ForegroundColor Cyan
}

function Stop-Environment {
    Write-Host "=== Stopping QR Registros Development Environment ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file down
    Write-Host "[OK] Services stopped" -ForegroundColor Green
}

function Restart-Environment {
    Write-Host "=== Restarting QR Registros Development Environment ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file restart $Service
    Write-Host "[OK] Service restarted: $Service" -ForegroundColor Green
}

function Show-Logs {
    Write-Host "=== Docker Logs for: $Service ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file logs -f $Service
}

function Run-Tests {
    Write-Host "=== Running Auth Tests ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file exec app pytest tests/test_auth_*.py -v
}

function Run-Migrations {
    Write-Host "=== Running Database Migrations ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file exec app python -m alembic upgrade head
    
    Write-Host "`n=== Migration Status ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file exec app python -m alembic current
}

function Open-Shell {
    Write-Host "=== Opening Python Shell ===" -ForegroundColor Cyan
    Write-Host "Run 'exit()' to quit" -ForegroundColor Yellow
    & docker-compose -f $compose_file exec app python
}

function Open-DbShell {
    Write-Host "=== Opening PostgreSQL Shell ===" -ForegroundColor Cyan
    Write-Host "Run '\q' to quit" -ForegroundColor Yellow
    & docker-compose -f $compose_file exec db psql -U postgres -d attendance_db
}

function Show-Status {
    Write-Host "=== Service Status ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file ps
    
    Write-Host "`n=== Database Tables ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file exec db psql -U postgres -d attendance_db -c "\dt"
}

function Clean-Environment {
    Write-Host "=== Cleaning Environment ===" -ForegroundColor Cyan
    Write-Host "WARNING: This will remove all data!" -ForegroundColor Red
    $confirm = Read-Host "Continue? (yes/no)"
    
    if ($confirm -eq "yes") {
        & docker-compose -f $compose_file down -v
        Write-Host "[OK] Environment cleaned" -ForegroundColor Green
    } else {
        Write-Host "Cancelled" -ForegroundColor Yellow
    }
}

function Build-Image {
    Write-Host "=== Building Docker Image ===" -ForegroundColor Cyan
    & docker-compose -f $compose_file build --no-cache app
    Write-Host "[OK] Image built successfully" -ForegroundColor Green
}

function Show-Help {
    Write-Host @"
QR Registros Docker Helper Script

USAGE:
    .\docker-dev.ps1 [COMMAND] [SERVICE]

COMMANDS:
    start       - Start development environment
    stop        - Stop all services
    restart     - Restart a service (default: app)
    logs        - View logs for a service (default: app)
    test        - Run auth tests
    migrate     - Apply database migrations
    shell       - Open Python shell in app container
    db-shell    - Open PostgreSQL shell
    status      - Show service status and tables
    clean       - Remove all data and containers
    build       - Rebuild Docker image
    help        - Show this help message

SERVICES:
    app         - Application container
    db          - Database container

EXAMPLES:
    .\docker-dev.ps1 start              # Start environment
    .\docker-dev.ps1 logs app           # View app logs
    .\docker-dev.ps1 logs db            # View database logs
    .\docker-dev.ps1 restart            # Restart app
    .\docker-dev.ps1 test               # Run tests
    .\docker-dev.ps1 migrate            # Apply migrations
    .\docker-dev.ps1 db-shell           # Open psql
    .\docker-dev.ps1 clean              # Clean environment

"@
}

# Execute command
switch ($Command) {
    'start' { Start-Environment }
    'stop' { Stop-Environment }
    'restart' { Restart-Environment }
    'logs' { Show-Logs }
    'test' { Run-Tests }
    'migrate' { Run-Migrations }
    'shell' { Open-Shell }
    'db-shell' { Open-DbShell }
    'status' { Show-Status }
    'clean' { Clean-Environment }
    'build' { Build-Image }
    'help' { Show-Help }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
