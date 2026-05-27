#!/usr/bin/env python3
"""Music Factory - Windows Portable Version
音乐生成工厂 - Windows移植版
"""
import asyncio
import logging
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import yaml
from core.state import StateManager
from core.pipeline import StageContext
from utils.config import load_all_configs

from stages.fetcher import FetcherStage
from stages.cleaner import CleanerStage
from stages.ai_processor import AIProcessorStage
from stages.suno_client import SunoClientStage
from stages.post_processor import PostProcessorStage
from stages.cover_generator import CoverGeneratorStage
from scripts.archiver import Archiver
from scripts.deduplicator import SmartDeduplicator


def build_stages_config(config: dict) -> dict:
    """Build stages configuration from loaded configs"""
    sources_config = config.get("sources", {})
    settings = config.get("settings", {})
    
    # 构建 fetcher 的 sources 列表
    fetcher_sources = []
    
    # 从 sources.yaml 添加榜单源
    chart_sources = sources_config.get("chart_sources", [])
    for source in chart_sources:
        if source.get("enabled", True):
            fetcher_sources.append({
                "name": source.get("name", "unknown"),
                "type": "kugou_rank",
                "rank_id": source.get("rank_id", 6666),
                "page_size": source.get("page_size", 100),
                "enabled": True
            })
    
    # 从 sources.yaml 添加艺人监控源
    monitored_artists = sources_config.get("monitored_artists", [])
    if monitored_artists:
        fetcher_sources.append({
            "name": "artist_albums",
            "type": "artist_album",
            "artists": monitored_artists,
            "enabled": True
        })
    
    # 如果没有配置任何源，使用默认的酷狗榜单
    if not fetcher_sources:
        fetcher_sources = [
            {
                "name": "kugou_surfing",
                "type": "kugou_rank",
                "rank_id": 6666,
                "page_size": 100,
                "enabled": True
            },
            {
                "name": "kugou_new",
                "type": "kugou_rank",
                "rank_id": 31308,
                "page_size": 100,
                "enabled": True
            }
        ]
    
    # 使用 settings.yaml 中的配置或默认值
    stages_config = {
        "fetcher": {
            "enabled": True,
            "sources": fetcher_sources
        },
        "cleaner": {
            "enabled": True,
            "filters": settings.get("filters", {
                "blacklist_artists": [
                    "en", "王翊恩", "张靓颖", "薛之谦", "周深", "张良", "刘宇宁",
                    "邓紫棋", "陈奕迅", "林俊杰", "周杰伦", "华晨宇", "毛不易",
                    "李荣浩", "张杰", "汪苏泷", "许嵩", "那英", "王菲", "孙燕姿",
                    "蔡依林", "五月天", "梁静茹", "刘德华", "张学友", "郭富城",
                    "黎明", "莫文蔚", "杨宗纬", "林志炫", "韩红", "李健",
                    "王力宏", "陶喆", "周笔畅", "李宇春", "张韶涵", "田馥甄",
                    "汪峰", "朴树", "许巍", "伍佰", "单依纯", "黄霄雲",
                    "希林娜依·高", "郁可唯", "张碧晨", "王心凌", "杨丞琳",
                    "队长", "告五人", "时代少年团", "马嘉祺", "宋亚轩",
                    "TFBOYS", "EXO", "Beyond", "G.E.M."
                ],
                "non_song_keywords": [
                    "古诗", "必背", "朗读", "课文", "年级", "上册", "下册",
                    "语文", "有声", "故事", "评书", "相声", "小品", "广播剧",
                    "戏曲", "豫剧", "小学", "初中", "高中", "幼儿", "儿歌",
                    "英语", "听力", "百科", "教程", "讲座", "记忆教室", "宝宝巴士",
                    "配音", "伴读"
                ],
                "saturation_check": {
                    "enabled": True,
                    "max_versions": 50,
                    "old_song_days": 30
                },
                "safe_english_tags": [
                    "DJ", "Remix", "Live", "Mix", "Vs", "Feat", "Ft",
                    "Ver", "Version", "Inst", "Demo"
                ]
            })
        },
        "ai_processor": {
            "enabled": True,
            "title_mode": settings.get("title_mode", "original")
        },
        "suno_client": {
            "enabled": True,
            "api": {
                "base_url": "https://api.acedata.cloud/suno",
                "timeout": 300
            },
            "generation": {
                "model": "chirp-v5",
                "instrumental": False,
                "variation_category": "normal",
                "wait_timeout": 600,
                "poll_interval": 10
            },
            "concurrent_limit": settings.get("concurrent_limit", 2)
        },
        "post_processor": {
            "enabled": True,
            "fingerprint_removal": settings.get("fingerprint_removal", True),
            "loudness_normalization": True,
            "target_loudness": -5,
            "true_peak": -0.1,
            "lra": 4
        },
        "cover_generator": {
            "enabled": True,
            "image_model": "Kwai-Kolors/Kolors",
            "cover_style": settings.get("cover_style", "realistic"),
            "cover_include_figure": settings.get("cover_include_figure", True)
        }
    }
    
    return stages_config


def setup_logging() -> logging.Logger:
    """Configure logging"""
    log_dir = Path("./data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"music_factory_{datetime.now():%Y%m%d_%H%M%S}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def check_api_keys(config: dict) -> bool:
    """Check if API keys are configured"""
    apis = config.get("apis", {})
    missing = []
    
    for provider in ["deepseek", "openai", "suno", "siliconflow"]:
        key = apis.get(provider, {}).get("api_key", "")
        if not key or "YOUR_" in key:
            missing.append(provider)
    
    if missing:
        print("\n" + "=" * 60)
        print("❌ 错误：以下 API 密钥未配置")
        print("=" * 60)
        for provider in missing:
            print(f"   - {provider}")
        print("\n请编辑 config/apis.yaml 文件，填写您的 API 密钥")
        print("=" * 60 + "\n")
        return False
    
    return True


# 获取项目根目录（脚本所在目录）
PROJECT_ROOT = Path(__file__).parent.resolve()


async def run_pipeline(config: dict, max_songs: int = None, progress_callback=None):
    """
    Run the complete music generation pipeline with streaming processing
    采用流式处理：逐首歌完成所有阶段，实时显示每首歌的处理进度
    """
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("🎵 Music Factory Windows版 启动")
    logger.info(f"📁 工作目录: {PROJECT_ROOT}")
    logger.info("=" * 60)
    
    def update_progress(stage, step, total_steps, message="", extra=None):
        """Update progress via callback"""
        if progress_callback:
            progress_callback({
                "stage": stage,
                "step": step,
                "total_steps": total_steps,
                "progress": int((step / total_steps) * 100),
                "message": message,
                **(extra or {})
            })
    
    stages_config = config.get("stages", {})
    settings = config.get("settings", {})
    state = StateManager()
    
    # Step 1: Fetch all songs (batch)
    update_progress("数据采集", 1, 5, "正在采集歌曲数据...")
    logger.info("\n📊 阶段 1/5: 数据采集")
    fetcher = FetcherStage(stages_config.get("fetcher", {}))
    context = StageContext()
    async with fetcher.http:
        context = await fetcher.execute(context)
    all_songs = context.get("raw_songs", [])
    logger.info(f"✅ 采集完成: {len(all_songs)} 首\n")
    update_progress("数据采集", 1, 5, f"采集完成: {len(all_songs)} 首", {"fetched": len(all_songs)})
    
    # Step 2: Clean all songs (batch)
    update_progress("数据清洗", 2, 5, "正在清洗数据...")
    logger.info("🧹 阶段 2/5: 数据清洗")
    cleaner = CleanerStage(stages_config.get("cleaner", {}), state_manager=state)
    context.set("raw_songs", all_songs)
    context = await cleaner.execute(context)
    cleaned_songs = context.get("cleaned_songs", [])
    logger.info(f"✅ 清洗完成: {len(cleaned_songs)} 首通过\n")
    
    # 显示清洗出的每首歌名
    logger.info("📋 清洗通过歌曲列表:")
    for i, song in enumerate(cleaned_songs, 1):
        logger.info(f"   [{i}] {song.get('title', 'Unknown')} - {song.get('artist', 'Unknown')}")
    logger.info("")
    
    update_progress("数据清洗", 2, 5, f"清洗完成: {len(cleaned_songs)} 首", {"cleaned": len(cleaned_songs)})
    
    # Step 3: Deduplicate
    update_progress("智能去重", 3, 5, "正在去重...")
    logger.info("🧠 阶段 3/5: 智能去重")
    output_dir = PROJECT_ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"   输出目录: {output_dir}")
    deduplicator = SmartDeduplicator(str(output_dir / "pure_lyrics"))
    unique_songs = deduplicator.filter_songs(cleaned_songs)
    
    if max_songs is not None and max_songs > 0:
        unique_songs = unique_songs[:max_songs]
        logger.info(f"✅ 去重完成: {len(unique_songs)} 首 (限制生成 {max_songs} 首)\n")
    else:
        logger.info(f"✅ 去重完成: {len(unique_songs)} 首唯一歌曲\n")
    
    update_progress("智能去重", 3, 5, f"去重完成: {len(unique_songs)} 首")
    
    if not unique_songs:
        logger.warning("没有待生成的歌曲，流程结束")
        update_progress("完成", 5, 5, "没有待生成的歌曲")
        return
    
    # Step 4: Stream processing - one song at a time
    logger.info("=" * 60)
    logger.info("🎼 阶段 4/5: 逐首生成 (流式处理)")
    logger.info(f"总计: {len(unique_songs)} 首")
    logger.info("=" * 60)
    
    # Setup stages
    ai_config = stages_config.get("ai_processor", {})
    ai_config["title_mode"] = settings.get("title_mode", "original")
    ai_stage = AIProcessorStage(ai_config)
    ai_stage.set_api_configs(config.get("apis", {}))
    
    suno_config = stages_config.get("suno_client", {}).copy()
    suno_config["api_key"] = config.get("apis", {}).get("suno", {}).get("api_key", "")
    suno_stage = SunoClientStage(suno_config, state_manager=state)
    
    post_stage = PostProcessorStage(stages_config.get("post_processor", {}))
    
    # Process each song individually (streaming)
    generated_count = 0
    processed_songs = []
    generated_covers = []
    
    for i, song in enumerate(unique_songs, 1):
        logger.info("=" * 60)
        logger.info(f"🎵 [{i}/{len(unique_songs)}] 开始处理: {song.get('title', 'Unknown')}")
        logger.info("=" * 60)
        
        try:
            # AI Processing
            logger.info("   🤖 AI风格分析...")
            song_context = StageContext()
            song_context.set("cleaned_songs", [song])
            song_context = await ai_stage.execute(song_context)
            processed = song_context.get("ai_processed_songs", [])
            
            if not processed:
                logger.warning("   ⚠️ AI处理失败，跳过")
                continue
            
            ai_song = processed[0]
            logger.info(f"   ✍️ AI写词完成")
            logger.info(f"   🎤 匹配歌手: {ai_song.get('singer')} ({ai_song.get('version')})")
            logger.info(f"   🏷️ 标签: {ai_song.get('tags')}")
            
            # Suno Generation
            logger.info("   🎼 提交Suno生成...")
            suno_context = StageContext()
            suno_context.set("ai_processed_songs", [ai_song])
            suno_context = await suno_stage.execute(suno_context)
            generated = suno_context.get("generated_songs", [])
            
            if not generated:
                logger.warning("   ⚠️ Suno生成失败，跳过")
                continue
            
            gen_song = generated[0]
            logger.info(f"   💾 下载完成:")
            for f in gen_song.get("audio_files", []):
                logger.info(f"      - {f}")
            
            # Post Processing
            logger.info("   🔧 后处理...")
            post_context = StageContext()
            post_context.set("generated_songs", [gen_song])
            post_context = await post_stage.execute(post_context)
            processed_song = post_context.get("post_processed_songs", [gen_song])[0]
            
            # Generate covers for this song (per-song)
            logger.info("   🎨 生成封面...")
            cover_config = {
                "siliconflow_api_key": config.get("apis", {}).get("siliconflow", {}).get("api_key", ""),
                "deepseek_api_key": config.get("apis", {}).get("deepseek", {}).get("api_key", ""),
                "image_model": "Kwai-Kolors/Kolors",
                "cover_style": settings.get("cover_style", "realistic"),
                "cover_include_figure": settings.get("cover_include_figure", True)
            }
            cover_stage = CoverGeneratorStage(cover_config)
            
            cover_context = StageContext()
            cover_context.set("post_processed_songs", [processed_song])
            cover_context = await cover_stage.execute(cover_context)
            cover_result = cover_context.get("generated_covers", [])
            if cover_result:
                generated_covers.extend(cover_result)
            
            processed_songs.append(processed_song)
            generated_count += 1
            logger.info(f"✅ [{i}/{len(unique_songs)}] 全部完成: {ai_song.get('final_title', 'Unknown')}")
            
            # Update progress - 动态计算进度（第4阶段占20%-100%，根据歌曲进度分配）
            # 阶段1-3各占20%，阶段4占60%，阶段5占20%
            song_progress = i / len(unique_songs)  # 0-1
            stage4_progress = 20 + (song_progress * 60)  # 20%-80%
            
            update_progress("逐首生成", 4, 5, 
                f"已生成 {generated_count}/{len(unique_songs)} 首 - 当前: {ai_song.get('final_title', 'Unknown')}",
                {
                    "current": i, 
                    "total": len(unique_songs), 
                    "generated": generated_count,
                    "progress": int(stage4_progress)
                }
            )
            
        except Exception as e:
            logger.error(f"   ❌ 处理失败: {e}")
            continue
        
        logger.info("")  # Empty line between songs
    
    # Step 5: Archive all files
    logger.info("\n" + "=" * 60)
    logger.info("📦 阶段 5/5: 文件归档")
    logger.info("=" * 60)
    
    archiver = Archiver(str(PROJECT_ROOT / "output"))
    report = archiver.archive(generated_covers)
    
    update_progress("完成", 5, 5, f"全部完成！生成 {generated_count} 首", {
        "generated": generated_count,
        "covers": len(generated_covers),
        "target_dir": report['target_dir']
    })
    
    logger.info("=" * 60)
    logger.info(f"🎉 全部流程完成！")
    logger.info(f"   音频生成: {generated_count}/{len(unique_songs)} 首")
    logger.info(f"   封面生成: {len(generated_covers)}/{len(processed_songs)} 首")
    logger.info(f"   归档位置: {report['target_dir']}")
    logger.info("=" * 60)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Music Factory - 音乐生成工厂')
    parser.add_argument('--count', '-c', type=int, default=None, 
                        help='指定生成歌曲数量（默认：全部）')
    parser.add_argument('--max-songs', '-m', type=int, default=None,
                        help='同 --count，指定生成歌曲数量')
    args = parser.parse_args()
    
    max_songs = args.count or args.max_songs
    
    # Load all configurations using the new unified loader
    config = load_all_configs(str(PROJECT_ROOT / "config"))
    
    # Build stages configuration
    stages_config = build_stages_config(config)
    config["stages"] = stages_config
    
    # Check API keys
    if not check_api_keys(config):
        sys.exit(1)
    
    # Run pipeline
    await run_pipeline(config, max_songs=max_songs)


if __name__ == "__main__":
    asyncio.run(main())
