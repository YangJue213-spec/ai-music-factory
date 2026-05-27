#!/usr/bin/env python3
"""Web API - Flask backend for Music Factory Web UI"""
import os
import sys
import json
import yaml
import asyncio
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import check_api_keys, run_pipeline, build_stages_config, PROJECT_ROOT
from utils.config import load_all_configs, save_apis_config, save_sources_config, save_singers_config

app = Flask(__name__)
CORS(app)

# 禁用 werkzeug 的 HTTP 访问日志，只保留错误日志
import logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

# Global state
pipeline_thread = None
pipeline_running = False
current_progress = {
    "status": "idle",
    "stage": "",
    "progress": 0,
    "message": "",
    "logs": []
}
# 用于存储正在运行的子进程，以便停止时可以终止
active_processes = []
stop_event = threading.Event()

def run_async(f):
    """Run async function in sync context"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Get static folder path - 使用绝对路径确保正确
WEB_DIR = Path(__file__).parent.resolve()
STATIC_FOLDER = WEB_DIR / 'static'

@app.route('/')
def index():
    """Serve main HTML"""
    return send_from_directory(str(STATIC_FOLDER), 'index.html')

@app.route('/static/<path:path>')
def static_files(path):
    """Serve static files"""
    return send_from_directory(str(STATIC_FOLDER), path)

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        config = load_all_configs(str(PROJECT_ROOT / "config"))
        # Hide actual API keys
        apis = config.get("apis", {})
        safe_apis = {}
        for provider, cfg in apis.items():
            key = cfg.get("api_key", "")
            safe_apis[provider] = {
                "configured": bool(key and "YOUR_" not in key),
                "base_url": cfg.get("base_url", ""),
                "model": cfg.get("model", "")
            }
        return jsonify({
            "success": True,
            "apis": safe_apis,
            "singers": config.get("singers", {})
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update API configuration"""
    try:
        data = request.json
        
        # Load current config
        config = load_all_configs(str(PROJECT_ROOT / "config"))
        apis = config.get("apis", {})
        
        # Update keys
        for provider, key in data.get("apis", {}).items():
            if provider in apis:
                if key and not key.startswith("***"):  # Only update if changed
                    apis[provider]["api_key"] = key
        
        # Save back using the config utility
        save_apis_config(apis, str(PROJECT_ROOT / "config"))
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get pipeline status"""
    return jsonify({
        "running": pipeline_running,
        **current_progress
    })

@app.route('/api/start', methods=['POST'])
@run_async
async def start_pipeline():
    """Start the pipeline"""
    global pipeline_running, pipeline_thread, current_progress
    
    if pipeline_running:
        return jsonify({"success": False, "error": "Pipeline already running"})
    
    data = request.json or {}
    max_songs = data.get('max_songs')
    
    # Load all configurations using the unified loader
    config = load_all_configs(str(PROJECT_ROOT / "config"))
    
    # Build stages configuration
    stages_config = build_stages_config(config)
    config["stages"] = stages_config
    
    if not check_api_keys(config):
        return jsonify({"success": False, "error": "API keys not configured"})
    
    # Reset progress
    current_progress = {
        "status": "running",
        "stage": "Initializing",
        "progress": 0,
        "message": "Starting...",
        "logs": []
    }
    
    def progress_callback(data):
        """Update progress from pipeline"""
        global current_progress
        # 使用显式赋值而不是 update()，确保线程安全
        current_progress["stage"] = data.get("stage", current_progress.get("stage", ""))
        current_progress["step"] = data.get("step", current_progress.get("step", 0))
        current_progress["total_steps"] = data.get("total_steps", current_progress.get("total_steps", 5))
        current_progress["progress"] = data.get("progress", current_progress.get("progress", 0))
        current_progress["message"] = data.get("message", current_progress.get("message", ""))
        current_progress["fetched"] = data.get("fetched", current_progress.get("fetched", 0))
        current_progress["cleaned"] = data.get("cleaned", current_progress.get("cleaned", 0))
        current_progress["generated"] = data.get("generated", current_progress.get("generated", 0))
    
    def run_pipeline_wrapper():
        global pipeline_running, current_progress
        try:
            asyncio.run(run_pipeline(config, max_songs=max_songs, progress_callback=progress_callback))
            current_progress["status"] = "completed"
            current_progress["message"] = "全部完成！"
        except Exception as e:
            current_progress["status"] = "error"
            current_progress["message"] = f"错误: {e}"
        finally:
            pipeline_running = False
    
    pipeline_running = True
    pipeline_thread = threading.Thread(target=run_pipeline_wrapper)
    pipeline_thread.start()
    
    return jsonify({"success": True})

@app.route('/api/stop', methods=['POST'])
def stop_pipeline():
    """Stop the pipeline"""
    global pipeline_running, stop_event
    
    if not pipeline_running:
        return jsonify({"success": False, "error": "Pipeline not running"})
    
    # 设置停止标志
    stop_event.set()
    pipeline_running = False
    current_progress["status"] = "stopping"
    current_progress["message"] = "正在停止...（等待当前操作完成）"
    
    # 使用 app.logger 代替未定义的 logger
    app.logger.info("🛑 收到停止请求，等待当前操作完成后停止...")
    
    return jsonify({
        "success": True, 
        "message": "停止请求已发送，将在当前操作完成后停止"
    })

@app.route('/api/files', methods=['GET'])
def list_files():
    """List generated files"""
    try:
        output_dir = Path(__file__).parent.parent / "output"
        files = []
        
        # List musics directory
        musics_dir = output_dir / "musics"
        if musics_dir.exists():
            for date_dir in sorted(musics_dir.iterdir(), reverse=True):
                if date_dir.is_dir():
                    date_files = []
                    for f in sorted(date_dir.iterdir()):
                        if f.is_file():
                            date_files.append({
                                "name": f.name,
                                "path": str(f.relative_to(output_dir)),
                                "size": f.stat().st_size,
                                "mtime": f.stat().st_mtime
                            })
                    files.append({
                        "date": date_dir.name,
                        "files": date_files
                    })
        
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/files/download/<path:filepath>')
def download_file(filepath):
    """Download a file"""
    output_dir = Path(__file__).parent.parent / "output"
    file_path = output_dir / filepath
    
    if not file_path.exists():
        return jsonify({"success": False, "error": "File not found"})
    
    return send_from_directory(output_dir, filepath, as_attachment=True)

@app.route('/api/archive', methods=['POST'])
def archive_files():
    """Archive files to today's folder"""
    try:
        data = request.json or {}
        count = data.get('count', 0)  # 0 means all
        
        output_dir = Path(__file__).parent.parent / "output"
        suno_dir = output_dir / "suno_output"
        lyrics_dir = output_dir / "pure_lyrics"
        covers_dir = output_dir / "covers"
        musics_dir = output_dir / "musics"
        
        # Create today's folder
        today = datetime.now()
        date_folder = f"{today.month:02d}.{today.day:02d}"
        target_dir = musics_dir / date_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all mp3 files from suno_output
        mp3_files = sorted(suno_dir.glob("*.mp3"))
        
        if not mp3_files:
            return jsonify({
                "success": True,
                "message": "没有找到可归档的文件",
                "archived": 0,
                "target_dir": str(target_dir)
            })
        
        # Limit by count if specified
        if count > 0:
            mp3_files = mp3_files[:count]
        
        archived = []
        failed = []
        
        for mp3_file in mp3_files:
            try:
                # Get base filename (without extension)
                base_name = mp3_file.stem
                
                # Copy MP3
                dst_mp3 = target_dir / f"{base_name}.mp3"
                shutil.copy2(mp3_file, dst_mp3)
                
                # Copy lyrics if exists
                src_txt = lyrics_dir / f"{base_name}.txt"
                if src_txt.exists():
                    dst_txt = target_dir / f"{base_name}.txt"
                    shutil.copy2(src_txt, dst_txt)
                
                # Copy cover if exists
                src_png = covers_dir / f"{base_name}.png"
                if src_png.exists():
                    dst_png = target_dir / f"{base_name}.png"
                    shutil.copy2(src_png, dst_png)
                
                archived.append(base_name)
                
            except Exception as e:
                failed.append({"file": base_name, "error": str(e)})
        
        # Generate report
        report = {
            "date": date_folder,
            "target_dir": str(target_dir),
            "total": len(mp3_files),
            "archived": len(archived),
            "failed": len(failed),
            "files": archived
        }
        
        # Save report to file
        report_path = target_dir / f"_archive_report_{datetime.now():%H%M%S}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"Music Factory Archive Report\n")
            f.write(f"Date: {date_folder}\n")
            f.write(f"Time: {datetime.now():%H:%M:%S}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Total Files: {report['total']}\n")
            f.write(f"Successfully Archived: {report['archived']}\n")
            f.write(f"Failed: {report['failed']}\n\n")
            f.write("Archived Files:\n")
            for fname in archived:
                f.write(f"  - {fname}\n")
        
        return jsonify({
            "success": True,
            "message": f"归档完成: {len(archived)} 首成功, {len(failed)} 首失败",
            "archived": len(archived),
            "failed": len(failed),
            "target_dir": str(target_dir),
            "date_folder": date_folder,
            "files": archived
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/deduplication', methods=['GET'])
def get_deduplication_status():
    """Get deduplication status"""
    try:
        lyrics_dir = Path(__file__).parent.parent / "output" / "pure_lyrics"
        
        fingerprints = set()
        if lyrics_dir.exists():
            for f in lyrics_dir.iterdir():
                if f.suffix == '.txt':
                    # Extract song name from filename
                    name = f.stem  # Remove .txt
                    fingerprints.add(name)
        
        return jsonify({
            "success": True,
            "total_fingerprints": len(fingerprints),
            "sample": list(fingerprints)[:20]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get recent log entries"""
    try:
        log_dir = Path(__file__).parent.parent / "data" / "logs"
        logs = []
        
        if log_dir.exists():
            # Get most recent log file
            log_files = sorted(log_dir.glob("*.log"), reverse=True)
            if log_files:
                with open(log_files[0], 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    logs = lines[-100:]  # Last 100 lines
        
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/check', methods=['GET'])
def check_environment():
    """Check environment status"""
    try:
        import sys
        import importlib
        from pathlib import Path
        import yaml
        
        results = {
            "python": {"status": False, "message": ""},
            "dependencies": {"status": False, "message": ""},
            "api_config": {"status": False, "message": ""},
            "folders": {"status": False, "message": ""}
        }
        
        # 1. Python version
        version = sys.version_info
        results["python"]["status"] = version.major == 3 and version.minor >= 10
        results["python"]["message"] = f"{version.major}.{version.minor}.{version.micro}"
        
        # 2. Dependencies
        required = ['aiohttp', 'PIL', 'yaml', 'flask', 'flask_cors']
        missing = []
        for module in required:
            try:
                importlib.import_module(module)
            except ImportError:
                missing.append(module)
        results["dependencies"]["status"] = len(missing) == 0
        results["dependencies"]["message"] = "全部安装" if not missing else f"缺少: {', '.join(missing)}"
        
        # 3. API Config
        config_path = Path(__file__).parent.parent / "config" / "apis.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            apis = config.get("apis", {})
            providers = ["deepseek", "openai", "suno", "siliconflow"]
            missing_apis = []
            for provider in providers:
                key = apis.get(provider, {}).get("api_key", "")
                if not key or "YOUR_" in key:
                    missing_apis.append(provider)
            results["api_config"]["status"] = len(missing_apis) == 0
            results["api_config"]["message"] = "全部配置" if not missing_apis else f"未配置: {', '.join(missing_apis)}"
        else:
            results["api_config"]["message"] = "配置文件不存在"
        
        # 4. Folders
        base = Path(__file__).parent.parent
        required_folders = ["config", "core", "stages", "scripts", "utils", "web", "data", "output"]
        missing_folders = [f for f in required_folders if not (base / f).exists()]
        results["folders"]["status"] = len(missing_folders) == 0
        results["folders"]["message"] = "完整" if not missing_folders else f"缺少: {', '.join(missing_folders)}"
        
        # Overall status
        all_ok = all(r["status"] for r in results.values())
        
        return jsonify({
            "success": True,
            "ready": all_ok,
            "checks": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    try:
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f) or {}
        return jsonify({"success": True, "settings": settings})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        data = request.json
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(settings_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Sources Management API
@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get music sources configuration"""
    try:
        sources_path = Path(__file__).parent.parent / "config" / "sources.yaml"
        if sources_path.exists():
            with open(sources_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # 将字符串列表转换为字典格式（兼容前端）
        monitored_artists_raw = config.get("monitored_artists", [])
        monitored_artists = []
        for artist in monitored_artists_raw:
            if isinstance(artist, str):
                monitored_artists.append({"name": artist, "enabled": True})
            elif isinstance(artist, dict):
                monitored_artists.append(artist)
        
        return jsonify({
            "success": True,
            "sources": {
                "monitored_artists": monitored_artists,
                "chart_sources": config.get("chart_sources", [])
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/sources', methods=['POST'])
def update_sources():
    """Update music sources configuration"""
    try:
        data = request.json
        sources_path = Path(__file__).parent.parent / "config" / "sources.yaml"
        
        # Load existing or create new
        if sources_path.exists():
            with open(sources_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # 前端发送的是字典格式，保存为字符串列表（与主项目兼容）
        artists_raw = data.get("monitored_artists", [])
        monitored_artists = []
        for artist_item in artists_raw:
            if isinstance(artist_item, dict):
                if artist_item.get("enabled", True):
                    monitored_artists.append(artist_item.get("name", ""))
            elif isinstance(artist_item, str):
                monitored_artists.append(artist_item)
        
        # 过滤空字符串
        monitored_artists = [a for a in monitored_artists if a]
        
        config["monitored_artists"] = monitored_artists
        config["chart_sources"] = data.get("chart_sources", [])
        
        # Save
        with open(sources_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Singers Management API
@app.route('/api/singers', methods=['GET'])
def get_singers():
    """Get singers configuration"""
    try:
        singers_path = Path(__file__).parent.parent / "config" / "singers.yaml"
        if singers_path.exists():
            with open(singers_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # singers.yaml 使用 female_singers 和 male_singers 作为键名
        return jsonify({
            "success": True,
            "singers": {
                "male": config.get("male_singers", []),
                "female": config.get("female_singers", []),
                "version_suffixes": config.get("version_suffixes", [])
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/singers', methods=['POST'])
def update_singers():
    """Update singers configuration"""
    try:
        data = request.json
        singers_path = Path(__file__).parent.parent / "config" / "singers.yaml"
        
        # Load existing or create new
        if singers_path.exists():
            with open(singers_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # Update - 使用正确的键名
        config["male_singers"] = data.get("male", [])
        config["female_singers"] = data.get("female", [])
        
        # Save
        with open(singers_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


if __name__ == '__main__':
    import socket
    import time
    
    def find_available_port(start_port=5001, end_port=5100):
        """Find an available port and return it
        
        Note: macOS Monterey+ uses port 5000 for AirPlay/ControlCenter,
        so we start from 5001 to avoid conflicts.
        """
        for port in range(start_port, end_port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # 尝试绑定到端口进行测试
                sock.bind(('127.0.0.1', port))
                sock.close()
                # 立即再次测试确保端口真的可用
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(('127.0.0.1', port))
                test_sock.close()
                return port
            except socket.error:
                pass
            finally:
                try:
                    sock.close()
                except:
                    pass
        return None
    
    # 查找可用端口（从5001开始，避免macOS ControlCenter冲突）
    port = find_available_port()
    if port is None:
        print("❌ 错误: 无法找到可用端口 (5001-5100 都被占用)")
        print("   请检查是否有其他程序占用了这些端口")
        sys.exit(1)
    
    print(f"🚀 Web 服务启动中...")
    print(f"📱 请在浏览器中访问: http://127.0.0.1:{port}")
    print(f"   或者: http://localhost:{port}")
    print(f"   按 Ctrl+C 停止服务\n")
    
    # 禁用重载器，避免端口冲突问题
    # 明确绑定到 127.0.0.1，避免 IPv6 或其他地址问题
    try:
        app.run(debug=False, host='127.0.0.1', port=port, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print(f"   请检查端口 {port} 是否被占用")
        sys.exit(1)
