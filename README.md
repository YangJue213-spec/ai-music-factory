# Music Factory - 跨平台音乐生成工厂

音乐生成工厂 Windows/macOS 便携版本，一键启动，自动安装依赖，开箱即用。

## ✨ 功能特性

- ✅ **一键启动** - 双击 bat/command 文件，自动安装所有依赖
- ✅ **跨平台** - 支持 Windows 10/11 和 macOS 10.15+
- ✅ **Web 可视化** - 浏览器访问 http://localhost:5000，可视化操作
- ✅ **双重指纹保护** - AI 指纹移除 + FFmpeg 后处理
- ✅ **智能去重** - 基于指纹算法，自动跳过已生成歌曲
- ✅ **酷狗榜单采集** - 自动获取热门歌曲数据
- ✅ **AI 全流程** - DeepSeek 分析 + OpenAI 写词 + Suno 生成 + SiliconFlow 封面

---

## 🚀 快速开始

### 第一步：安装 Python

**Windows:**
1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.10+
3. **安装时勾选** `Add Python to PATH`

**macOS:**
```bash
brew install python
# 或从官网下载安装包
```

### 第二步：配置 API 密钥

编辑 `config/apis.yaml`，填写您的 API 密钥：

```yaml
apis:
  deepseek:
    api_key: "sk-your-deepseek-api-key"
  openai:
    api_key: "sk-your-openai-api-key"
  suno:
    api_key: "your-suno-api-key"
  siliconflow:
    api_key: "sk-your-siliconflow-api-key"
```

获取地址：
- DeepSeek: https://platform.deepseek.com
- OpenAI: https://platform.openai.com
- Suno: https://www.acedata.cloud
- SiliconFlow: https://siliconflow.cn

### 第三步：双击启动

| 模式 | Windows | macOS |
|------|---------|-------|
| **Web 可视化** | 双击 `web_start.bat` | 双击 `web_start.command` |
| **命令行** | 双击 `start.bat` | 双击 `start.command` |

> 💡 **首次启动需要 2-5 分钟**（自动安装依赖）

启动后：
- **Web 模式**：浏览器访问 http://localhost:5000
- **命令行模式**：在终端中交互操作

---

## 📁 目录结构

```
music_made/
├── launcher.py              # 跨平台启动器核心
├── start.bat                # Windows 命令行启动（中文）
├── web_start.bat            # Windows Web 启动（中文）
├── start_en.bat             # Windows 命令行启动（英文）
├── web_start_en.bat         # Windows Web 启动（英文）
├── start.command            # macOS 命令行启动
├── web_start.command        # macOS Web 启动
├── setup_mac.sh             # macOS 权限设置脚本
├── config/
│   ├── apis.yaml           # API 密钥配置
│   ├── settings.yaml       # 生成设置
│   ├── singers.yaml        # 歌手列表
│   └── sources.yaml        # 音乐源配置
├── core/                    # 核心框架
├── stages/                  # 处理阶段
├── scripts/                 # 工具脚本
├── third_party/             # 第三方工具（AI指纹移除）
├── web/                     # Web 界面
├── output/                  # 输出目录（自动生成）
└── venv/                    # 虚拟环境（自动创建）
```

---

## 🎵 输出文件

生成的文件按日期归档到 `output/musics/MM.DD/`：

```
output/musics/02.07/
├── 爱过的人一生惦记 (伤感版)-花花.mp3   # 音频
├── 爱过的人一生惦记 (伤感版)-花花.png   # 封面
└── 爱过的人一生惦记 (伤感版)-花花.txt   # 歌词
```

每个歌曲生成两个版本：
- **带版本标注** - 如"伤感版"、"治愈版"
- **原版** - 不带版本标注

---

## ⚙️ 自定义配置

### 修改歌手列表

编辑 `config/singers.yaml`：
```yaml
female_singers:
  - "歌手1"
  - "歌手2"

male_singers:
  - "歌手1"
  - "歌手2"
```

或使用 Web 界面的"歌手管理"页面。

### 修改音乐源

编辑 `config/sources.yaml`：
```yaml
monitored_artists:
  - "艺人名称"

chart_sources:
  - name: "酷狗飙升榜"
    rank_id: 6666
    page_size: 100
    enabled: true
```

或使用 Web 界面的"音乐源管理"页面。

### 修改生成设置

编辑 `config/settings.yaml`：
```yaml
# 歌名生成模式
title_mode: "original"  # "original" 或 "chorus"

# 封面风格
cover_style: "realistic"  # "realistic" 或 "anime"

# 封面是否包含人物
cover_include_figure: true
```

或使用 Web 界面的"生成设置"页面。

---

## 🔧 启动选项

| 启动文件 | 适用平台 | 语言 | 特点 |
|----------|----------|------|------|
| `web_start.bat` | Windows | 中文 | Web 可视化界面，推荐新手 |
| `start.bat` | Windows | 中文 | 命令行界面，简洁高效 |
| `web_start_en.bat` | Windows | 英文 | Web 界面，避免编码问题 |
| `start_en.bat` | Windows | 英文 | 命令行，避免编码问题 |
| `web_start.command` | macOS | 中文 | Web 可视化界面 |
| `start.command` | macOS | 中文 | 命令行界面 |

---

## 🐛 常见问题

### 首次启动卡在"安装依赖"

正在下载 numpy、scipy 等大型库，耐心等待 3-5 分钟。如失败，可手动安装：
```bash
pip install numpy scipy librosa soundfile mutagen matplotlib
```

### Windows 中文显示乱码

使用英文版启动脚本：
- `start_en.bat` 代替 `start.bat`
- `web_start_en.bat` 代替 `web_start.bat`

### 提示 "Python not found"

**Windows:** 安装 Python 时勾选 "Add Python to PATH"  
**macOS:** `brew install python`

### 如何指定生成数量

**Web 界面**：控制面板中输入数字  
**命令行**：
```bash
start.bat --count 5
```

---

## 💡 使用技巧

1. **首次使用**：建议先用 Web 界面熟悉流程
2. **批量生成**：设置数量后让程序自动运行，无需值守
3. **随时停止**：按 Ctrl+C 或点击 Web 界面的"停止"按钮
4. **查看日志**：Web 界面"运行日志"标签页，或 `data/logs/` 目录

---

## 📋 系统要求

- **操作系统**: Windows 10/11 或 macOS 10.15+
- **Python**: 3.10 或更高版本
- **内存**: 建议 8GB 以上
- **磁盘空间**: 至少 2GB 可用空间
- **网络**: 需要连接互联网调用 API

---

## 📖 详细文档

- **完整使用手册**: [USER_GUIDE.md](USER_GUIDE.md)
- **Windows 专用说明**: [WINDOWS_README.md](WINDOWS_README.md)
- **便携版说明**: [PORTABLE_README.md](PORTABLE_README.md)

---

## 📝 许可证

本项目采用 [GNU General Public License v3.0 (GPL-3.0)](LICENSE) 开源许可证。

```
AI Music Factory - 跨平台音乐生成工厂
Copyright (C) 2024 AI Music Factory Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
```

## 🙏 致谢

- [DeepSeek](https://platform.deepseek.com) - AI 歌词分析
- [OpenAI](https://platform.openai.com) - AI 歌词创作
- [Suno](https://www.acedata.cloud) - AI 音乐生成
- [SiliconFlow](https://siliconflow.cn) - AI 封面生成

---

**祝您使用愉快！🎵**
