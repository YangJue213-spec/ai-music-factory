#!/usr/bin/env python3
"""Music Factory 诊断脚本 - 排查启动问题"""
import sys
import os
from pathlib import Path

print("="*60)
print("🔍 Music Factory 诊断工具")
print("="*60)
print()

# 1. 检查 Python 版本
print("1️⃣  Python 版本")
print(f"   版本: {sys.version}")
print(f"   路径: {sys.executable}")
print()

# 2. 检查关键文件
print("2️⃣  关键文件检查")
base = Path(__file__).parent
files_to_check = [
    "web/static/index.html",
    "web/static/style.css",
    "web/static/app.js",
    "web/api.py",
    "config/apis.yaml",
    "config/settings.yaml",
]

all_exist = True
for f in files_to_check:
    path = base / f
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"   {status} {f}")
    if not exists:
        all_exist = False

if not all_exist:
    print("   ⚠️  有文件缺失！")
print()

# 3. 检查依赖
print("3️⃣  依赖检查")
dependencies = {
    'flask': 'Flask',
    'flask_cors': 'Flask-CORS',
    'yaml': 'PyYAML',
    'aiohttp': 'aiohttp',
    'PIL': 'Pillow',
}

missing = []
for module, name in dependencies.items():
    try:
        __import__(module)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} - 未安装")
        missing.append(name)

if missing:
    print(f"\n   请运行: pip install {' '.join(missing)}")
print()

# 4. 检查端口
print("4️⃣  端口检查")
import socket
port = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    sock.bind(('127.0.0.1', port))
    print(f"   ✅ 端口 {port} 可用")
    sock.close()
except socket.error as e:
    print(f"   ❌ 端口 {port} 被占用: {e}")
print()

# 5. 尝试启动 Flask（测试模式）
print("5️⃣  Flask 启动测试")
try:
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def test():
        return "OK"
    
    # 测试静态文件
    static_folder = base / 'web' / 'static'
    print(f"   静态文件夹: {static_folder}")
    print(f"   存在: {static_folder.exists()}")
    if static_folder.exists():
        files = list(static_folder.iterdir())
        print(f"   文件数: {len(files)}")
        for f in files:
            print(f"      - {f.name}")
    
    print("   ✅ Flask 可以正常启动")
    
except Exception as e:
    print(f"   ❌ Flask 启动失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("="*60)
print("诊断完成")
print("="*60)