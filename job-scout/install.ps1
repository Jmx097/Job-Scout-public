# Job Scout - Installer (PowerShell)
# Run: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = Join-Path $DIR ".venv"

Write-Host ""
Write-Host "  Job Scout - Installer" -ForegroundColor Cyan
Write-Host "  --------------------------"
Write-Host ""

# 1. Python check
$pycheck = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
Write-Host "  OK  $pycheck" -ForegroundColor Green

# 2. Venv
if (-not (Test-Path $VENV)) {
    Write-Host "  Creating virtual environment..."
    python -m venv $VENV
}
Write-Host "  OK  Virtual environment ready" -ForegroundColor Green

# 3. Dependencies
Write-Host "  Installing dependencies (may take ~60s)..."
& "$VENV\Scripts\pip.exe" install --quiet --upgrade pip
& "$VENV\Scripts\pip.exe" install --quiet -r "$DIR\requirements.txt"
Write-Host "  OK  Dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "  Done! Now run:" -ForegroundColor Green
Write-Host "  powershell -ExecutionPolicy Bypass -File build.ps1" -ForegroundColor Yellow
Write-Host ""
