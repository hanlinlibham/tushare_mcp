#!/bin/bash

# ================================================================
# Tavily MCP 服务器注册脚本
# 用途：自动化注册 Tavily Search 到数据库
# ================================================================

set -e

echo "================================================"
echo "🔧 Tavily MCP 服务器注册脚本"
echo "================================================"

# 检查是否已安装 tavily-mcp
echo "🔍 检查 tavily-mcp 安装状态..."
if ! command -v tavily-mcp &> /dev/null; then
    echo "❌ tavily-mcp 未安装"
    echo ""
    echo "请先运行以下命令安装："
    echo "  npm install -g tavily-mcp"
    echo ""
    exit 1
fi

echo "✅ tavily-mcp 已安装"
tavily-mcp --version 2>/dev/null || echo "   (版本信息不可用)"

# 获取数据库连接信息（从环境变量或 .env 文件读取）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 尝试从 .env 文件加载
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📄 从 .env 文件加载配置..."
    source "$PROJECT_ROOT/.env"
elif [ -f "$PROJECT_ROOT/.env.local" ]; then
    echo "📄 从 .env.local 文件加载配置..."
    source "$PROJECT_ROOT/.env.local"
fi

# 设置默认值
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-able}"
DB_USER="${POSTGRES_USER:-able_user}"

echo ""
echo "📊 数据库连接信息:"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo ""

# 检查 SQL 文件是否存在
SQL_FILE="$SCRIPT_DIR/register_tavily_to_database.sql"
if [ ! -f "$SQL_FILE" ]; then
    echo "❌ SQL文件不存在: $SQL_FILE"
    exit 1
fi

# 执行SQL脚本
echo "🔄 执行SQL脚本注册 Tavily MCP 服务器..."
echo ""

psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tavily MCP 服务器注册成功！"
    echo ""
    echo "================================================"
    echo "📝 下一步操作："
    echo "================================================"
    echo ""
    echo "1. 🔄 重启后端服务"
    echo "   cd $PROJECT_ROOT"
    echo "   ./start_services.sh"
    echo ""
    echo "2. 🌐 在前端设置页面检查 Tavily Search 是否显示"
    echo "   http://localhost:8090/settings"
    echo ""
    echo "3. 🧪 测试搜索功能"
    echo "   在聊天界面询问实时信息，如："
    echo "   - \"搜索最新的人工智能发展趋势\""
    echo "   - \"查找特斯拉最新新闻\""
    echo ""
    echo "4. 📊 查看可用工具"
    echo "   - tavily-search: 实时网络搜索"
    echo "   - tavily-extract: 网页内容提取"
    echo "   - tavily-map: 网站结构地图"
    echo "   - tavily-crawl: 网站爬虫（Beta）"
    echo ""
else
    echo ""
    echo "❌ 注册失败，请检查错误信息"
    exit 1
fi

