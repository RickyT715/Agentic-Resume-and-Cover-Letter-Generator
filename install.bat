@echo off
echo ============================================================
echo   Resume & Cover Letter Generator - Installation Script
echo ============================================================
echo.

:: Check for Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo [OK] Python found.
echo.

:: Check for Node.js
echo [2/4] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo [OK] Node.js found.
echo.

:: Check for pdflatex
echo [3/4] Checking LaTeX installation...
pdflatex --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] pdflatex is not installed or not in PATH.
    echo.
    echo Please install MiKTeX from https://miktex.org/download
    echo After installation:
    echo   1. Open MiKTeX Console
    echo   2. Go to Settings ^> General
    echo   3. Set "Install missing packages on-the-fly" to "Always"
    echo   4. Restart your terminal
    echo.
    echo Press any key to continue installation anyway...
    pause >nul
) else (
    echo [OK] pdflatex found.
)
echo.

:: Install backend dependencies
echo [4/4] Installing dependencies...
echo.
echo Installing backend Python packages...
cd /d "%~dp0backend"
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)
echo [OK] Backend dependencies installed.
echo.

:: Install frontend dependencies
echo Installing frontend npm packages...
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install npm packages.
    pause
    exit /b 1
)
echo [OK] Frontend dependencies installed.
echo.

:: Check for .env file
cd /d "%~dp0backend"
if not exist ".env" (
    echo.
    echo [IMPORTANT] Creating .env file from template...
    copy .env.example .env
    echo.
    echo ============================================================
    echo   IMPORTANT: You need to add your Gemini API key!
    echo ============================================================
    echo.
    echo   1. Open backend\.env in a text editor
    echo   2. Replace 'your_gemini_api_key_here' with your actual key
    echo   3. Get your API key from: https://aistudio.google.com/
    echo.
)

echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Make sure you have set your GEMINI_API_KEY in backend\.env
echo   2. Run 'start.bat' to launch the application
echo.
pause
