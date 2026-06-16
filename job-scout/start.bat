@echo off
:: ─────────────────────────────────────────────────────────
::  Job Scout — Start (Windows)
:: ─────────────────────────────────────────────────────────
setlocal

set "DIR=%~dp0"
set "VENV=%DIR%.venv"

if not exist "%VENV%" (
  echo   ⚠  Run install.bat first.
  pause & exit /b 1
)

set PORT=5000
echo.
echo   🔍  Starting Job Scout on http://localhost:%PORT%
echo   Press Ctrl+C to stop.
echo.

:: Open browser after 2 s
start "" /wait timeout /t 2 /nobreak >nul
start "" "http://localhost:%PORT%"

"%VENV%\Scripts\python.exe" "%DIR%app.py"
pause
