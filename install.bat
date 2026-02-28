@echo off
echo ============================================================
echo   Resume ^& Cover Letter Generator v3.0 - Installation
echo ============================================================
echo.

:: Check for Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found.
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
for /f %%v in ('node --version 2^>^&1') do set NODEVER=%%v
echo [OK] Node.js %NODEVER% found.
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

:: Try uv first (recommended), fall back to pip
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Using uv (recommended)...
    uv sync
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Python packages with uv.
        pause
        exit /b 1
    )
    echo Downloading spaCy English model...
    uv run python -m spacy download en_core_web_sm
    echo [OK] Backend dependencies installed via uv.
) else (
    echo uv not found, using pip...
    echo   (Tip: install uv for faster installs: pip install uv)
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
    echo Downloading spaCy English model...
    python -m spacy download en_core_web_sm
    echo [OK] Backend dependencies installed via pip.
)
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
    echo   IMPORTANT: Configure at least one AI provider API key!
    echo ============================================================
    echo.
    echo   1. Open backend\.env in a text editor
    echo   2. Add your API key for one or more providers:
    echo      - Gemini:  https://aistudio.google.com/
    echo      - Claude:  https://console.anthropic.com/
    echo      - OpenAI-compatible: any local or remote endpoint
    echo   3. Configure via the Settings panel in the UI after launch
    echo.
) else (
    echo [OK] .env file already exists.
)

echo.
echo ============================================================
echo   Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Ensure at least one AI provider API key is set in backend\.env
echo      or configure it later in the Settings panel
echo   2. Run 'start.bat' to launch the application
echo.
pause
