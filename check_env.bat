@echo off
chcp 65001 >nul
title Music Factory - 环境检查

echo ===========================================
echo    Music Factory - 环境检查工具
echo ===========================================
echo.

REM 设置 Python 绝对路径
set PYTHON_PATH=C:\Users\19602\AppData\Local\Programs\Python\Python313\python.exe

REM Check Python
"%PYTHON_PATH%" --version >nul 2>&1
if errorlevel 1 (
    echo [❌] 未检测到 Python
    echo.
    echo 预期路径: %PYTHON_PATH%
    echo 请先安装 Python 3.10+ 
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [✓] Python 已安装
echo.

REM Run check script
"%PYTHON_PATH%" check_env.py

echo.
pause
