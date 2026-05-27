@echo off
chcp 437 >nul
title Music Factory Web - Visual Console

echo ===========================================
echo    Music Factory Web Launcher
echo    Web Visual Interface - Windows Version
echo ===========================================
echo.

REM Switch to script directory
cd /d "%~dp0"

REM Check Python (try python first, then python3)
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found
        echo.
        echo Please install Python 3.10+:
        echo   Option 1: https://www.python.org/downloads/
        echo   Option 2: Search "Python" in Microsoft Store
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
    )
) else (
    set PYTHON_CMD=python
)

echo [OK] Found Python
%PYTHON_CMD% --version

REM Set virtual environment paths
set "VENV_DIR=venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

REM Check and create virtual environment
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo [INFO] Creating Python virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Upgrade pip
echo.
echo [INFO] Upgrading pip...
pip install --upgrade pip -q

REM Install main dependencies
echo.
echo [INFO] Installing main dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [WARNING] Issues occurred while installing main dependencies, continuing...
) else (
    echo [OK] Main dependencies installed
)

REM Install AI audio processing dependencies
echo.
echo [INFO] Installing AI audio processing dependencies...
pip install "numpy>=1.20.0" "scipy>=1.7.0" "librosa>=0.9.0" "soundfile>=0.10.3" "mutagen>=1.45.0" "matplotlib>=3.4.0" -q
if errorlevel 1 (
    echo [WARNING] Issues occurred while installing AI dependencies, continuing...
) else (
    echo [OK] AI audio processing dependencies installed
)

REM Check FFmpeg
echo.
echo [INFO] Checking FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FFmpeg not found
    echo    Installation instructions:
    echo      1. Download: https://ffmpeg.org/download.html
    echo      2. Extract to C:\ffmpeg or other location
    echo      3. Add to system PATH environment variable
    echo.
    choice /C YN /N /M "Continue without FFmpeg? (Y/N): "
    if errorlevel 2 exit /b 1
) else (
    for /f "tokens=3" %%a in ('ffmpeg -version ^| findstr "ffmpeg version"') do (
        echo [OK] FFmpeg installed: version %%a
    )
)

REM Check port availability
echo.
echo [INFO] Checking port...
set PORT=5001

REM Use PowerShell to check port
powershell -Command "try { $conn = New-Object System.Net.Sockets.TcpClient('127.0.0.1', %PORT%); $conn.Close(); exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [OK] Port %PORT% is available
) else (
    echo [WARNING] Port %PORT% is in use
    echo    Trying to find and close the occupying process...
    
    REM Find process using the port
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
        echo    Found process PID: %%a
        taskkill /PID %%a /F >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Cannot close process, please manually release port %PORT%
            pause
            exit /b 1
        ) else (
            echo [OK] Closed occupying process
            timeout /t 1 /nobreak >nul
        )
    )
)

echo.
echo [INFO] Starting Web Service...
echo ===========================================
echo    After startup, please visit in browser:
echo    http://localhost:%PORT%
echo    (If port 5000 is in use, another port will be used automatically)
echo    Press Ctrl+C to stop service
echo ===========================================
echo.

REM Run Web launcher
"%VENV_PYTHON%" launcher.py --mode web

REM Keep window open on error
if errorlevel 1 (
    echo.
    echo [ERROR] Service failed to start
)

pause