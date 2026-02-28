@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo   Resume ^& Cover Letter Generator v3.0 - Starting...
echo ============================================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: ---------------------------------------------------------------
:: Read PORT and FRONTEND_PORT from backend\.env (if present)
:: ---------------------------------------------------------------
set BACKEND_PORT=48765
set FRONTEND_PORT=45173

if exist "backend\.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("backend\.env") do (
        set "LINE=%%A"
        if "!LINE!"=="PORT" set "BACKEND_PORT=%%B"
        if "!LINE!"=="FRONTEND_PORT" set "FRONTEND_PORT=%%B"
    )
) else (
    echo [ERROR] backend\.env file not found!
    echo Please run install.bat first or create .env from .env.example
    pause
    exit /b 1
)

echo   Backend port:  !BACKEND_PORT!
echo   Frontend port: !FRONTEND_PORT!
echo.

:: ---------------------------------------------------------------
:: Detect backend runner (venv or uv)
:: ---------------------------------------------------------------
set BACKEND_CMD=

if exist "backend\.venv\Scripts\activate.bat" (
    set BACKEND_CMD=cd /d "%~dp0backend" ^&^& call .venv\Scripts\activate.bat ^&^& python main.py
    goto :backend_ready
)
if exist "backend\venv\Scripts\activate.bat" (
    set BACKEND_CMD=cd /d "%~dp0backend" ^&^& call venv\Scripts\activate.bat ^&^& python main.py
    goto :backend_ready
)

:: No venv found - try uv
uv --version >nul 2>&1
if !errorlevel! equ 0 (
    set BACKEND_CMD=cd /d "%~dp0backend" ^&^& uv run python main.py
    goto :backend_ready
)

echo [ERROR] Backend virtual environment not found and uv is not installed!
echo Please run install.bat first.
pause
exit /b 1

:backend_ready

:: ---------------------------------------------------------------
:: Check frontend dependencies
:: ---------------------------------------------------------------
if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: Start backend
:: ---------------------------------------------------------------
echo Starting Backend Server...
start "Resume Generator - Backend" cmd /k "!BACKEND_CMD!"

:: Wait for backend to start and verify health
echo Waiting for backend to initialize...
set RETRIES=0
:healthcheck
timeout /t 2 /nobreak >nul
set /a RETRIES+=1
curl -s -o nul -w "" http://localhost:!BACKEND_PORT!/health >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Backend is healthy.
    goto :backend_healthy
)
if !RETRIES! lss 10 (
    echo   Waiting... ^(attempt !RETRIES!/10^)
    goto :healthcheck
)
echo [WARNING] Backend health check timed out.
echo   The server may still be starting. Check the backend terminal window.

:backend_healthy
echo.

:: ---------------------------------------------------------------
:: Start frontend
:: ---------------------------------------------------------------
echo Starting Frontend Dev Server...
start "Resume Generator - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Wait for frontend to start
echo Waiting for frontend to initialize...
timeout /t 4 /nobreak >nul

echo.
echo ============================================================
echo   Opening browser...
echo ============================================================
echo.

:: Open default browser to frontend URL
start "" "http://localhost:!FRONTEND_PORT!"

echo.
echo Application is running!
echo.
echo   Frontend: http://localhost:!FRONTEND_PORT!
echo   Backend:  http://localhost:!BACKEND_PORT!
echo   Health:   http://localhost:!BACKEND_PORT!/health
echo   API Docs: http://localhost:!BACKEND_PORT!/docs
echo.
echo To stop the application, close the backend and frontend terminal windows.
echo.
pause
endlocal
