@echo off
echo ============================================================
echo   Resume & Cover Letter Generator - Starting...
echo ============================================================
echo.

:: Change to script directory
cd /d "%~dp0"

:: Check if .env exists
if not exist "backend\.env" (
    echo [ERROR] backend\.env file not found!
    echo Please run install.bat first or create .env from .env.example
    pause
    exit /b 1
)

:: Check if dependencies are installed
if not exist "backend\venv" (
    echo [ERROR] Backend virtual environment not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo [ERROR] Frontend dependencies not found!
    echo Please run install.bat first.
    pause
    exit /b 1
)

echo Starting Backend Server...
start "Resume Generator - Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python main.py"

:: Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

echo Starting Frontend Dev Server...
start "Resume Generator - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Wait for frontend to start
echo Waiting for frontend to initialize...
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo   Opening browser...
echo ============================================================
echo.

:: Open default browser to frontend URL
start "" "http://localhost:5173"

echo.
echo Application is running!
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.
echo To stop the application, close the terminal windows.
echo.
pause
