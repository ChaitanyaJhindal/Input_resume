@echo off
title FacultyScreen - All-in-One Launcher
color 0A

echo =====================================================================
echo                FACULTYSCREEN ALL-IN-ONE LAUNCHER
echo     AI-Powered Academic Faculty Screening and Curation Platform
echo =====================================================================
echo.

cd /d "%~dp0"

:: -------------------------------------------------------------------
:: 1. Clear any lingering stale processes on ports 8000 and 3000
:: -------------------------------------------------------------------
echo [*] Checking for conflicting processes on ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo     [>] Freeing port 8000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo     [>] Freeing port 3000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)

:: -------------------------------------------------------------------
:: 2. Verify / Auto-Setup Python Virtual Environment
:: -------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [*] Python virtual environment not found. Setting up .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Failed to create Python virtual environment.
        echo     Please ensure Python 3.10+ is installed and on your PATH.
        pause
        exit /b 1
    )
    echo [*] Installing backend dependencies...
    .venv\Scripts\python -m pip install --upgrade pip >nul 2>&1
    .venv\Scripts\pip install -r backend\requirements.txt
)

:: -------------------------------------------------------------------
:: 3. Verify / Auto-Setup Node.js Frontend Dependencies
:: -------------------------------------------------------------------
if not exist "apps\web\node_modules" (
    echo [*] Frontend dependencies not found. Running npm install in apps\web...
    cd apps\web
    call npm install
    cd ..\..
)

:: -------------------------------------------------------------------
:: 4. Ensure Data and Cache Directories Exist
:: -------------------------------------------------------------------
if not exist "data\processed" mkdir data\processed
if not exist "data\results" mkdir data\results
if not exist "data\logs" mkdir data\logs
if not exist "data\institutions" mkdir data\institutions

:: -------------------------------------------------------------------
:: 5. Launch FastAPI Backend on Port 8000
:: -------------------------------------------------------------------
echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "FacultyScreen Backend (FastAPI)" cmd /k "title FacultyScreen Backend && color 0B && .venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

:: -------------------------------------------------------------------
:: 6. Launch Next.js Frontend on Port 3000
:: -------------------------------------------------------------------
echo [*] Starting Next.js Frontend on http://localhost:3000 ...
start "FacultyScreen Frontend (Next.js)" cmd /k "title FacultyScreen Frontend && color 0D && cd apps\web && npm run dev -- -p 3000"

:: -------------------------------------------------------------------
:: 7. Wait and Open Recruiter Dashboard in Browser
:: -------------------------------------------------------------------
echo.
echo [*] Initializing services (waiting 4 seconds)...
ping -n 5 127.0.0.1 >nul

echo [*] Opening FacultyScreen Recruiter Dashboard in default browser...
start http://localhost:3000

echo.
echo =====================================================================
echo   FacultyScreen is LIVE and RUNNING!
echo   -------------------------------------------------------------------
echo   - Web Dashboard:  http://localhost:3000
echo   - Backend API:    http://127.0.0.1:8000
echo   - Swagger Docs:   http://127.0.0.1:8000/docs
echo   - Architecture:   BRAIN.md
echo =====================================================================
echo.
echo Both servers are actively running in separate windows.
echo To shut down all servers at any time, run: stop_facultyscreen.bat
echo.
pause
