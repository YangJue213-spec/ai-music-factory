@echo off
chcp 65001 >nul
title Music Factory Web - 可视化控制台

echo ===========================================
echo    Music Factory Web Launcher
echo    音乐生成工厂 - Web可视化版
echo ===========================================
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 检查 Python（优先 python，然后是 python3）
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo [❌] 错误：未找到 Python
        echo.
        echo 请安装 Python 3.10+：
        echo   方法1: 访问 https://www.python.org/downloads/
        echo   方法2: Microsoft Store 搜索 "Python"
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python3
    )
) else (
    set PYTHON_CMD=python
)

echo [✓] 找到 Python
%PYTHON_CMD% --version

REM 设置虚拟环境路径
set "VENV_DIR=venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

REM 检查并创建虚拟环境
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo.
    echo [📦] 创建 Python 虚拟环境...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [❌] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [✓] 虚拟环境创建成功
) else (
    echo [✓] 虚拟环境已存在
)

REM 激活虚拟环境
call "%VENV_DIR%\Scripts\activate.bat"

REM 升级 pip
echo.
echo [📦] 升级 pip...
pip install --upgrade pip -q

REM 安装主项目依赖
echo.
echo [📦] 检查并安装主项目依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [⚠️] 主项目依赖安装出现问题，尝试继续...
) else (
    echo [✓] 主项目依赖已安装/更新
)

REM 安装 AI fingerprint remover 依赖
echo.
echo [📦] 检查并安装 AI 音频处理依赖...
pip install "numpy>=1.20.0" "scipy>=1.7.0" "librosa>=0.9.0" "soundfile>=0.10.3" "mutagen>=1.45.0" "matplotlib>=3.4.0" -q
if errorlevel 1 (
    echo [⚠️] AI 音频处理依赖安装出现问题，尝试继续...
) else (
    echo [✓] AI 音频处理依赖已安装/更新
)

REM 检查 FFmpeg
echo.
echo [🔍] 检查 FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [⚠️] 未找到 FFmpeg
    echo    建议安装：
    echo      1. 下载：https://ffmpeg.org/download.html
    echo      2. 解压到 C:\ffmpeg 或其他位置
    echo      3. 将路径添加到系统环境变量 PATH
    echo.
    choice /C YN /N /M "是否继续启动？(Y/N): "
    if errorlevel 2 exit /b 1
) else (
    for /f "tokens=3" %%a in ('ffmpeg -version ^| findstr "ffmpeg version"') do (
        echo [✓] FFmpeg 已安装: 版本 %%a
    )
)

REM 检查端口是否被占用
echo.
echo [🔍] 检查端口...
set PORT=5001

REM 使用 PowerShell 检查端口
powershell -Command "try { $conn = New-Object System.Net.Sockets.TcpClient('127.0.0.1', %PORT%); $conn.Close(); exit 0 } catch { exit 1 }" >nul 2>&1

if errorlevel 1 (
    echo [✓] 端口 %PORT% 可用
) else (
    echo [⚠️] 端口 %PORT% 已被占用
    echo    尝试查找并关闭占用进程...
    
    REM 查找占用端口的进程
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
        echo    发现进程 PID: %%a
        taskkill /PID %%a /F >nul 2>&1
        if errorlevel 1 (
            echo [❌] 无法关闭进程，请手动释放端口 %PORT%
            pause
            exit /b 1
        ) else (
            echo [✓] 已关闭占用进程
            timeout /t 1 /nobreak >nul
        )
    )
)

echo.
echo [🌐] 启动 Web 服务...
echo ===========================================
echo    服务启动后，请在浏览器中访问：
echo    http://localhost:%PORT%
echo    （如果 5000 端口被占用，会自动使用其他端口）
echo    按 Ctrl+C 停止服务
echo ===========================================
echo.

REM 运行 Web 启动器
"%VENV_PYTHON%" launcher.py --mode web

REM 如果启动失败，保持窗口打开
if errorlevel 1 (
    echo.
    echo [❌] 服务启动失败
)

pause