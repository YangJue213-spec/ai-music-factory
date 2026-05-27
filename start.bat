@echo off
chcp 65001 >nul
title Music Factory - 音乐生成工厂

echo ===========================================
echo    Music Factory Launcher
echo    音乐生成工厂 - Windows版
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
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

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

echo.
echo [🎵] 启动 Music Factory...
echo ===========================================

REM 运行启动器
"%VENV_PYTHON%" launcher.py --mode cli

REM 如果启动失败，保持窗口打开
if errorlevel 1 (
    echo.
    echo [❌] 程序异常退出
)

pause