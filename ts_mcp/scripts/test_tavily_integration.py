
import asyncio
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.mcp.unified_service import get_unified_mcp_service

async def test_tavily_search():
    """测试 Tavily Search 工具"""
    service = get_unified_mcp_service()
    
    print("=" * 60)
    print("🧪 Testing Tavily Search Integration")
    print("=" * 60)
    
    # Test 1: Check connection
    if service.is_connected("tavily-search"):
        print("✅ Tavily Search is connected")
    else:
        print("❌ Tavily Search is NOT connected")
        return
    
    # Test 2: Call tavily-search tool
    print("\n🔍 Testing tavily-search tool...")
    try:
        result = await service.call_tool(
            "tavily-search",
            "tavily-search",
            {
                "query": "latest AI technology 2024",
                "max_results": 3
            }
        )
        print(f"✅ Search completed successfully!")
        print(f"   Result type: {type(result)}")
        if isinstance(result, dict) and 'content' in result:
            print(f"   Content preview: {str(result['content'])[:200]}...")
        elif isinstance(result, list) and len(result) > 0:
            print(f"   First result preview: {str(result[0])[:200]}...")
        else:
            print(f"   Result preview: {str(result)[:200]}...")
            
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Tavily Integration Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_tavily_search())

