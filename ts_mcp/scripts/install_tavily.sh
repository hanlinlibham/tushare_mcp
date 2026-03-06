#!/bin/bash

# ================================================================
# Tavily MCP 完整安装脚本
# 用途：一键安装和配置 Tavily Search 服务
# ================================================================

set -e

echo "========================================================"
echo "🚀 Tavily MCP 完整安装脚本"
echo "========================================================"
echo ""

# ================================================================
# 步骤 1: 检查 Node.js 和 npm
# ================================================================
echo "📦 步骤 1/4: 检查依赖..."
echo ""

if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装"
    echo "请先安装 Node.js (v20 或更高版本)"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装"
    echo "请先安装 npm"
    exit 1
fi

echo "✅ Node.js $(node --version)"
echo "✅ npm $(npm --version)"
echo ""

# ================================================================
# 步骤 2: 安装 tavily-mcp
# ================================================================
echo "📦 步骤 2/4: 安装 tavily-mcp..."
echo ""

if command -v tavily-mcp &> /dev/null; then
    echo "⚠️  tavily-mcp 已安装"
    echo "当前版本: $(tavily-mcp --version 2>/dev/null || echo '未知')"
    echo ""
    read -p "是否重新安装? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 重新安装 tavily-mcp..."
        npm install -g tavily-mcp@latest
    fi
else
    echo "📥 安装 tavily-mcp..."
    npm install -g tavily-mcp
fi

echo ""
echo "✅ tavily-mcp 安装完成"
tavily-mcp --version 2>/dev/null || echo "   (版本信息不可用)"
echo ""

# ================================================================
# 步骤 3: 注册到数据库
# ================================================================
echo "📊 步骤 3/4: 注册到数据库..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 执行注册脚本
if [ -f "$SCRIPT_DIR/register_tavily.sh" ]; then
    bash "$SCRIPT_DIR/register_tavily.sh"
else
    echo "❌ 找不到注册脚本: register_tavily.sh"
    exit 1
fi

# ================================================================
# 步骤 4: 验证安装
# ================================================================
echo ""
echo "========================================================"
echo "🎉 安装完成！"
echo "========================================================"
echo ""
echo "📝 接下来的操作："
echo ""
echo "1. 🔄 重启服务"
echo "   cd /home/abmind_v01"
echo "   ./start_services.sh"
echo ""
echo "2. 🌐 打开前端设置页面"
echo "   http://localhost:8090/settings"
echo "   确认 'Tavily Search' 显示为已启用"
echo ""
echo "3. 🧪 测试搜索功能"
echo "   在聊天界面测试："
echo "   - \"搜索最新的AI发展趋势\""
echo "   - \"查找特斯拉最新新闻\""
echo ""
echo "4. 📚 查看文档"
echo "   /home/abmind_v01/mcp/docs/TAVILY_INTEGRATION_GUIDE.md"
echo ""
echo "========================================================"

