"""Suno API Client Stage - Music generation and polling"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from core.pipeline import Stage, StageContext
from core.state import StateManager
from core.retry import with_retry
from utils.http import HTTPClient

logger = logging.getLogger(__name__)


class SunoClientStage(Stage):
    """Generate music using Suno API"""
    
    def __init__(self, config: Optional[Dict] = None, state_manager: Optional[StateManager] = None):
        super().__init__("suno_client", config)
        self.config = config or {}
        self.state = state_manager
        self.http = HTTPClient(
            base_url=config.get("api", {}).get("base_url", "https://api.acedata.cloud/suno"),
            timeout=config.get("api", {}).get("timeout", 300)
        )
        self.api_key = config.get("api_key", "")
        
    async def execute(self, context: StageContext) -> StageContext:
        songs = context.get("ai_processed_songs", [])
        
        logger.info("=" * 60)
        logger.info("🎼 开始Suno音乐生成阶段")
        logger.info("=" * 60)
        logger.info(f"📝 待生成歌曲: {len(songs)} 首")
        logger.info(f"⚙️ 并发限制: {self.config.get('concurrent_limit', 2)}")
        
        generated = []
        
        # Process with concurrency limit
        semaphore = asyncio.Semaphore(self.config.get("concurrent_limit", 2))
        
        async def process_one(song: Dict, index: int) -> Optional[Dict]:
            async with semaphore:
                logger.info(f"🎵 [{index}/{len(songs)}] 开始生成: {song.get('final_title', 'Unknown')}")
                try:
                    result = await self._generate_song(song)
                    if result:
                        logger.info(f"   ✅ 生成成功: {song.get('final_title')}")
                    return result
                except Exception as e:
                    logger.error(f"   ❌ 生成失败: {song.get('final_title')}: {e}")
                    return None
                    
        tasks = [process_one(s, i+1) for i, s in enumerate(songs)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for song, result in zip(songs, results):
            if isinstance(result, Exception):
                continue
            if result:
                generated.append(result)
        
        logger.info(f"✅ Suno生成完成 - 成功: {len(generated)}/{len(songs)} 首")
        context.set("generated_songs", generated)
        return context
        
    async def _generate_song(self, song: Dict) -> Optional[Dict]:
        """Generate single song through Suno API"""
        # Step 1: Submit generation request
        task_id = await self._submit_generation(song)
        if not task_id:
            return None
            
        # Step 2: Poll for completion
        result = await self._poll_task(task_id)
        if not result:
            return None
            
        # Step 3: Download audio files
        downloads = await self._download_audios(result, song)
        
        return {
            **song,
            "task_id": task_id,
            "audio_files": downloads,
            "generation_result": result
        }
        
    @with_retry(max_retries=5, base_delay=5.0)
    async def _submit_generation(self, song: Dict) -> Optional[str]:
        """Submit generation request to Suno"""
        async with self.http:
            resp = await self.http.post(
                "/audios",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "action": "generate",
                    "custom": True,
                    "lyric": song["lyrics"],
                    "style": song["tags"],
                    "title": song["final_title"],
                    "model": self.config.get("generation", {}).get("model", "chirp-v5"),
                    "instrumental": False,
                    "variation_category": "normal"
                }
            )
            
        # Extract task ID
        task_id = resp.get("id") or resp.get("task_id")
        if task_id and self.state:
            await self.state.create_suno_task(task_id, song.get("song_hash", ""))
            
        logger.info(f"Submitted generation for '{song['final_title']}', task_id: {task_id}")
        return task_id
        
    async def _poll_task(self, task_id: str) -> Optional[Dict]:
        """Poll task until completion or timeout"""
        poll_interval = self.config.get("generation", {}).get("poll_interval", 10)
        max_wait = self.config.get("generation", {}).get("wait_timeout", 600)
        
        start_time = asyncio.get_event_loop().time()
        last_state = None
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                logger.warning(f"⏱️ 任务 {task_id} 轮询超时")
                return None
                
            try:
                async with self.http:
                    resp = await self.http.post(
                        "/tasks",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"action": "retrieve", "id": task_id}
                    )
                    
                data = resp.get("data", []) or resp.get("response", {}).get("data", [])
                if not data:
                    await asyncio.sleep(poll_interval)
                    continue
                    
                state = data[0].get("state", "unknown")
                
                if self.state:
                    await self.state.update_suno_task(task_id, state)
                
                # Log state changes
                if state != last_state:
                    logger.info(f"   ⏳ 任务状态: {state}")
                    last_state = state
                    
                if state == "succeeded":
                    logger.info(f"   ✅ 任务完成: {task_id}")
                    return data[0]
                elif state == "failed":
                    logger.error(f"   ❌ 任务失败: {task_id}")
                    return None
                    
                await asyncio.sleep(poll_interval)
                    
            except Exception as e:
                logger.warning(f"轮询错误 {task_id}: {e}")
                await asyncio.sleep(poll_interval)
                
    async def _download_audios(self, result: Dict, song: Dict) -> Dict[str, str]:
        """Download generated audio files - V1 and V2 with correct naming"""
        # Extract audio URLs from result
        audio_urls = []
        
        if "data" in result and isinstance(result["data"], list):
            for item in result["data"]:
                if isinstance(item, dict) and "audio_url" in item:
                    audio_urls.append(item["audio_url"])
        elif "audio_url" in result:
            audio_urls.append(result["audio_url"])
        
        # Need at least 2 URLs for V1 and V2
        if len(audio_urls) < 2:
            logger.warning(f"   ⚠️ 只找到 {len(audio_urls)} 个音频URL，需要2个")
            if len(audio_urls) == 1:
                audio_urls.append(audio_urls[0])
        
        logger.info(f"   🎵 发现 {len(audio_urls)} 个音频版本")
        
        downloads = {}
        
        # Create directories - 使用脚本所在目录作为项目根目录
        project_root = Path(__file__).parent.parent.resolve()
        suno_dir = project_root / "output" / "suno_output"
        lyrics_dir = project_root / "output" / "pure_lyrics"
        suno_dir.mkdir(parents=True, exist_ok=True)
        lyrics_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   📁 保存目录: {suno_dir}")
        
        # Get base components
        clean_title = song["clean_title"]
        version = song["version"]
        singer = song["singer"]
        
        # V1: 原来的歌名 (伤感版)-歌手
        v1_name = f"{clean_title} ({version})-{singer}"
        # V2: 原来的歌名-歌手
        v2_name = f"{clean_title}-{singer}"
        
        versions = [
            ("v1", v1_name, audio_urls[0]),
            ("v2", v2_name, audio_urls[1] if len(audio_urls) > 1 else audio_urls[0])
        ]
        
        for ver_key, filename_base, audio_url in versions:
            try:
                mp3_filename = f"{filename_base}.mp3"
                mp3_filepath = suno_dir / mp3_filename
                
                # Download audio
                logger.info(f"   ⬇️  下载{ver_key.upper()}音频...")
                async with self.http:
                    await self.http.download(audio_url, str(mp3_filepath))
                    
                downloads[ver_key] = {
                    "mp3": str(mp3_filepath),
                    "filename_base": filename_base
                }
                logger.info(f"   💾 {ver_key.upper()}音频: {mp3_filename}")
                
                # Save lyrics file
                lyrics_filename = f"{filename_base}.txt"
                lyrics_path = lyrics_dir / lyrics_filename
                lyrics_path.write_text(song["lyrics"], encoding="utf-8")
                logger.info(f"   📝 {ver_key.upper()}歌词: {lyrics_filename}")
                
            except Exception as e:
                logger.error(f"   ❌ {ver_key.upper()}下载失败: {e}")
                
        return downloads