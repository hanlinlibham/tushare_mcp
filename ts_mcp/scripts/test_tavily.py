#!/usr/bin/env python3
"""
Tavily MCP 集成测试脚本
用途：验证 Tavily Search 服务是否正确集成
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.app.services.unified_mcp_service import get_unified_mcp_service
from backend.app.repositories.mcp_repository import McpRepository
from backend.app.database import get_db


async def test_tavily_connection():
    """测试 Tavily MCP 连接"""
    print("=" * 60)
    print("🧪 Tavily MCP 集成测试")
    print("=" * 60)
    print()
    
    try:
        # 1. 获取数据库连接
        print("📊 步骤 1: 连接数据库...")
        db = await get_db()
        repo = McpRepository(db)
        print("✅ 数据库连接成功")
        print()
        
        # 2. 查询 Tavily 配置
        print("🔍 步骤 2: 查询 Tavily 配置...")
        config = await repo.get_server_config_with_secrets('tavily-search')
        
        if not config:
            print("❌ 未找到 Tavily 配置")
            print("请先运行注册脚本: bash mcp/scripts/register_tavily.sh")
            return False
        
        print("✅ 找到配置:")
        print(f"   - server_name: {config.get('server_name')}")
        print(f"   - connection_type: {config.get('connection_type')}")
        print(f"   - url: {config.get('url')}")
        print(f"   - timeout: {config.get('timeout_seconds')}s")
        
        extra_config = config.get('extra_config', {})
        if extra_config:
            print(f"   - command: {extra_config.get('command')}")
            print(f"   - has API key: {'TAVILY_API_KEY' in extra_config.get('env', {})}")
        print()
        
        # 3. 测试连接
        print("🔌 步骤 3: 测试 MCP 连接...")
        service = get_unified_mcp_service()
        
        # 准备连接配置
        connect_config = {
            'connection_type': config['connection_type'],
            'url': config['url'],
            'timeout_seconds': config.get('timeout_seconds', 60),
            'extra_config': config.get('extra_config', {}),
        }
        
        success = await service.connect_server('tavily-search', connect_config)
        
        if not success:
            print("❌ 连接失败")
            print("请检查:")
            print("  1. tavily-mcp 是否已安装: which tavily-mcp")
            print("  2. API Key 是否有效")
            return False
        
        print("✅ 连接成功")
        print()
        
        # 4. 列出可用工具
        print("🔧 步骤 4: 列出可用工具...")
        tools = await service.list_tools('tavily-search')
        
        if not tools:
            print("⚠️  未找到工具")
            return False
        
        print(f"✅ 找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description', 'N/A')[:60]}...")
        print()
        
        # 5. 测试搜索功能（可选）
        print("🔍 步骤 5: 测试搜索功能...")
        print("   执行简单搜索: 'Python programming'")
        
        try:
            result = await service.call_tool(
                'tavily-search',
                'tavily-search',
                {
                    'query': 'Python programming',
                    'max_results': 2
                }
            )
            
            if result:
                print("✅ 搜索成功")
                print(f"   返回数据类型: {type(result)}")
                if isinstance(result, dict):
                    print(f"   结果字段: {list(result.keys())}")
            else:
                print("⚠️  搜索返回空结果")
        except Exception as e:
            print(f"⚠️  搜索测试失败: {e}")
        print()
        
        # 6. 清理
        print("🧹 清理连接...")
        await service.disconnect_server('tavily-search')
        
        print()
        print("=" * 60)
        print("🎉 测试完成！Tavily MCP 集成成功")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await test_tavily_connection()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())

