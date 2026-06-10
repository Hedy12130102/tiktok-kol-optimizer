@echo off
echo ============================================
echo   TikTok KOL Optimizer - Starting Backend
echo ============================================
echo.

cd /d "%~dp0"

:: ── Step 1: Kill ALL processes on port 8000 ────────────────────
echo [1/3] Stopping old server processes...
set KILLED=0
for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000"') do (
    taskkill /PID %%a /F >nul 2>&1
    if not errorlevel 1 (set KILLED=1)
)
:: If port-based kill didn't work, nuke all python children too
for /f "tokens=2" %%a in ('tasklist /fi "IMAGENAME eq python.exe" /fo table /nh 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
:: Wait a moment and verify port is free
timeout /t 2 /nobreak >nul
netstat -ano | find ":8000" >nul 2>&1
if not errorlevel 1 (
    echo WARNING: Port 8000 still occupied! Trying force kill...
    for /f "tokens=5" %%a in ('netstat -ano ^| find ":8000"') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
)
echo     Done.

:: ── Step 2: Find Python ────────────────────────────────────────
echo [2/3] Detecting Python...
set PYTHON=python
if exist ".conda\python.exe" (
    set PYTHON=.conda\python.exe
    echo     Using project conda Python
) else (
    echo     Using system Python
)

:: ── Step 3: Start server ───────────────────────────────────────
echo [3/3] Starting server at http://localhost:8000
echo.
echo Press Ctrl+C to stop.
echo ============================================
echo.

%PYTHON% -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
pause
