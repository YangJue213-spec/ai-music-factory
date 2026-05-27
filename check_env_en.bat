@echo off
chcp 437 >nul
title Music Factory - Environment Check

echo ===========================================
echo    Music Factory - Environment Check Tool
echo ===========================================
echo.

REM Set Python path
set PYTHON_PATH=C:\Users\19602\AppData\Local\Programs\Python\Python313\python.exe

REM Check Python
"%PYTHON_PATH%" --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python not detected
    echo.
    echo Expected path: %PYTHON_PATH%
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [OK] Python installed
echo.

REM Run check script
"%PYTHON_PATH%" check_env.py

echo.
pause