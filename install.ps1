<#
.SYNOPSIS
    SysWatch v2.1 - Windows Installer
.DESCRIPTION
    Installs Python dependencies, initializes database, starts the application
#>

param(
    [string]$InstallDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  SysWatch v2.1 Installer" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

$BackendDir = Join-Path $InstallDir "backend"

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "ERROR: Python is not installed." -ForegroundColor Red
    Write-Host "Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$python = $pythonCmd.Source
Write-Host "Python found: $python"

# Create virtual environment
$VenvDir = Join-Path $InstallDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment..."
    & $python -m venv $VenvDir
}

# Activate and install
$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "Installing Python dependencies..."
& $PipExe install --upgrade pip
& $PipExe install -r (Join-Path $BackendDir "requirements.txt")

# Create .env if it doesn't exist
$EnvFile = Join-Path $InstallDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item (Join-Path $InstallDir ".env.example") $EnvFile
    
    # Generate secrets
    $jwtSecret = & $PythonExe -c "import secrets; print(secrets.token_hex(32))"
    $encKey = & $PythonExe -c "import secrets; print(secrets.token_hex(32))"
    
    $content = Get-Content $EnvFile
    $content = $content -replace "JWT_SECRET=.*", "JWT_SECRET=$jwtSecret"
    $content = $content -replace "ENCRYPTION_KEY=.*", "ENCRYPTION_KEY=$encKey"
    $content | Set-Content $EnvFile
    
    Write-Host "Generated JWT_SECRET and ENCRYPTION_KEY"
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit .env to configure database and settings"
Write-Host "  2. Ensure MySQL/MariaDB is running"
Write-Host "  3. Start: cd backend; python app.py"
Write-Host "  4. Access: http://localhost:5000"
Write-Host ""
Write-Host "Default login: admin@syswatch.local / admin123"
Write-Host "CHANGE THE PASSWORD IMMEDIATELY!"
Write-Host ""
Write-Host "To install the agent as a Windows service:"
Write-Host "  python agents/syswatch_agent.py --install"
Write-Host ""