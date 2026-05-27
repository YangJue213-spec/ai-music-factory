"""Data fetching stage - Kugou API integration"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from core.pipeline import Stage, StageContext
from core.retry import with_retry
from utils.http import HTTPClient

logger = logging.getLogger(__name__)


KUGOU_BASE = "http://mobilecdn.kugou.com/api/v3"


class FetcherStage(Stage):
    """Fetch songs from Kugou rankings and artist albums"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("fetcher", config)
        self.config = config or {}
        self.http = HTTPClient(base_url=KUGOU_BASE, timeout=30)
        
    async def execute(self, context: StageContext) -> StageContext:
        all_songs = []
        
        logger.info("=" * 60)
        logger.info("📊 开始数据采集阶段")
        logger.info("=" * 60)
        
        # Fetch from rankings
        for source in self.config.get("sources", []):
            if not source.get("enabled", True):
                continue
                
            source_type = source.get("type")
            
            if source_type == "kugou_rank":
                logger.info(f"🎵 开始抓取榜单: {source.get('name', '未知榜单')} (ID: {source['rank_id']})")
                songs = await self._fetch_ranking(
                    source["rank_id"],
                    source.get("page_size", 100)
                )
                all_songs.extend(songs)
                logger.info(f"✅ 榜单抓取完成: {source.get('name')} - 获取 {len(songs)} 首")
                
            elif source_type == "artist_album":
                artists = source.get("artists", [])
                logger.info(f"🎤 开始监控艺人新专辑，共 {len(artists)} 位艺人")
                songs = await self._fetch_artist_albums(artists)
                all_songs.extend(songs)
                logger.info(f"✅ 艺人专辑监控完成 - 获取 {len(songs)} 张新专辑")
                
        logger.info(f"📊 数据采集完成 - 总计: {len(all_songs)} 首")
        context.set("raw_songs", all_songs)
        return context
        
    @with_retry(max_retries=5, base_delay=1.0)
    async def _fetch_ranking(self, rank_id: int, page_size: int = 100) -> List[Dict]:
        """Fetch ranking list"""
        async with self.http:
            resp = await self.http.get(
                f"/rank/song",
                params={
                    "rankid": rank_id,
                    "page": 1,
                    "pagesize": page_size
                },
                headers={
                    "Referer": "http://mobilecdn.kugou.com/"
                }
            )
            
        songs = []
        data = resp.get("data", {}).get("info", [])
        
        for song in data:
            title = song.get("songname", "")
            artist = song.get("singername", "")
            
            # Fix missing artist from filename
            if not artist and "filename" in song and "-" in song["filename"]:
                parts = song["filename"].split("-")
                artist = parts[0].strip()
                if not title:
                    title = "-".join(parts[1:]).strip()
                    
            songs.append({
                "title": title,
                "artist": artist or "未知歌手",
                "original_hash": song.get("hash"),
                "album_id": song.get("album_id"),
                "cover_url": song.get("album_img", "").replace("{size}", "400") if song.get("album_img") else "",
                "source": f"rank_{rank_id}",
                "raw_data": song
            })
            
        return songs
        
    async def _fetch_artist_albums(self, artists: List[str]) -> List[Dict]:
        """Fetch recent albums for monitored artists - matching n8n logic"""
        songs = []
        cutoff_date = datetime.now() - timedelta(days=3)
        cutoff_date = cutoff_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with self.http:
            for artist in artists:
                try:
                    logger.debug(f"Searching albums for: {artist}")
                    
                    # Search for artist albums
                    resp = await self.http.get(
                        "/search/album",
                        params={
                            "keyword": artist,
                            "page": 1,
                            "pagesize": 20,
                            "sorttype": 2
                        }
                    )
                    
                    # Handle data parsing like n8n (data might be string)
                    resp_data = resp
                    if isinstance(resp.get("data"), str):
                        import json
                        resp_data = {"data": json.loads(resp["data"])}
                    
                    # Get albums list (n8n: responseData.data.info)
                    albums = resp_data.get("data", {}).get("info", [])
                    logger.debug(f"Found {len(albums)} albums for {artist}")
                    
                    # Sort by date (newest first) - n8n does this
                    albums.sort(key=lambda x: x.get("publishtime", ""), reverse=True)
                    
                    for album in albums:
                        pub_time = album.get("publishtime", "")
                        if not pub_time:
                            continue
                        
                        # Parse date like n8n: new Date(album.publishtime)
                        try:
                            pub_date = datetime.strptime(pub_time[:10], "%Y-%m-%d")
                            
                            # Check if within 3 days
                            if pub_date >= cutoff_date:
                                logger.info(f"   🆕 新专辑: {album.get('albumname')} ({pub_time})")
                                songs.append({
                                    "title": album.get("albumname", ""),
                                    "artist": album.get("singername", artist),
                                    "album_id": album.get("albumid"),
                                    "cover_url": (album.get("imgurl") or "").replace("{size}", "400"),
                                    "source": "new_album_search",
                                    "publish_date": pub_time
                                })
                        except ValueError as e:
                            logger.debug(f"Date parse error for {pub_time}: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch albums for {artist}: {e}")
                    
        return songs