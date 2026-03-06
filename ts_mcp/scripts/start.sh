#!/bin/bash
# Tushare MCP 服务器启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目路径
PROJECT_DIR="/home/abmind_v01"
MCP_DIR="${PROJECT_DIR}/mcp"
LOG_DIR="${PROJECT_DIR}/logs/mcp"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}🚀 Starting Tushare MCP Server${NC}"
echo -e "${GREEN}======================================${NC}"

# 创建日志目录
echo -e "${YELLOW}📁 Creating log directory...${NC}"
mkdir -p "${LOG_DIR}"

# 激活conda环境
echo -e "${YELLOW}🐍 Activating conda environment: able_bff${NC}"
source "/opt/miniforge/etc/profile.d/conda.sh"
conda activate able_bff

# 检查必要的包
echo -e "${YELLOW}🔍 Checking required packages...${NC}"
python -c "import fastmcp" 2>/dev/null || {
    echo -e "${RED}❌ fastmcp not installed${NC}"
    echo -e "${YELLOW}Installing fastmcp...${NC}"
    pip install fastmcp uvicorn
}

python -c "import tushare" 2>/dev/null || {
    echo -e "${RED}❌ tushare not installed${NC}"
    echo -e "${YELLOW}Installing tushare...${NC}"
    pip install tushare
}

# 切换到MCP目录
cd "${MCP_DIR}"

# 加载环境变量
if [ -f "${MCP_DIR}/.env" ]; then
    echo -e "${YELLOW}📝 Loading environment variables from .env${NC}"
    export $(cat "${MCP_DIR}/.env" | grep -v '^#' | xargs)
fi

# 检查PM2是否安装
if ! command -v pm2 &> /dev/null; then
    echo -e "${RED}❌ PM2 not installed${NC}"
    echo -e "${YELLOW}Please install PM2: npm install -g pm2${NC}"
    exit 1
fi

# 停止已存在的实例
echo -e "${YELLOW}🛑 Stopping existing instances...${NC}"
pm2 delete tushare-mcp 2>/dev/null || true

# 启动MCP服务器
echo -e "${YELLOW}🚀 Starting Tushare MCP Server...${NC}"
pm2 start ecosystem.config.js

# 保存PM2配置
pm2 save

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✅ Tushare MCP Server Started${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}📊 Server Info:${NC}"
echo -e "   URL: http://127.0.0.1:8006"
echo -e "   Conda Env: able_bff"
echo -e "   Log Dir: ${LOG_DIR}"
echo ""
echo -e "${YELLOW}📝 Useful Commands:${NC}"
echo -e "   Check status: ${GREEN}pm2 list${NC}"
echo -e "   View logs:    ${GREEN}pm2 logs tushare-mcp${NC}"
echo -e "   Restart:      ${GREEN}pm2 restart tushare-mcp${NC}"
echo -e "   Stop:         ${GREEN}pm2 stop tushare-mcp${NC}"
echo ""

