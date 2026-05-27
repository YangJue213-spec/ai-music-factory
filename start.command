#!/bin/bash
# Music Factory Launcher for macOS
# 音乐生成工厂 - Mac 启动脚本（带自动依赖安装）

# 获取脚本所在目录
cd "$(dirname "$0")"

echo "🚀 Music Factory Launcher"
echo "=============================="

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python3"
    echo "请安装 Python 3.10+："
    echo "  方法1: 访问 https://www.python.org/downloads/"
    echo "  方法2: 运行: brew install python"
    read -p "按回车键退出..."
    exit 1
fi

echo "✅ 找到 Python3: $(python3 --version)"

# 设置虚拟环境路径
VENV_DIR="venv"
VENV_PYTHON="$VENV_DIR/bin/python"

# 检查并创建虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "❌ 创建虚拟环境失败"
        read -p "按回车键退出..."
        exit 1
    fi
    echo "✅ 虚拟环境创建成功"
else
    echo "✅ 虚拟环境已存在"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 升级 pip
echo ""
echo "📦 升级 pip..."
pip install --upgrade pip -q

# 安装主项目依赖
echo ""
echo "📦 检查并安装主项目依赖..."
pip install -r requirements.txt -q
if [ $? -eq 0 ]; then
    echo "✅ 主项目依赖已安装/更新"
else
    echo "⚠️  主项目依赖安装出现问题，尝试继续..."
fi

# 安装 AI fingerprint remover 依赖
echo ""
echo "📦 检查并安装 AI 音频处理依赖..."
pip install "numpy>=1.20.0" "scipy>=1.7.0" "librosa>=0.9.0" "soundfile>=0.10.3" "mutagen>=1.45.0" "matplotlib>=3.4.0" -q
if [ $? -eq 0 ]; then
    echo "✅ AI 音频处理依赖已安装/更新"
else
    echo "⚠️  AI 音频处理依赖安装出现问题，尝试继续..."
fi

# 检查 FFmpeg
echo ""
echo "🔍 检查 FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3)
    echo "✅ FFmpeg 已安装: 版本 $FFMPEG_VERSION"
else
    echo "⚠️  未找到 FFmpeg"
    echo "   建议安装: brew install ffmpeg"
    echo "   或者运行: ./scripts/install_ffmpeg.sh"
    echo ""
    read -p "是否继续启动？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🎵 启动 Music Factory..."
echo "=============================="

# 运行启动器
"$VENV_PYTHON" launcher.py --mode cli

# 如果启动失败，保持窗口打开
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 程序异常退出"
fi

read -p "按回车键退出..."