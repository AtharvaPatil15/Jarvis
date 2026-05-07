@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."

echo.
echo ================================================
echo   JARVIS ASSISTANT - Desktop Mode
echo ================================================
echo.
echo Starting services...
echo.

echo [1/3] Starting Python Backend Server...
start "JARVIS Backend" cmd /k "call .venv\Scripts\activate && python apps\backend\run_server.py"
timeout /t 3 /nobreak >nul

echo [2/3] Starting Next.js UI Server...
start "JARVIS UI Server" cmd /k "npm run dev:web"
timeout /t 5 /nobreak >nul

echo [3/3] Launching Desktop Window...
call npm run desktop

echo.
echo ================================================
echo   JARVIS is now running!
echo ================================================

popd
