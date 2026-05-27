#!/usr/bin/env python3
"""Archiver - Move files from staging areas to final musics directory"""
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class Archiver:
    """Archive generated files to final destination"""
    
    def __init__(self, base_dir: str = "./output"):
        self.base_dir = Path(base_dir).resolve()  # 转换为绝对路径
        self.musics_dir = self.base_dir / "musics"
        self.suno_dir = self.base_dir / "suno_output"
        self.lyrics_dir = self.base_dir / "pure_lyrics"
        self.covers_dir = self.base_dir / "covers"
        logger.info(f"📁 归档器初始化，基础目录: {self.base_dir}")
        
    def archive(self, generation_report: List[Dict]) -> Dict[str, Any]:
        """Archive files and generate report"""
        today = datetime.now()
        date_folder = f"{today.month:02d}.{today.day:02d}"
        target_dir = self.musics_dir / date_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("=" * 60)
        logger.info(f"📦 开始归档到: musics/{date_folder}/")
        logger.info("=" * 60)
        
        archived = []
        failed = []
        
        for item in generation_report:
            song = item.get("song", {})
            covers = item.get("covers", {})
            audio_files = song.get("audio_files", {})
            
            clean_title = song.get("clean_title", "")
            version = song.get("version", "")
            singer = song.get("singer", "")
            
            # Archive files for each version
            versions = [
                (f"{clean_title} ({version})-{singer}", "v1"),
                (f"{clean_title}-{singer}", "v2")
            ]
            
            for filename_base, version_key in versions:
                try:
                    # Copy MP3
                    audio_info = audio_files.get(version_key, {})
                    src_mp3_path = audio_info.get("mp3", "")
                    if src_mp3_path and Path(src_mp3_path).exists():
                        dst_mp3 = target_dir / f"{filename_base}.mp3"
                        shutil.copy2(src_mp3_path, dst_mp3)
                        logger.info(f"   📄 {filename_base}.mp3")
                    
                    # Copy lyrics
                    src_txt = self.lyrics_dir / f"{filename_base}.txt"
                    if src_txt.exists():
                        dst_txt = target_dir / f"{filename_base}.txt"
                        shutil.copy2(src_txt, dst_txt)
                        logger.info(f"   📝 {filename_base}.txt")
                    
                    # Copy cover
                    cover_path = covers.get(version_key)
                    if cover_path and Path(cover_path).exists():
                        dst_png = target_dir / f"{filename_base}.png"
                        shutil.copy2(cover_path, dst_png)
                        logger.info(f"   🎨 {filename_base}.png")
                    
                    archived.append(filename_base)
                    
                except Exception as e:
                    logger.error(f"   ❌ 归档失败 {filename_base}: {e}")
                    failed.append(filename_base)
        
        # Generate report
        report = {
            "date": date_folder,
            "target_dir": str(target_dir),
            "total": len(generation_report),
            "archived": len(archived),
            "failed": len(failed),
            "files": archived
        }
        
        # Save report to file
        report_path = target_dir / f"_report_{datetime.now():%H%M%S}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"Music Factory Archive Report\n")
            f.write(f"Date: {date_folder}\n")
            f.write(f"Time: {datetime.now():%H:%M:%S}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"Total Songs: {report['total']}\n")
            f.write(f"Successfully Archived: {report['archived']}\n")
            f.write(f"Failed: {report['failed']}\n\n")
            f.write("Archived Files:\n")
            for fname in archived:
                f.write(f"  - {fname}\n")
        
        logger.info("=" * 60)
        logger.info(f"✅ 归档完成: {report['archived']} 首成功, {report['failed']} 首失败")
        logger.info(f"📁 保存位置: {target_dir}")
        logger.info(f"📋 报告文件: {report_path.name}")
        logger.info("=" * 60)
        
        return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    archiver = Archiver()
    
    test_report = [
        {
            "song": {
                "clean_title": "测试歌曲",
                "version": "伤感版",
                "singer": "测试歌手",
                "audio_files": {}
            },
            "covers": {"v1": "", "v2": ""}
        }
    ]
    archiver.archive(test_report)