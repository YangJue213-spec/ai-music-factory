"""AI Processing Stage - Style analysis, lyrics generation, singer matching"""
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

from core.pipeline import Stage, StageContext
from core.retry import with_retry
from utils.llm import LLMClient

logger = logging.getLogger(__name__)


def load_singer_config() -> Dict:
    """Load singer configuration from singers.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "singers.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Failed to load singers.yaml: {e}")
        return {
            "female_singers": [],
            "male_singers": [],
            "version_suffixes": []
        }


# Load singer config on module import
_SINGER_CONFIG = load_singer_config()
FEMALE_SINGERS = _SINGER_CONFIG.get("female_singers", [])
MALE_SINGERS = _SINGER_CONFIG.get("male_singers", [])
VERSION_SUFFIXES = _SINGER_CONFIG.get("version_suffixes", ["伤感版", "治愈版", "深情版"])


class AIProcessorStage(Stage):
    """Process songs with AI for style, lyrics, and singer matching"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("ai_processor", config)
        self.config = config or {}
        self.clients = {}
        self.api_configs = {}
        self.title_mode = config.get("title_mode", "original") if config else "original"  # "original" 或 "chorus"
        
    def set_api_configs(self, api_configs: Dict):
        """Set API configurations from apis.yaml"""
        self.api_configs = api_configs
        
    def _get_client(self, provider: str) -> LLMClient:
        """Get or create LLM client with API config"""
        if provider not in self.clients:
            api_cfg = self.api_configs.get(provider, {})
            api_key = api_cfg.get("api_key", "")
            base_url = api_cfg.get("base_url")
            
            if not api_key:
                raise ValueError(f"API key not configured for {provider} in config/apis.yaml")
            
            self.clients[provider] = LLMClient(
                provider=provider,
                api_key=api_key,
                base_url=base_url
            )
            self.clients[provider]._model = api_cfg.get("model")
            
        return self.clients[provider]
        
    async def execute(self, context: StageContext) -> StageContext:
        songs = context.get("cleaned_songs", [])
        
        logger.info("=" * 60)
        logger.info("🤖 开始AI处理阶段")
        logger.info("=" * 60)
        logger.info(f"📝 待处理歌曲: {len(songs)} 首")
        
        processed = []
        
        for i, song in enumerate(songs, 1):
            logger.info(f"🎵 [{i}/{len(songs)}] 处理: {song.get('title', 'Unknown')}")
            try:
                result = await self._process_song(song)
                if result:
                    processed.append(result)
                    logger.info(f"   ✅ 完成: {result.get('final_title', 'Unknown')}")
            except Exception as e:
                logger.error(f"   ❌ 处理失败: {e}")
                continue
                
        logger.info(f"✅ AI处理完成 - 成功: {len(processed)}/{len(songs)} 首")
        context.set("ai_processed_songs", processed)
        return context
        
    async def _process_song(self, song: Dict) -> Optional[Dict]:
        """Process single song through AI pipeline"""
        style = await self._analyze_style(song)
        lyrics = await self._generate_lyrics(song, style)
        final = await self._match_singer(song, style, lyrics)
        return final
        
    @with_retry(max_retries=5, base_delay=5.0)
    async def _analyze_style(self, song: Dict) -> Dict:
        """Analyze song style with DeepSeek"""
        client = self._get_client("deepseek")
        
        prompt = f"""你是一位崇尚"极简主义"的 Suno 风格顾问。请为这首歌生成一套最简单的 Tags。

=== 目标歌曲 ===
歌名：{song['title']}
歌手：{song['artist']}

=== 极简提取指令 ===
请只提取以下两类标签，总数不要超过 4 个单词：

1. **基础流派**：固定使用 `Mandopop` (华语流行) 或 `Chinese Pop`。
2. **核心情绪**：根据原曲感觉，从以下词中选 1-2 个：
   - `Sad` (悲伤), `Emotional` (深情), `Nostalgic` (怀旧), `Heartbreaking` (心碎), `Upbeat` (欢快).

=== 输出格式 (Strict JSON) ===
{{
  "original_song_name": "{song['title']}",
  "analysis_report": "简短分析...",
  "suno_profile": {{
    "style_tags": "生成的极简 Tags (例如: Mandopop, Sad)",
    "lyrics_theme_guide": "歌词基调：苦情、痴心、红尘、沧桑。"
  }}
}}"""

        model = getattr(client, '_model', None) or "deepseek-chat"
        
        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.7
        )
        
        result = client.parse_json_response(response)
        if not result:
            result = {
                "original_song_name": song["title"],
                "analysis_report": "默认分析",
                "suno_profile": {
                    "style_tags": "Mandopop, Sad",
                    "lyrics_theme_guide": "苦情、痴心"
                }
            }
            
        return result
        
    @with_retry(max_retries=5, base_delay=5.0)
    async def _generate_lyrics(self, song: Dict, style: Dict) -> Dict:
        """Generate lyrics with OpenAI GPT"""
        client = self._get_client("openai")
        
        profile = style.get("suno_profile", {})
        
        prompt = f"""你是一位擅长"同题重构"的顶级作词人。
请根据以下"乐评人"提供的风格报告，写一首**歌名相同、意境相近**的新歌。

=== 原始歌名 ===
{song['title']}

=== 风格标签 ===
{profile.get('style_tags', 'Mandopop')}

=== 歌词要求 ===
- **标题锁定**：必须严格使用原始歌名，去掉括号内的内容。
- **Tags 继承**：{profile.get('style_tags', 'Mandopop')}
- **内容风格**：土味、沧桑、下沉市场、大白话。减少对日常生活的内容描述，尽量使用简单直白的情绪输出。
- **注意押韵**：强制要求押韵，韵律和谐，语句通顺。
- **结构**：[Verse1], [Verse2], [Chorus1], [Chorus2], [Guitar Solo], [Verse2], [Chorus1], [Chorus2], [Chorus1], [Chorus2]
- **逻辑**：歌词逻辑要通顺，注意上下句之间的逻辑。

=== 输出格式 (Strict JSON) ===
{{
  "title": "{song['title']}",
  "tags": "{profile.get('style_tags', 'Mandopop')}",
  "prompt": "[Intro]\\n(这里写歌词...)"
}}"""

        model = getattr(client, '_model', None) or "gpt-4"
        
        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.8
        )
        
        result = client.parse_json_response(response)
        if not result:
            result = {
                "title": song["title"],
                "tags": profile.get("style_tags", "Mandopop"),
                "prompt": f"[Verse1]\\n{song['title']}\\n\\n[Chorus1]\\n{song['title']}"
            }
            
        return result
        
    @with_retry(max_retries=5, base_delay=5.0)
    async def _analyze_version(self, lyrics: Dict) -> str:
        """Analyze lyrics to determine version suffix"""
        client = self._get_client("deepseek")
        
        prompt = f"""你是一位专业的音乐情感分析师。
请阅读以下歌词，分析其情感基调，选择最贴切的版本后缀。

=== 歌词内容 ===
{lyrics.get('prompt', '')}

=== 可选版本 ===
- 伤感版：悲伤、失落、痛苦
- 治愈版：温暖、安慰、希望
- 深情版：深情、真挚、感动
- 告别版：离别、结束、放下
- 思念版：想念、回忆、牵挂
- 释怀版：释然、放下、成长

请只输出版本名称（如：伤感版），不要输出任何解释。"""

        model = getattr(client, '_model', None) or "deepseek-chat"
        
        response = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.5
        )
        
        version = response.strip()
        
        for v in VERSION_SUFFIXES:
            if v in version:
                return v
                
        return VERSION_SUFFIXES[0] if VERSION_SUFFIXES else "深情版"
        
    def _extract_chorus_first_line(self, lyrics_text: str) -> str:
        """从歌词中提取副歌(Chorus)的第一句"""
        try:
            lines = lyrics_text.split('\n')
            in_chorus = False
            for line in lines:
                line = line.strip()
                if '[Chorus' in line or '[Chorus]' in line:
                    in_chorus = True
                    continue
                if in_chorus and line and not line.startswith('['):
                    # 找到副歌第一句，清理标点符号
                    import re
                    clean_line = re.sub(r'[，。！？、；：""''（）【】]', '', line)
                    # 限制长度，最多10个字
                    if len(clean_line) > 10:
                        clean_line = clean_line[:10]
                    return clean_line
            # 如果没找到Chorus标签，尝试找重复出现的句子
            return ""
        except:
            return ""
        
    @with_retry(max_retries=5, base_delay=5.0)
    async def _match_singer(self, song: Dict, style: Dict, lyrics: Dict) -> Dict:
        """Match singer and finalize metadata"""
        version = await self._analyze_version(lyrics)
        
        if random.random() < 0.5:
            singer = random.choice(MALE_SINGERS)
            gender_tag = "male vocals"
        else:
            singer = random.choice(FEMALE_SINGERS)
            gender_tag = "female vocals"
            
        original_tags = lyrics.get("tags", "Mandopop")
        final_tags = f"{gender_tag}, {original_tags}"
        
        # 根据 title_mode 决定歌名生成方式
        if self.title_mode == "chorus":
            # 使用副歌第一句作为歌名
            chorus_line = self._extract_chorus_first_line(lyrics.get("prompt", ""))
            if chorus_line:
                clean_title = chorus_line
                logger.info(f"   📝 使用副歌第一句作为歌名: {clean_title}")
            else:
                # 如果提取失败，回退到原始歌名
                clean_title = song["title"].split("(")[0].strip()
                logger.info(f"   📝 副歌提取失败，使用原始歌名: {clean_title}")
        else:
            # 使用原始歌名（默认）
            clean_title = song["title"].split("(")[0].strip()
            logger.info(f"   📝 使用原始歌名: {clean_title}")
        
        final_title = f"{clean_title} ({version})-{singer}"
        
        return {
            "original_title": song["title"],
            "original_artist": song["artist"],
            "final_title": final_title,
            "clean_title": clean_title,
            "singer": singer,
            "gender_tag": gender_tag,
            "version": version,
            "tags": final_tags,
            "style_tags": original_tags,
            "lyrics": lyrics.get("prompt", ""),
            "analysis": style.get("analysis_report", ""),
            "cover_url": song.get("cover_url", ""),
            "song_hash": song.get("song_hash", ""),
            "title_mode": self.title_mode
        }
