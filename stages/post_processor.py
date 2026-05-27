"""Post-processing stage - Audio fingerprint removal and loudness normalization"""
import asyncio
import logging
import subprocess
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.pipeline import Stage, StageContext
from core.retry import with_retry

logger = logging.getLogger(__name__)


class PostProcessorStage(Stage):
    """Audio post-processing: AI fingerprint removal + FFmpeg normalization"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("post_processor", config)
        self.config = config or {}
        self.ffmpeg_path = self._find_ffmpeg()
        self.ai_remover_path = self._find_ai_remover()
        
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable"""
        # First, check system PATH
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            logger.info(f"   ✅ 使用系统 FFmpeg: {ffmpeg}")
            return ffmpeg
            
        # Check common locations based on OS
        common_paths = []
        
        # macOS (Homebrew - Apple Silicon)
        if Path("/opt/homebrew/bin/ffmpeg").exists():
            common_paths.append("/opt/homebrew/bin/ffmpeg")
        # macOS (Homebrew - Intel)
        if Path("/usr/local/bin/ffmpeg").exists():
            common_paths.append("/usr/local/bin/ffmpeg")
            
        # Linux common paths
        common_paths.extend([
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
        ])
        
        # Windows common paths
        common_paths.extend([
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ])
        
        # Check project local bin
        project_root = Path(__file__).parent.parent
        local_ffmpeg = project_root / "bin" / "ffmpeg"
        if local_ffmpeg.exists():
            common_paths.append(str(local_ffmpeg))
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"   ✅ 使用 FFmpeg: {path}")
                return path
                
        logger.warning("   ⚠️ FFmpeg not found! Audio processing will be skipped.")
        logger.warning("      请安装 FFmpeg: brew install ffmpeg (macOS) 或访问 ffmpeg.org (Windows)")
        return "ffmpeg"
        
    def _find_ai_remover(self) -> Optional[Path]:
        """Find AI fingerprint remover script"""
        # Check project third_party directory (自带工具)
        project_root = Path(__file__).parent.parent
        ai_path = project_root / "third_party" / "ai-audio-fingerprint-remover" / "ai_audio_fingerprint_remover.py"
        
        if ai_path.exists():
            logger.info("   ✅ 使用项目自带 AI 指纹移除工具")
            return ai_path
            
        # Fallback: Check parent project (主项目)
        parent_root = project_root.parent
        parent_ai_path = parent_root / "third_party" / "ai-audio-fingerprint-remover" / "ai_audio_fingerprint_remover.py"
        
        if parent_ai_path.exists():
            logger.info("   ✅ 使用主项目 AI 指纹移除工具")
            return parent_ai_path
            
        logger.warning("   ⚠️ AI fingerprint remover not found")
        return None
        
    async def execute(self, context: StageContext) -> StageContext:
        songs = context.get("generated_songs", [])
        
        logger.info("=" * 60)
        logger.info("🔧 开始后处理阶段")
        logger.info("=" * 60)
        logger.info(f"📝 待处理音频: {len(songs)} 首")
        
        processed = []
        
        for i, song in enumerate(songs, 1):
            logger.info(f"🎵 [{i}/{len(songs)}] 处理: {song.get('final_title', 'Unknown')}")
            try:
                result = await self._process_song(song)
                if result:
                    processed.append(result)
                    logger.info(f"   ✅ 后处理完成")
            except Exception as e:
                logger.error(f"   ❌ 后处理失败: {e}")
                processed.append(song)
                
        logger.info(f"✅ 后处理完成 - 成功: {len(processed)}/{len(songs)} 首")
        context.set("post_processed_songs", processed)
        return context
        
    async def _process_song(self, song: Dict) -> Optional[Dict]:
        """Process audio files for a song with dual protection"""
        audio_files = song.get("audio_files", [])
        if not audio_files:
            return song
            
        processed_files = []
        
        for audio_path in audio_files:
            try:
                current_path = audio_path
                
                # Step 1: AI fingerprint removal (双重保险第一层)
                if self.config.get("fingerprint_removal", True) and self.ai_remover_path:
                    current_path = await self._remove_fingerprint_ai(current_path)
                    
                # Step 2: FFmpeg processing (双重保险第二层 + 响度)
                if self.config.get("loudness_normalization", True):
                    current_path = await self._process_with_ffmpeg(current_path)
                    
                processed_files.append(current_path)
                
            except Exception as e:
                logger.error(f"Failed to process {audio_path}: {e}")
                processed_files.append(audio_path)  # Keep original on failure
                
        song["processed_files"] = processed_files
        return song
        
    @with_retry(max_retries=3, base_delay=2.0)
    async def _remove_fingerprint_ai(self, audio_path: str) -> str:
        """Remove AI audio fingerprint using GitHub AI tool (第一层)"""
        if not self.ai_remover_path:
            logger.warning("AI remover not available, skipping AI fingerprint removal")
            return audio_path
            
        output_path = audio_path.replace(".mp3", "_ai_cleaned.mp3")
        
        cmd = [
            sys.executable,  # python3
            str(self.ai_remover_path),
            audio_path,
            output_path,
            "--level", "aggressive"
        ]
        
        logger.info(f"Running AI fingerprint remover: {self.ai_remover_path.name}")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"AI remover failed: {error_msg[:200]}")
            # Return original if AI remover fails
            return audio_path
        
        # Verify output exists
        if not Path(output_path).exists():
            logger.error("AI remover did not create output file")
            return audio_path
            
        # Replace original with AI cleaned version
        Path(audio_path).unlink()
        Path(output_path).rename(audio_path)
        
        logger.info(f"AI fingerprint removal complete: {audio_path}")
        return audio_path
        
    async def _process_with_ffmpeg(self, audio_path: str) -> str:
        """Process with FFmpeg: fingerprint破坏 + 响度标准化 (第二层)"""
        # First: subtle modifications to break fingerprints
        temp_path = audio_path.replace(".mp3", "_ff_temp.mp3")
        
        cmd1 = [
            self.ffmpeg_path, "-y", "-i", audio_path,
            "-af", "asetrate=44100*0.99,atempo=1.01",  # Pitch -1%, tempo +1%
            "-c:a", "libmp3lame", "-b:a", "320k",
            temp_path
        ]
        
        await self._run_ffmpeg(cmd1)
        Path(audio_path).unlink()
        Path(temp_path).rename(audio_path)
        
        # Second: loudness normalization
        final_path = audio_path.replace(".mp3", "_final.mp3")
        
        target_loudness = self.config.get("target_loudness", -5)
        true_peak = self.config.get("true_peak", -0.1)
        lra = self.config.get("lra", 4)
        
        loudnorm_filter = (
            f"loudnorm=I={target_loudness}:"
            f"TP={true_peak}:"
            f"LRA={lra}"
        )
        
        cmd2 = [
            self.ffmpeg_path, "-y", "-i", audio_path,
            "-af", loudnorm_filter,
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            "-ar", "44100",
            final_path
        ]
        
        await self._run_ffmpeg(cmd2)
        Path(audio_path).unlink()
        Path(final_path).rename(audio_path)
        
        logger.info(f"FFmpeg processing complete: {audio_path}")
        return audio_path
        
    async def _run_ffmpeg(self, cmd: List[str]):
        """Run FFmpeg command"""
        logger.debug(f"Running: {' '.join(cmd)}")
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"FFmpeg failed: {error_msg[:200]}")