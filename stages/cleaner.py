"""Data cleaning stage - filters and deduplication"""
import re
import logging
import unicodedata
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set

from core.pipeline import Stage, StageContext
from core.state import StateManager
from core.retry import with_retry
from utils.http import HTTPClient

logger = logging.getLogger(__name__)


class CleanerStage(Stage):
    """Clean and filter fetched songs"""
    
    def __init__(self, config: Optional[Dict] = None, state_manager: Optional[StateManager] = None):
        super().__init__("cleaner", config)
        self.config = config or {}
        self.state = state_manager
        self.http = HTTPClient(timeout=30)
        self._processed_hashes: Set[str] = set()
        
    async def execute(self, context: StageContext) -> StageContext:
        songs = context.get("raw_songs", [])
        filters = self.config.get("filters", {})
        
        logger.info("=" * 60)
        logger.info("🧹 开始数据清洗阶段")
        logger.info("=" * 60)
        
        # Load already processed hashes
        if self.state:
            self._processed_hashes = set(await self.state.get_processed_hashes(days=30))
            logger.info(f"📋 加载历史记录: {len(self._processed_hashes)} 首已处理")
            
        cleaned = []
        dropped_log = []
        
        logger.info("🔍 开始过滤处理...")
        for song in songs:
            result = await self._process_song(song, filters)
            if result:
                cleaned.append(result)
            else:
                dropped_log.append(f"Filtered: {song.get('title', 'Unknown')}")
                
        if dropped_log:
            logger.info(f"🚫 过滤剔除: {len(dropped_log)} 首")
        
        # Check saturation
        if filters.get("saturation_check", {}).get("enabled", True):
            logger.info("🌊 开始饱和度检测...")
            cleaned = await self._check_saturation(cleaned, filters["saturation_check"])
            
        logger.info(f"✅ 数据清洗完成 - 通过: {len(cleaned)} 首, 剔除: {len(dropped_log)} 首")
        context.set("cleaned_songs", cleaned)
        context.set_metadata("total_cleaned", len(cleaned))
        context.set_metadata("dropped", len(dropped_log))
            
        return context
        
    async def _process_song(self, song: Dict, filters: Dict) -> Optional[Dict]:
        """Process single song through filters"""
        title = song.get("title", "")
        artist = song.get("artist", "")
        song_hash = song.get("original_hash", f"{title}-{artist}")
        
        # Skip if already processed
        if song_hash in self._processed_hashes:
            logger.debug(f"🔄 跳过已处理: {title}")
            return None
            
        # Check blacklist artists
        blacklist = [a.lower() for a in filters.get("blacklist_artists", [])]
        if any(star in artist.lower() for star in blacklist):
            logger.debug(f"🚫 黑名单过滤: {artist} - {title}")
            return None
            
        # Check non-song keywords
        non_song = filters.get("non_song_keywords", [])
        if any(kw in title or kw in artist for kw in non_song):
            logger.debug(f"📚 非歌曲过滤: {title}")
            return None
            
        # Check for unwanted English (except in whitelist)
        if self._has_unwanted_english(title, filters.get("safe_english_tags", [])):
            logger.debug(f"🔤 英文过滤: {title}")
            return None
            
        if self._has_unwanted_english(artist, filters.get("safe_english_tags", [])):
            logger.debug(f"🔤 英文歌手过滤: {artist}")
            return None
            
        # Check for Chinese characters after stripping brackets
        if not self._has_chinese_after_strip(title):
            logger.debug(f"🇨🇳 无中文过滤: {title}")
            return None
            
        # Split titles with brackets
        main_title, subtitles = self._extract_subtitles(title)
        
        # Return main song
        result = {
            **song,
            "title": main_title,
            "subtitles": subtitles,
            "song_hash": song_hash,
            "is_blue_ocean": True  # Will be updated after saturation check
        }
        
        return result
        
    def _has_unwanted_english(self, text: str, whitelist: List[str]) -> bool:
        """Check if text contains English not in whitelist"""
        if not text:
            return False
            
        # Remove whitelisted terms
        clean = text.upper()
        for tag in whitelist:
            clean = clean.replace(tag.upper(), "")
            
        # Check for remaining A-Z
        return bool(re.search(r'[A-Z]', clean))
        
    def _has_chinese_after_strip(self, text: str) -> bool:
        """Check if text has Chinese after removing brackets"""
        if not text:
            return False
            
        stripped = re.sub(r'[\(\)（）\[\]【】]', '', text)
        return bool(re.search(r'[\u4e00-\u9fa5]', stripped))
        
    def _extract_subtitles(self, title: str) -> tuple:
        """Extract main title and subtitles from bracketed text"""
        subtitles = []
        main = title
        
        # Find all bracketed content
        pattern = r'[\(\)（）\[\]【】]'
        parts = re.split(pattern, title)
        
        if len(parts) >= 2:
            main = parts[0].strip()
            for part in parts[1:]:
                part = part.strip()
                # Only keep if not a version indicator
                if part and "版" not in part:
                    subtitles.append(part)
                    
        return main, subtitles
        
    @with_retry(max_retries=5, base_delay=5.0)
    async def _check_saturation(self, songs: List[Dict], config: Dict) -> List[Dict]:
        """Check market saturation for each song"""
        max_versions = config.get("max_versions", 50)
        old_days = config.get("old_song_days", 30)
        cutoff = datetime.now() - timedelta(days=old_days)
        
        results = []
        
        async with self.http:
            for song in songs:
                try:
                    # Search for versions
                    resp = await self.http.get(
                        "http://mobilecdn.kugou.com/api/v3/search/song",
                        params={
                            "format": "json",
                            "keyword": song["title"],
                            "page": 1,
                            "pagesize": 100
                        }
                    )
                    
                    info = resp.get("data", {}).get("info", [])
                    total = resp.get("data", {}).get("total", len(info))
                    
                    # Check for old songs
                    is_old = False
                    for s in info[:10]:  # Check first 10
                        pub_time = s.get("addtime") or s.get("publish_date")
                        if pub_time:
                            try:
                                if isinstance(pub_time, (int, float)):
                                    pub_date = datetime.fromtimestamp(pub_time if pub_time > 1e10 else pub_time / 1000)
                                else:
                                    pub_date = datetime.strptime(str(pub_time)[:10], "%Y-%m-%d")
                                if pub_date < cutoff:
                                    is_old = True
                                    break
                            except:
                                pass
                                
                    # Determine if blue ocean
                    if is_old:
                        song["is_blue_ocean"] = False
                        song["pass_reason"] = f"红海 (早期歌曲)"
                    elif total > max_versions:
                        song["is_blue_ocean"] = False
                        song["pass_reason"] = f"红海 (版本过载: {total})"
                    else:
                        song["is_blue_ocean"] = True
                        song["pass_reason"] = f"蓝海 (版本数 {total})"
                        
                    song["market_saturation"] = total
                    results.append(song)
                    
                except Exception as e:
                    logger.warning(f"Saturation check failed for {song['title']}: {e}")
                    song["is_blue_ocean"] = True  # Default to allow on error
                    song["pass_reason"] = "蓝海 (检测失败，默认通过)"
                    results.append(song)
                    
        # Filter to only blue ocean songs
        blue_ocean = [s for s in results if s.get("is_blue_ocean", True)]
        red_ocean = [s for s in results if not s.get("is_blue_ocean", True)]
        
        logger.info(f"🌊 饱和度检测完成:")
        logger.info(f"   ✅ 蓝海歌曲: {len(blue_ocean)} 首")
        logger.info(f"   ❌ 红海歌曲: {len(red_ocean)} 首 (版本过多或老歌)")
        
        return blue_ocean