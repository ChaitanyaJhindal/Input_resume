@echo off
setlocal EnableDelayedExpansion
title FacultyScreen - Unified Service Controller
color 0A

cd /d "%~dp0"

set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=start"

if /I "%ACTION%"=="help" goto :cmd_help
if /I "%ACTION%"=="-h" goto :cmd_help
if /I "%ACTION%"=="--help" goto :cmd_help
if /I "%ACTION%"=="/?" goto :cmd_help
if /I "%ACTION%"=="stop" goto :cmd_stop
if /I "%ACTION%"=="status" goto :cmd_status
if /I "%ACTION%"=="restart" goto :cmd_restart
if /I "%ACTION%"=="start" goto :cmd_start

echo [!] Unknown command: %ACTION%
echo.
goto :cmd_help

:: =====================================================================
:cmd_help
echo =====================================================================
echo               FACULTYSCREEN - UNIFIED SERVICE LAUNCHER
echo =====================================================================
echo Usage:
echo   start.bat             Start Frontend, Backend, DB and open Control Menu
echo   start.bat start       Same as default start
echo   start.bat status      Check health of Frontend, Backend, AI Keys, and DB
echo   start.bat restart     Stop and cleanly restart all services
echo   start.bat stop        Stop all running Frontend and Backend services
echo   start.bat help        Show this help message
echo =====================================================================
exit /b 0

:: =====================================================================
:cmd_stop
echo =====================================================================
echo            STOPPING ALL FACULTYSCREEN SERVICES
echo =====================================================================
call :stop_services
echo [OK] All FacultyScreen services stopped.
exit /b 0

:: =====================================================================
:cmd_status
echo =====================================================================
echo            FACULTYSCREEN SERVICE HEALTH ^& DIAGNOSTICS
echo =====================================================================
call :print_status
exit /b 0

:: =====================================================================
:cmd_restart
echo =====================================================================
echo            RESTARTING ALL FACULTYSCREEN SERVICES
echo =====================================================================
call :stop_services
timeout /t 2 /nobreak >nul
goto :cmd_start

:: =====================================================================
:cmd_start
echo =====================================================================
echo               FACULTYSCREEN ALL-IN-ONE CONTROLLER
echo     Backend [FastAPI :8000] + Frontend [Next.js :3000] + SQLite/AI
echo =====================================================================
echo.

call :stop_services
call :ensure_environment
call :init_database
call :launch_backend
call :launch_frontend
call :wait_for_services

echo.
call :print_status
echo.
echo [*] Opening Web Dashboard: http://localhost:3000
start "" http://localhost:3000

:menu_loop
echo.
echo ---------------------------------------------------------------------
echo   CONTROL MENU:  [S] Status   [R] Restart   [B] Open Browser
echo                  [X] Stop All ^& Exit        [Q] Keep Running ^& Close
echo ---------------------------------------------------------------------
choice /C SRBXQ /N /M "Select action [S/R/B/X/Q]: "
if errorlevel 5 goto :menu_keep_running
if errorlevel 4 goto :menu_stop_exit
if errorlevel 3 goto :menu_browser
if errorlevel 2 goto :menu_restart
if errorlevel 1 goto :menu_status
goto :menu_loop

:menu_status
echo.
call :print_status
goto :menu_loop

:menu_browser
echo [*] Opening http://localhost:3000 ...
start "" http://localhost:3000
goto :menu_loop

:menu_restart
echo.
echo [*] Restarting Backend and Frontend services...
call :stop_services
timeout /t 2 /nobreak >nul
call :launch_backend
call :launch_frontend
call :wait_for_services
call :print_status
goto :menu_loop

:menu_stop_exit
echo.
call :stop_services
echo [OK] All FacultyScreen services shut down. Goodbye!
exit /b 0

:menu_keep_running
echo.
echo [*] Services remain running in separate terminal windows.
echo     Run "start.bat stop" or "start.bat status" anytime to manage them.
exit /b 0

:: =====================================================================
:: SUBROUTINES
:: =====================================================================

:stop_services
echo [*] Stopping any active listeners on ports 8000 and 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo     - Stopping Backend process tree PID %%a
    taskkill /F /T /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    echo     - Stopping Frontend process tree PID %%a
    taskkill /F /T /PID %%a >nul 2>&1
)
exit /b 0

:ensure_environment
if not exist ".venv\Scripts\python.exe" (
    echo [*] Python virtual environment not found. Setting up .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Failed to create .venv. Install Python 3.10+ and ensure it is on PATH.
        pause
        exit /b 1
    )
    echo [*] Installing backend requirements...
    .venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
    .venv\Scripts\pip.exe install -r backend\requirements.txt
)

if not exist "apps\web\node_modules" (
    echo [*] Frontend dependencies not found. Running npm install...
    pushd apps\web
    call npm install
    popd
)

if not exist "data\processed" mkdir data\processed
if not exist "data\uploads" mkdir data\uploads
if not exist "data\results" mkdir data\results
if not exist "data\logs" mkdir data\logs
if not exist "data\institutions" mkdir data\institutions
exit /b 0

:init_database
echo [*] Verifying SQLite WAL database and configuration files...
.venv\Scripts\python.exe -c "from backend.app.database.models import init_db; init_db()" >nul 2>&1
if errorlevel 1 (
    echo [!] Warning: Database initialization check returned a non-zero exit code.
) else (
    echo [OK] Database schema ready: data\facultyscreen.db
)
exit /b 0

:launch_backend
echo [*] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "FacultyScreen Backend - FastAPI :8000" cmd /k "cd /d ""%~dp0"" && title FacultyScreen Backend && color 0B && .venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"
exit /b 0

:launch_frontend
echo [*] Starting Next.js Frontend on http://localhost:3000 ...
start "FacultyScreen Frontend - Next.js :3000" cmd /k "cd /d ""%~dp0apps\web"" && title FacultyScreen Frontend && color 0D && npm run dev -- -p 3000"
exit /b 0

:wait_for_services
echo [*] Waiting for Backend :8000 and Frontend :3000 to respond...
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -c "import time, urllib.request; deadline = time.time() + 30; be = False; fe = False; probe = lambda u: urllib.request.urlopen(u, timeout=1.5).status; exec('while time.time() < deadline:\n try:\n  if not be and probe(\'http://127.0.0.1:8000/health\') == 200: be = True\n except Exception: pass\n try:\n  if not fe and probe(\'http://127.0.0.1:3000\') < 500: fe = True\n except Exception: pass\n if be and fe: break\n time.sleep(1.0)'); print('    Backend  :8000 ->', 'READY' if be else 'STARTING...'); print('    Frontend :3000 ->', 'READY' if fe else 'STARTING...')"
) else (
    timeout /t 5 /nobreak >nul
)
exit /b 0

:print_status
if not exist ".venv\Scripts\python.exe" (
    echo [!] Python environment .venv not initialized yet. Run start.bat first.
    exit /b 0
)
.venv\Scripts\python.exe -c "import json, urllib.request, pathlib; exec('def safe_get(u):\n try:\n  r = urllib.request.urlopen(u, timeout=2.0)\n  return r.status, r.read().decode(\'utf-8\', \'ignore\')\n except Exception:\n  return None, \'\'\nh_st, _ = safe_get(\'http://127.0.0.1:8000/health\')\ns_st, s_body = safe_get(\'http://127.0.0.1:8000/api/settings/system-status\')\nf_st, _ = safe_get(\'http://127.0.0.1:3000\')\ninfo = json.loads(s_body) if (s_st == 200 and s_body) else {}\nmode = (\'Mock Mode\' if info.get(\'mock_mode\') else \'Live Groq Mode\') if info else \'Unknown (Backend offline)\'\nkeys = str(info.get(\'groq_keys_count\', 0)) + \' configured\' if info else \'N/A (Backend offline)\'\nmodels = str(info.get(\'groq_reasoning_model\', \'-\')) + \' / \' + str(info.get(\'groq_vision_model\', \'-\')) if info else \'N/A\'\ndb_ok = \'READY\' if pathlib.Path(\'data/facultyscreen.db\').exists() else \'NOT CREATED YET\'\npdfs = len(list(pathlib.Path(\'Input_resumes\').glob(\'*.pdf\'))) if pathlib.Path(\'Input_resumes\').exists() else 0\nprint(\'  Frontend Web App  [http://localhost:3000]       :\', \'ONLINE\' if (f_st and f_st < 500) else \'OFFLINE\')\nprint(\'  Backend API       [http://127.0.0.1:8000]       :\', \'ONLINE\' if h_st == 200 else \'OFFLINE\')\nprint(\'  Swagger Docs      [http://127.0.0.1:8000/docs]  :\', \'ONLINE\' if h_st == 200 else \'OFFLINE\')\nprint(\'  AI Engine Mode                                  :\', mode)\nprint(\'  Groq API Keys                                   :\', keys)\nprint(\'  Reasoning / Vision                              :\', models)\nprint(\'  SQLite Database   [data/facultyscreen.db]       :\', db_ok)\nprint(\'  Source Resumes    [Input_resumes/]              :\', str(pdfs) + \' PDFs\')')"
exit /b 0
