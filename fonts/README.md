# 字体目录

此目录用于存放封面生成所需的中文字体文件。

## 推荐字体

### 1. 思源黑体 (Source Han Sans / Noto Sans CJK) ⭐推荐
- **文件名**: `SourceHanSansSC-Regular.otf` 或 `NotoSansCJKsc-Regular.otf`
- **下载地址**: https://github.com/adobe-fonts/source-han-sans/releases
- **许可证**: SIL Open Font License 1.1（免费商用）

### 2. 系统字体（备用）
如果未放置字体文件，程序会尝试查找系统字体：
- Windows: `C:/Windows/Fonts/simhei.ttf`, `msyh.ttc`
- macOS: `/System/Library/Fonts/PingFang.ttc`
- Linux: `/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc`

## 使用方法

1. 下载推荐字体文件
2. 将 `.otf` 或 `.ttf` 文件放入此目录
3. 程序会自动识别并使用

## 注意事项

- 字体文件较大（10-20MB），请勿提交到 Git
- 建议使用 Regular 和 Bold 两种字重
- 确保字体支持中文，否则封面文字会显示为小方块或默认字体