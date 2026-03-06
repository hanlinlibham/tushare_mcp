#!/bin/bash
# Tushare MCP 服务器停止脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 Stopping Tushare MCP Server...${NC}"

# 检查PM2是否安装
if ! command -v pm2 &> /dev/null; then
    echo -e "${RED}❌ PM2 not installed${NC}"
    exit 1
fi

# 停止服务
pm2 stop tushare-mcp 2>/dev/null || {
    echo -e "${YELLOW}⚠️ Tushare MCP Server is not running${NC}"
    exit 0
}

echo -e "${GREEN}✅ Tushare MCP Server stopped${NC}"

