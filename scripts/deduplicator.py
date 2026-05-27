#!/usr/bin/env python3
"""Smart Deduplicator - Intelligent fingerprint-based duplicate detection"""
import re
import unicodedata
import logging
from pathlib import Path
from typing import Set, Dict, List, Optional

logger = logging.getLogger(__name__)


class SmartDeduplicator:
    """Intelligent duplicate detection using multiple fingerprints"""
    
    def __init__(self, search_dir: str = "./output/pure_lyrics"):
        self.search_dir = Path(search_dir)
        self.local_hashes: Set[str] = set()
        
    def clean_chars(self, text: str) -> str:
        """Clean text - keep only Chinese characters, letters and numbers"""
        if not text:
            return ""
        text = unicodedata.normalize('NFKC', text).lower()
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        return text
        
    def generate_fingerprints(self, filename: str) -> Set[str]:
        """Generate all possible fingerprints from a filename"""
        fingerprints = set()
        
        if not filename:
            return fingerprints
            
        text = unicodedata.normalize('NFKC', filename).lower()
        
        if '.' in text:
            text = text.rsplit('.', 1)[0]
            
        if '-' in text:
            text = text.rsplit('-', 1)[0]
        
        pattern = re.compile(r'[\(\[\{<（【《](.*?)[\)\]\}>）】》]')
        matches = pattern.findall(text)
        
        for content in matches:
            if "版" not in content:
                sub_key = self.clean_chars(content)
                if sub_key:
                    fingerprints.add(sub_key)
        
        main_title_raw = pattern.sub('', text)
        main_key = self.clean_chars(main_title_raw)
        
        if main_key:
            fingerprints.add(main_key)
            
        return fingerprints
        
    def scan_local_files(self) -> Set[str]:
        """Scan local directory and build fingerprint library"""
        self.local_hashes = set()
        files_scanned = 0
        
        logger.info(f"🔍 扫描本地文件: {self.search_dir}")
        
        if not self.search_dir.exists():
            logger.warning(f"   ⚠️ 目录不存在: {self.search_dir}")
            return self.local_hashes
            
        for f in self.search_dir.iterdir():
            if f.is_file() and f.suffix.lower() in ('.txt', '.mp3', '.png'):
                files_scanned += 1
                keys = self.generate_fingerprints(f.name)
                self.local_hashes.update(keys)
                    
        logger.info(f"   ✅ 扫描完成: {files_scanned} 个文件, {len(self.local_hashes)} 个唯一指纹")
        return self.local_hashes
        
    def check_duplicates(self, candidates: List[Dict]) -> tuple:
        """Check for duplicates among candidate songs"""
        if not self.local_hashes:
            self.scan_local_files()
            
        unique_songs = []
        duplicates = []
        
        logger.info(f"🔍 开始查重: {len(candidates)} 首候选歌曲")
        
        for song in candidates:
            title = song.get('title') or song.get('generated_title') or ''
            title = str(title).strip()
            
            input_keys = self.generate_fingerprints(title)
            
            if not input_keys:
                unique_songs.append(song)
                continue
                
            is_duplicate = False
            hit_key = ""
            
            for key in input_keys:
                if key in self.local_hashes:
                    is_duplicate = True
                    hit_key = key
                    break
                    
            if is_duplicate:
                duplicates.append({
                    'title': title,
                    'hit_key': hit_key,
                    'song': song
                })
                logger.info(f"   🚫 重复: [{title}] -> 命中 [{hit_key}]")
            else:
                unique_songs.append(song)
                self.local_hashes.update(input_keys)
                
        logger.info(f"   ✅ 查重完成: {len(unique_songs)} 首通过, {len(duplicates)} 首重复")
        return unique_songs, duplicates
        
    def filter_songs(self, songs: List[Dict]) -> List[Dict]:
        """Filter songs, return only unique ones"""
        unique, duplicates = self.check_duplicates(songs)
        
        if duplicates:
            logger.info("⬇️  被拦截的歌曲:")
            for dup in duplicates:
                logger.info(f"   - {dup['title']}")
                
        return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    dedup = SmartDeduplicator("./output/pure_lyrics")
    
    test_songs = [
        {"title": "男人海洋 (深情版)-歌手1", "artist": "歌手1"},
        {"title": "男人海洋 (最痴情的男人像海洋)-歌手2", "artist": "歌手2"},
        {"title": "全新歌曲-歌手3", "artist": "歌手3"},
    ]
    
    unique = dedup.filter_songs(test_songs)
    
    print(f"\n通过: {len(unique)} 首")
    for s in unique:
        print(f"  - {s.get('title')}")