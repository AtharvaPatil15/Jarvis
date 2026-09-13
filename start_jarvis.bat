@echo off
echo.
echo ================================================
echo   JARVIS ASSISTANT - Desktop Mode
echo ================================================
echo.
echo Starting services...
echo.

REM Start the backend server
echo [1/3] Starting Python Backend Server...
start "JARVIS Backend" cmd /k "call .venv\Scripts\activate && python start_backend.py"
timeout /t 3 /nobreak >nul

REM Start Next.js dev server
echo [2/3] Starting Next.js UI Server...
start "JARVIS UI Server" cmd /k "npm run dev"
timeout /t 5 /nobreak >nul

REM Launch Electron window
echo [3/3] Launching Desktop Window...
call npm run app

echo.
echo ================================================
echo   JARVIS is now running!
echo ================================================
