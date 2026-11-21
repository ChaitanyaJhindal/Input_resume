@echo off
title Stop FacultyScreen
color 0C

echo Stopping FacultyScreen servers on ports 8000 and 3000...

:: Terminate process listening on port 8000 (Backend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Terminating backend process PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)

:: Terminate process listening on port 3000 (Frontend)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Terminating frontend process PID %%a...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All FacultyScreen servers stopped.
ping -n 3 127.0.0.1 >nul
