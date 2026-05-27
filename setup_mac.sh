#!/bin/bash
# Music Factory - macOS 权限设置脚本
# 修复 .command 文件的执行权限

echo "🔧 Music Factory - macOS 权限设置"
echo "=================================="
echo ""

# 获取脚本所在目录
cd "$(dirname "$0")"

# 设置 .command 文件执行权限
echo "📋 设置启动脚本权限..."
chmod +x start.command
chmod +x web_start.command

echo "✅ 权限设置完成！"
echo ""
echo "现在可以双击以下文件启动："
echo "  - start.command      (命令行模式)"
echo "  - web_start.command  (Web界面模式)"
echo ""
echo "如果仍然提示无法打开，请："
echo "1. 右键点击 .command 文件"
echo "2. 选择'打开'"
echo "3. 在弹出的对话框中点击'打开'"
echo ""
read -p "按回车键退出..."