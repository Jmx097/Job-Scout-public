# Plinko Pocket: Job Scout - Build Executable (PowerShell)
# Run: powershell -ExecutionPolicy Bypass -File build.ps1

$ErrorActionPreference = "Stop"
$DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$VENV = Join-Path $DIR ".venv"

Write-Host ""
Write-Host "  Plinko Pocket: Job Scout - Build" -ForegroundColor Green
Write-Host "  ----------------------------------"
Write-Host ""

if (-not (Test-Path $VENV)) {
    Write-Host "  ERROR: Run install.ps1 first." -ForegroundColor Red
    exit 1
}

# 1. Build deps
Write-Host "  Installing PyInstaller..."
& "$VENV\Scripts\pip.exe" install --quiet pyinstaller
Write-Host "  OK  PyInstaller ready" -ForegroundColor Green

# 2. Clean previous build
if (Test-Path "$DIR\dist")  { Remove-Item "$DIR\dist"  -Recurse -Force }
if (Test-Path "$DIR\build") { Remove-Item "$DIR\build" -Recurse -Force }

# 3. Build
Write-Host "  Building executable (1-3 minutes, please wait)..."
& "$VENV\Scripts\pyinstaller.exe" "$DIR\JobScout.spec" `
    --distpath "$DIR\dist" `
    --workpath "$DIR\build" `
    --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Build failed. See output above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  Build complete!" -ForegroundColor Green
Write-Host "  Executable: $DIR\dist\JobScout.exe" -ForegroundColor Yellow
Write-Host "  Double-click it to launch." -ForegroundColor Yellow
Write-Host ""
