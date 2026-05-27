"""Cover Generator Stage - AI image generation and text overlay"""
import asyncio
import logging
import random
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
import aiohttp

from core.pipeline import Stage, StageContext
from core.retry import with_retry
from utils.llm import LLMClient

logger = logging.getLogger(__name__)


class CoverGeneratorStage(Stage):
    """Generate album covers using SiliconFlow API + Pillow text overlay"""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__("cover_generator", config)
        self.config = config or {}
        self.api_key = config.get("siliconflow_api_key", "") if config else ""
        self.base_url = "https://api.siliconflow.cn/v1"
        self.model = config.get("image_model", "Kwai-Kolors/Kolors") if config else "Kwai-Kolors/Kolors"
        self.image_size = "1024x1024"
        
    async def execute(self, context: StageContext) -> StageContext:
        """Generate covers for processed songs"""
        songs = context.get("post_processed_songs", [])
        
        logger.info("=" * 60)
        logger.info("🎨 开始封面生成阶段")
        logger.info("=" * 60)
        
        covers = []
        for i, song in enumerate(songs, 1):
            logger.info(f"🎵 [{i}/{len(songs)}] 生成封面: {song.get('final_title', 'Unknown')}")
            try:
                cover_paths = await self._generate_covers_for_song(song)
                if cover_paths:
                    covers.append({
                        "song": song,
                        "covers": cover_paths
                    })
                    logger.info(f"   ✅ 封面生成完成")
            except Exception as e:
                logger.error(f"   ❌ 封面生成失败: {e}")
                continue
                
        context.set("generated_covers", covers)
        logger.info(f"✅ 封面生成完成 - 成功: {len(covers)}/{len(songs)} 首")
        return context
        
    async def _generate_covers_for_song(self, song: Dict) -> Optional[Dict[str, str]]:
        """Generate two cover versions for a song"""
        clean_title = song.get("clean_title") or song.get("title", "")
        version = song.get("version", "")
        singer = song.get("singer", "")
        
        # Generate AI image prompt
        prompt = await self._generate_prompt(clean_title, singer)
        if not prompt:
            logger.warning("   ⚠️ 封面Prompt生成失败，使用默认")
            prompt = f"anime style album cover, {clean_title}, emotional, artistic, masterpiece"
        
        # Download image from SiliconFlow
        image_url = await self._generate_image(prompt)
        if not image_url:
            return None
            
        # Download and process image
        image_data = await self._download_image(image_url)
        if not image_data:
            return None
            
        # Create output directory - 使用脚本所在目录作为项目根目录
        project_root = Path(__file__).parent.parent.resolve()
        covers_dir = project_root / "output" / "covers"
        covers_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"   📁 封面保存目录: {covers_dir}")
        
        # Generate two versions
        cover_paths = {}
        
        # V1: 原来的歌名 (伤感版)-歌手.png
        v1_name = f"{clean_title} ({version})-{singer}"
        v1_path = covers_dir / f"{v1_name}.png"
        self._process_cover(image_data, v1_path, clean_title, version, singer)
        cover_paths["v1"] = str(v1_path)
        logger.info(f"   💾 V1封面: {v1_path.name}")
        
        # V2: 原来的歌名-歌手.png
        v2_name = f"{clean_title}-{singer}"
        v2_path = covers_dir / f"{v2_name}.png"
        self._process_cover(image_data, v2_path, clean_title, "", singer)
        cover_paths["v2"] = str(v2_path)
        logger.info(f"   💾 V2封面: {v2_path.name}")
        
        return cover_paths
        
    @with_retry(max_retries=3, base_delay=2.0)
    async def _generate_prompt(self, title: str, singer: str) -> Optional[str]:
        """Generate image prompt from song title"""
        client = LLMClient(
            provider="deepseek",
            api_key=self.config.get("deepseek_api_key", "")
        )
        
        # 获取封面风格配置
        cover_style = self.config.get("cover_style", "realistic")  # realistic 或 anime
        
        if cover_style == "anime":
            # 日系动漫风格（原风格）
            prompt_text = f"""你是一位顶尖的日系动漫插画导演。请根据歌名发散联想，生成生图Prompt。

=== 输入 ===
歌名：{title}
歌手：{singer}

=== 角色设定 ===
- 男歌手 → 1boy, male focus
- 女歌手 → 1girl, female focus
- 必须成年：(young adult:1.4), (mature:1.2)

=== 画风要求 ===
日系ACG：(anime style:1.5), flat color, masterpiece, best quality

=== 输出格式 ===
只输出英文标签，逗号分隔，不要解释：

masterpiece, best quality, (anime style:1.5), (young adult:1.4), [1boy/1girl], solo, [动作/姿态], [表情情绪], [核心意象1], [核心意象2], [场景环境], [光影氛围], cinematic lighting

现在请根据歌名"{title}"生成Prompt："""
        else:
            # 写实风景电影感风格（新默认风格）
            include_figure = self.config.get("cover_include_figure", True)
            figure_prompt = "with a person standing in the distance looking at the view, back view, silhouette," if include_figure else ""
            
            prompt_text = f"""你是一位顶尖的电影美术指导。请根据歌名发散联想，生成电影感风景图片的Prompt。

=== 输入 ===
歌名：{title}
歌手：{singer}

=== 画风要求 ===
- 写实风格：photorealistic, realistic, cinematic, 8k uhd
- 风景为主：landscape, scenic view, atmospheric perspective
- 电影感：cinematic composition, dramatic lighting, film grain, color grading
- 情绪氛围：moody, atmospheric, emotional depth
{"- 人物元素：distant figure, back view, silhouette, contemplative" if include_figure else ""}

=== 输出格式 ===
只输出英文标签，逗号分隔，不要解释：

masterpiece, best quality, photorealistic, 8k uhd, cinematic lighting, film grain, [风景类型如mountain/ocean/cityscape], [时间如sunset/sunrise/night], [天气氛围如misty/cloudy/starry], [核心意象], [情绪关键词], {figure_prompt} color grading, atmospheric perspective, highly detailed

现在请根据歌名"{title}"生成Prompt："""

        try:
            response = await client.chat(
                messages=[{"role": "user", "content": prompt_text}],
                model="deepseek-chat",
                temperature=0.7
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Prompt generation failed: {e}")
            return None
            
    @with_retry(max_retries=3, base_delay=5.0)
    async def _generate_image(self, prompt: str) -> Optional[str]:
        """Generate image using SiliconFlow API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": self.image_size,
            "num_inference_steps": 25,
            "batch_size": 1,
            "seed": random.randint(1, 1000000000)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/images/generations",
                headers=headers,
                json=payload
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                
                if "data" in data and len(data["data"]) > 0:
                    return data["data"][0].get("url")
                return None
                
    async def _download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.read()
                
    def _find_font(self) -> Optional[str]:
        """Find suitable CJK font - prioritize bundled fonts, then system fonts"""
        # Get project root directory
        project_root = Path(__file__).parent.parent.resolve()
        fonts_dir = project_root / "fonts"
        
        # Priority 1: Check bundled fonts in project fonts directory
        if fonts_dir.exists():
            bundled_fonts = [
                "SourceHanSansSC-Regular.otf",
                "SourceHanSansSC-Bold.otf", 
                "NotoSansCJKsc-Regular.otf",
                "NotoSansCJKsc-Bold.otf",
                "NotoSansSC-Regular.ttf",
                "NotoSansSC-Bold.ttf",
                "simhei.ttf",
                "simsun.ttc",
                "msyh.ttc",
                "msyhbd.ttc",
                "PingFang.ttc",
                "STHeiti Light.ttc",
                "WenQuanYi Micro Hei.ttf",
            ]
            
            for font_name in bundled_fonts:
                font_path = fonts_dir / font_name
                if font_path.exists():
                    logger.info(f"   🔤 使用项目自带字体: {font_name}")
                    return str(font_path)
        
        # Priority 2: Check system fonts based on OS
        system_fonts = []
        
        # Windows
        if Path("C:/Windows/Fonts").exists():
            system_fonts = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/simsun.ttc", 
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/msyhbd.ttc",
                "C:/Windows/Fonts/simkai.ttf",
            ]
        # macOS
        elif Path("/System/Library/Fonts").exists():
            system_fonts = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
        # Linux
        else:
            linux_font_paths = [
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
            system_fonts = linux_font_paths
        
        for font_path in system_fonts:
            if Path(font_path).exists():
                logger.info(f"   🔤 使用系统字体: {Path(font_path).name}")
                return font_path
        
        # No suitable font found
        return None
                
    def _process_cover(self, image_data: bytes, output_path: Path, 
                      title: str, version: str, singer: str):
        """Process image: resize to 1500x1500, add text overlay"""
        # Load image
        img = Image.open(BytesIO(image_data))
        
        # Resize to 1500x1500
        img = img.resize((1500, 1500), Image.Resampling.LANCZOS)
        img = img.convert('RGBA')
        
        # Create overlay for bottom section
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # Draw semi-transparent black rectangle at bottom
        draw.rectangle([(0, 1000), (1500, 1500)], fill=(0, 0, 0, 160))
        
        # Composite overlay
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # Load font - 优先使用项目自带字体，然后查找系统字体
        font_path = self._find_font()
        
        if not font_path:
            logger.warning("No CJK font found! Text may be small or display incorrectly.")
        
        def get_font(size):
            if font_path:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception as e:
                    logger.warning(f"Font load error: {e}")
            return ImageFont.load_default()
        
        def get_fitted_font(text, max_width, start_size, min_size=40):
            size = start_size
            font = get_font(size)
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                width = bbox[2] - bbox[0]
            except:
                width = 100
            
            while width > max_width and size > min_size:
                size -= 5
                font = get_font(size)
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    width = bbox[2] - bbox[0]
                except:
                    break
            return font, width
        
        CANVAS_WIDTH = 1500
        MAX_TEXT_WIDTH = 1400
        
        # Prepare text
        if version:
            title_text = f"{title} ({version})"
        else:
            title_text = title
        
        # Get fitted fonts
        font_t, w_t = get_fitted_font(title_text, MAX_TEXT_WIDTH, 120, 50)
        x_t = (CANVAS_WIDTH - w_t) / 2
        y_t = 1180
        
        font_a, w_a = get_fitted_font(singer, MAX_TEXT_WIDTH, 70, 30)
        x_a = (CANVAS_WIDTH - w_a) / 2
        y_a = 1350
        
        # Draw with shadow
        def draw_txt(x, y, t, f):
            draw.text((x+4, y+4), t, font=f, fill=(0,0,0,255))
            draw.text((x, y), t, font=f, fill=(255,255,255,255))
        
        draw_txt(x_t, y_t, title_text, font_t)
        draw_txt(x_a, y_a, singer, font_a)
        
        # Save as PNG
        img.convert('RGB').save(output_path, 'PNG')