#!/usr/bin/env python3
"""测试 API 是否能正确读取 YAML 文件"""
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))

def test_api():
    print("="*60)
    print("🔍 API 测试 - 检查 YAML 读取")
    print("="*60)
    
    # 测试 1: singers.yaml
    print("\n1️⃣  测试 singers.yaml")
    singers_path = Path("config/singers.yaml")
    if singers_path.exists():
        try:
            with open(singers_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"   ✅ 文件存在")
            print(f"   📊 男歌手: {len(data.get('male', []))} 位")
            print(f"   📊 女歌手: {len(data.get('female', []))} 位")
            if data.get('male'):
                print(f"   🎤 示例: {data['male'][0]}")
        except Exception as e:
            print(f"   ❌ 读取失败: {e}")
    else:
        print(f"   ❌ 文件不存在: {singers_path.absolute()}")
    
    # 测试 2: sources.yaml
    print("\n2️⃣  测试 sources.yaml")
    sources_path = Path("config/sources.yaml")
    if sources_path.exists():
        try:
            with open(sources_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"   ✅ 文件存在")
            print(f"   📊 监控艺人: {len(data.get('monitored_artists', []))} 位")
            print(f"   📊 榜单: {len(data.get('chart_sources', []))} 个")
            if data.get('monitored_artists'):
                print(f"   👤 示例: {data['monitored_artists'][0]['name']}")
        except Exception as e:
            print(f"   ❌ 读取失败: {e}")
    else:
        print(f"   ❌ 文件不存在: {sources_path.absolute()}")
    
    # 测试 3: apis.yaml
    print("\n3️⃣  测试 apis.yaml")
    apis_path = Path("config/apis.yaml")
    if apis_path.exists():
        try:
            with open(apis_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"   ✅ 文件存在")
            apis = data.get("apis", {})
            for provider in ["deepseek", "openai", "suno", "siliconflow"]:
                key = apis.get(provider, {}).get("api_key", "")
                status = "✅" if key and "YOUR_" not in key else "⚪"
                print(f"   {status} {provider}: {'已配置' if key and 'YOUR_' not in key else '未配置'}")
        except Exception as e:
            print(f"   ❌ 读取失败: {e}")
    else:
        print(f"   ❌ 文件不存在: {apis_path.absolute()}")
    
    # 测试 4: 模拟 API 调用
    print("\n4️⃣  模拟 API 响应")
    try:
        from web.api import app
        with app.test_client() as client:
            # 测试 singers API
            resp = client.get('/api/singers')
            singers_data = resp.get_json()
            if singers_data.get('success'):
                print(f"   ✅ /api/singers 正常")
                print(f"   📊 返回男歌手: {len(singers_data.get('singers', {}).get('male', []))}")
            else:
                print(f"   ❌ /api/singers 失败: {singers_data}")
            
            # 测试 sources API
            resp = client.get('/api/sources')
            sources_data = resp.get_json()
            if sources_data.get('success'):
                print(f"   ✅ /api/sources 正常")
                print(f"   📊 返回艺人: {len(sources_data.get('sources', {}).get('monitored_artists', []))}")
            else:
                print(f"   ❌ /api/sources 失败: {sources_data}")
                
    except Exception as e:
        print(f"   ❌ API 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    test_api()