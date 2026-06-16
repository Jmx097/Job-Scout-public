@echo off
:: ─────────────────────────────────────────────────────────
::  Job Scout — Build one-click .exe (Windows)
::  Produces: dist\JobScout.exe
:: ─────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

echo.
echo   🔨  Job Scout — Build Executable
echo   ──────────────────────────────────
echo.

set "DIR=%~dp0"
set "VENV=%DIR%.venv"

:: 1. Ensure venv exists
if not exist "%VENV%" (
  echo   ⚠  Run install.bat first.
  pause & exit /b 1
)

:: 2. Install build deps
echo   →  Installing PyInstaller + Pillow…
"%VENV%\Scripts\pip.exe" install --quiet pyinstaller pillow
echo   ✓  Build tools ready

:: 3. Generate icon
echo   →  Generating icon…
"%VENV%\Scripts\python.exe" "%DIR%make_icon.py"

:: 4. Clean previous build
if exist "%DIR%dist" rmdir /s /q "%DIR%dist"
if exist "%DIR%build" rmdir /s /q "%DIR%build"

:: 5. Build
echo   →  Building executable (this takes 1-3 minutes)…
"%VENV%\Scripts\pyinstaller.exe" "%DIR%JobScout.spec" --distpath "%DIR%dist" --workpath "%DIR%build" --noconfirm

if errorlevel 1 (
  echo.
  echo   ✗  Build failed. See output above.
  pause & exit /b 1
)

echo.
echo   ✅  Build complete!
echo.
echo   Executable: dist\JobScout.exe
echo   Double-click it to launch Job Scout.
echo.
pause
