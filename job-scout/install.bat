@echo off
:: ─────────────────────────────────────────────────────────
::  Job Scout — One-shot installer (Windows)
:: ─────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

echo.
echo   🔍  Job Scout — Installer
echo   ──────────────────────────
echo.

:: 1. Python check
python --version >nul 2>&1
if errorlevel 1 (
  echo   ❌  Python not found. Install from https://www.python.org/downloads/
  pause & exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo   ✓  Python %PY_VER%

:: 2. Virtual environment
set "DIR=%~dp0"
set "VENV=%DIR%.venv"

if not exist "%VENV%" (
  echo   →  Creating virtual environment…
  python -m venv "%VENV%"
)
echo   ✓  Virtual environment ready

:: 3. Install dependencies
echo   →  Installing dependencies (this may take ~60 s)…
"%VENV%\Scripts\pip.exe" install --quiet --upgrade pip
"%VENV%\Scripts\pip.exe" install --quiet -r "%DIR%requirements.txt"
echo   ✓  Dependencies installed

echo.
echo   ✅  Installation complete!
echo.
echo   Start Job Scout with:  start.bat
echo.
pause
