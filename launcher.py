#!/usr/bin/env python3
"""Music Factory Cross-Platform Launcher
音乐生成工厂 - 跨平台启动器
支持 Windows, macOS, Linux
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.resolve()

def find_python():
    """自动查找可用的 Python 解释器"""
    # 优先尝试 python3，然后是 python
    for cmd in ['python3', 'python']:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ 找到 Python: {result.stdout.strip()}")
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    # Windows 上尝试从注册表或常见位置找
    if platform.system() == 'Windows':
        common_paths = [
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe",
            r"C:\Program Files\Python313\python.exe",
            r"C:\Program Files\Python312\python.exe",
            r"C:\Program Files\Python311\python.exe",
        ]
        import os
        for path_template in common_paths:
            path = os.path.expandvars(path_template)
            if Path(path).exists():
                print(f"✅ 找到 Python: {path}")
                return path
    
    print("❌ 错误：未找到 Python 3.10+")
    print("请安装 Python 3.10 或更高版本：https://www.python.org/downloads/")
    sys.exit(1)

def check_venv(python_cmd):
    """检查并创建虚拟环境"""
    venv_path = PROJECT_ROOT / "venv"
    
    if not venv_path.exists():
        print("📦 创建虚拟环境...")
        subprocess.run([python_cmd, "-m", "venv", str(venv_path)], check=True)
        print("✅ 虚拟环境创建完成")
    
    return venv_path

def get_venv_python(venv_path):
    """获取虚拟环境中的 Python"""
    if platform.system() == 'Windows':
        python_path = venv_path / "Scripts" / "python.exe"
    else:
        python_path = venv_path / "bin" / "python"
    
    return str(python_path)

def install_dependencies(python_path):
    """安装依赖"""
    req_file = PROJECT_ROOT / "requirements.txt"
    ai_remover_req = PROJECT_ROOT / "third_party" / "ai-audio-fingerprint-remover" / "requirements.txt"
    
    print("📦 安装依赖...")
    # 使用 -q 静默安装，并确保 pip 是最新版本
    subprocess.run([python_path, "-m", "pip", "install", "-q", "--upgrade", "pip"], check=False)
    
    # 安装主项目依赖
    if req_file.exists():
        result = subprocess.run(
            [python_path, "-m", "pip", "install", "-q", "-r", str(req_file)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"⚠️ 主依赖安装输出: {result.stderr}")
    else:
        print("⚠️ 未找到 requirements.txt")
    
    # 安装 AI fingerprint remover 依赖
    if ai_remover_req.exists():
        print("📦 安装 AI 指纹移除工具依赖...")
        result = subprocess.run(
            [python_path, "-m", "pip", "install", "-q", "-r", str(ai_remover_req)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"⚠️ AI remover 依赖安装输出: {result.stderr}")
        else:
            print("✅ AI 指纹移除工具依赖安装完成")
    else:
        print("⚠️ 未找到 AI remover 依赖文件")
    
    print("✅ 依赖安装完成")

def check_api_config():
    """检查 API 配置"""
    # 注意：此函数在虚拟环境创建前运行，可能缺少 yaml
    # 所以要用 try-except 包裹导入
    try:
        import yaml
    except ImportError:
        # yaml 未安装，跳过检查（会在主程序中再次检查）
        print("⚠️ 跳过 API 配置检查（依赖未安装）")
        return True
    
    config_path = PROJECT_ROOT / "config" / "apis.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        apis = config.get("apis", {})
        missing = []
        for provider in ["deepseek", "openai", "suno", "siliconflow"]:
            key = apis.get(provider, {}).get("api_key", "")
            if not key or "YOUR_" in key:
                missing.append(provider)
        
        if missing:
            print("\n⚠️ 警告：以下 API 密钥未配置")
            for p in missing:
                print(f"   - {p}")
            print(f"\n请编辑 config/apis.yaml 配置 API 密钥")
            return False
        
        print("✅ API 配置检查通过")
        return True
        
    except Exception as e:
        print(f"⚠️ 读取配置失败: {e}")
        print("将在运行时再次检查配置")
        return True  # 不阻止程序运行

def run_cli():
    """运行命令行版本"""
    print("\n" + "="*60)
    print("🎵 Music Factory - 命令行模式")
    print("="*60 + "\n")
    
    python_cmd = find_python()
    venv_path = check_venv(python_cmd)
    venv_python = get_venv_python(venv_path)
    install_dependencies(venv_python)
    
    if not check_api_config():
        print("\n按回车键退出...")
        input()
        return
    
    # 运行主程序
    main_script = PROJECT_ROOT / "main.py"
    print("\n🚀 启动 Music Factory...\n")
    subprocess.run([venv_python, str(main_script)])

def run_web():
    """运行 Web 版本"""
    print("\n" + "="*60)
    print("🎵 Music Factory - Web 控制台模式")
    print("="*60 + "\n")
    
    python_cmd = find_python()
    venv_path = check_venv(python_cmd)
    venv_python = get_venv_python(venv_path)
    install_dependencies(venv_python)
    
    if not check_api_config():
        print("\n按回车键退出...")
        input()
        return
    
    # 运行 Web API
    web_script = PROJECT_ROOT / "web" / "api.py"
    print("\n🚀 启动 Web 控制台...")
    print("📱 服务启动后，请在浏览器中访问显示的地址")
    print("   （如果 5000 端口被占用，会自动使用其他端口）")
    print("按 Ctrl+C 停止服务\n")
    
    try:
        subprocess.run([venv_python, str(web_script)])
    except KeyboardInterrupt:
        print("\n👋 服务已停止")

def check_env():
    """检查环境"""
    print("\n" + "="*60)
    print("🔍 环境检查")
    print("="*60 + "\n")
    
    # 检查 Python
    try:
        python_cmd = find_python()
        result = subprocess.run(
            [python_cmd, '--version'],
            capture_output=True,
            text=True
        )
        print(f"✅ Python: {result.stdout.strip()}")
    except:
        print("❌ Python: 未找到")
        return
    
    # 检查依赖
    try:
        import aiohttp
        print("✅ aiohttp: 已安装")
    except:
        print("❌ aiohttp: 未安装")
    
    try:
        from PIL import Image
        print("✅ Pillow: 已安装")
    except:
        print("❌ Pillow: 未安装")
    
    try:
        import yaml
        print("✅ PyYAML: 已安装")
    except:
        print("❌ PyYAML: 未安装")
    
    try:
        import flask
        print("✅ Flask: 已安装")
    except:
        print("❌ Flask: 未安装")
    
    # 检查 API 配置
    check_api_config()
    
    print("\n" + "="*60)

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Music Factory Launcher')
    parser.add_argument(
        '--mode', '-m',
        choices=['cli', 'web', 'check'],
        default='cli',
        help='运行模式: cli=命令行, web=Web控制台, check=环境检查'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'web':
        run_web()
    elif args.mode == 'check':
        check_env()
    else:
        run_cli()

if __name__ == "__main__":
    main()