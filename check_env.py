#!/usr/bin/env python3
"""环境检查脚本 - 检查 Music Factory 运行环境"""
import sys
import subprocess
import importlib
from pathlib import Path
import asyncio

# 颜色定义
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

def print_check(name, status, message=""):
    symbol = "✅" if status else "❌"
    color = GREEN if status else RED
    print(f"{color}{symbol} {name}{RESET}")
    if message:
        print(f"   {message}")

def check_python():
    """检查 Python 版本"""
    version = sys.version_info
    is_ok = version.major == 3 and version.minor >= 10
    message = f"当前版本: {version.major}.{version.minor}.{version.micro}"
    if not is_ok:
        message += " (需要 3.10+)"
    return is_ok, message

def check_dependencies():
    """检查依赖包"""
    required = {
        'aiohttp': 'aiohttp>=3.8.0',
        'PIL': 'Pillow>=9.0.0',
        'yaml': 'PyYAML>=6.0',
        'flask': 'flask>=2.3.0',
        'flask_cors': 'flask-cors>=4.0.0'
    }
    
    missing = []
    installed = []
    
    for module, package in required.items():
        try:
            importlib.import_module(module)
            installed.append(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        return False, f"缺少: {', '.join(missing)}", missing
    return True, f"已安装: {', '.join(installed)}", []

def check_api_config():
    """检查 API 密钥配置"""
    try:
        import yaml
        config_path = Path(__file__).parent / "config" / "apis.yaml"
        
        if not config_path.exists():
            return False, "config/apis.yaml 文件不存在"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        apis = config.get("apis", {})
        providers = ["deepseek", "openai", "suno", "siliconflow"]
        
        missing = []
        configured = []
        
        for provider in providers:
            key = apis.get(provider, {}).get("api_key", "")
            if not key or "YOUR_" in key:
                missing.append(provider)
            else:
                configured.append(provider)
        
        if missing:
            return False, f"未配置: {', '.join(missing)} | 已配置: {', '.join(configured)}"
        return True, f"全部配置完成: {', '.join(configured)}"
        
    except Exception as e:
        return False, f"检查失败: {e}"

def check_folders():
    """检查文件夹结构"""
    base = Path(__file__).parent
    required_folders = [
        "config",
        "core",
        "stages",
        "scripts",
        "utils",
        "web",
        "data",
        "output"
    ]
    
    missing = []
    for folder in required_folders:
        if not (base / folder).exists():
            missing.append(folder)
    
    if missing:
        return False, f"缺少文件夹: {', '.join(missing)}"
    return True, "所有必需文件夹都存在"

async def check_network():
    """检查网络连接"""
    try:
        import aiohttp
        urls = {
            "DeepSeek": "https://api.deepseek.com",
            "OpenAI": "https://api.openai.com",
            "Suno": "https://api.acedata.cloud",
            "SiliconFlow": "https://api.siliconflow.cn"
        }
        
        results = []
        timeout = aiohttp.ClientTimeout(total=5)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for name, url in urls.items():
                try:
                    async with session.get(url) as resp:
                        results.append(f"{name}: 可访问")
                except Exception as e:
                    results.append(f"{name}: 无法访问 ({str(e)[:30]})")
        
        all_ok = all("可访问" in r for r in results)
        return all_ok, " | ".join(results)
        
    except Exception as e:
        return False, f"网络检查失败: {e}"

def main():
    print_header("Music Factory 环境检查")
    
    # 1. Python 版本
    print(f"\n{YELLOW}📌 检查 Python 版本...{RESET}")
    ok, msg = check_python()
    print_check("Python 3.10+", ok, msg)
    
    # 2. 依赖包
    print(f"\n{YELLOW}📌 检查依赖包...{RESET}")
    ok, msg, missing = check_dependencies()
    print_check("依赖包", ok, msg)
    
    if not ok:
        print(f"\n{YELLOW}💡 安装依赖命令:{RESET}")
        print(f"   pip install {' '.join(missing)}")
    
    # 3. API 配置
    print(f"\n{YELLOW}📌 检查 API 配置...{RESET}")
    ok, msg = check_api_config()
    print_check("API 密钥", ok, msg)
    
    if not ok:
        print(f"\n{YELLOW}💡 请编辑 config/apis.yaml 文件，填入您的 API 密钥{RESET}")
    
    # 4. 文件夹结构
    print(f"\n{YELLOW}📌 检查文件夹结构...{RESET}")
    ok, msg = check_folders()
    print_check("文件夹结构", ok, msg)
    
    # 5. 网络连接
    print(f"\n{YELLOW}📌 检查网络连接...{RESET}")
    ok, msg = asyncio.run(check_network())
    print_check("API 服务器", ok, msg)
    
    # 总结
    print_header("检查完成")
    
    all_checks = [
        check_python()[0],
        check_dependencies()[0],
        check_api_config()[0],
        check_folders()[0],
        asyncio.run(check_network())[0]
    ]
    
    if all(all_checks):
        print(f"\n{GREEN}🎉 环境检查全部通过！可以运行 Music Factory{RESET}")
        print(f"\n运行方式:")
        print(f"  1. 命令行: {BLUE}start.bat{RESET}")
        print(f"  2. Web界面: {BLUE}web_start.bat{RESET}")
        return 0
    else:
        print(f"\n{RED}⚠️  环境检查未通过，请根据上方提示修复问题{RESET}")
        print(f"\n详细指南请查看: {BLUE}USER_GUIDE.md{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())