
import asyncio
import os
import sys
import json
# Add backend to sys.path to use app modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.database import Database
from app.core.config import settings

# Override settings with user provided info if needed, or trust the user provided localhost:8176
# User said: localhost 8176
# User: casdoor_8WpN2Z
# Pass: casdoor_6ZP36a
# DB: casdoor_nspzbt

DATABASE_URL = "postgresql://casdoor_8WpN2Z:casdoor_6ZP36a@localhost:8176/casdoor_nspzbt"

async def register_tavily():
    """
    Register Tavily MCP server to the database using the specific credentials provided.
    """
    print(f"🔌 Connecting to database: {DATABASE_URL}")
    
    # Manually creating database instance with specific URL to ensure we use the right one
    # We can't use the default Database() because it reads from env/settings
    # We need to patch the settings or modify how we init Database, 
    # but app.database.Database reads settings.DATABASE_URL in __init__
    
    # Let's monkeypatch settings for this script execution
    settings.DATABASE_URL = DATABASE_URL
    
    db = Database()
    await db.connect()
    
    try:
        # Tavily Configuration
        server_name = "tavily-search"
        display_name = "Tavily Search"
        url = "stdio://tavily-mcp"
        connection_type = "stdio"
        timeout_seconds = 60
        is_enabled = True
        priority = 60
        description = "Tavily实时搜索服务。提供4个工具：search（通用搜索）、extract（页面提取）、map（网站地图）、crawl（爬虫）。"
        
        extra_config = {
            "command": "tavily-mcp",
            "args": [],
            "env": {
                "TAVILY_API_KEY": "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"
            }
        }
        
        # Check if exists
        query_check = "SELECT id FROM global_mcp_servers WHERE server_name = $1"
        existing = await db.fetch_one(query_check, server_name)
        
        if existing:
            print(f"🔄 Updating existing server: {server_name}")
            query_update = """
                UPDATE global_mcp_servers
                SET 
                    display_name = $1,
                    url = $2,
                    connection_type = $3,
                    timeout_seconds = $4,
                    is_enabled = $5,
                    extra_config = $6::jsonb,
                    priority = $7,
                    description = $8,
                    updated_at = now()
                WHERE server_name = $9
            """
            await db.execute(
                query_update,
                display_name,
                url,
                connection_type,
                timeout_seconds,
                is_enabled,
                json.dumps(extra_config),
                priority,
                description,
                server_name
            )
        else:
            print(f"✨ Inserting new server: {server_name}")
            query_insert = """
                INSERT INTO global_mcp_servers (
                    display_name, server_name, url, connection_type,
                    timeout_seconds, is_enabled, extra_config, priority,
                    description, auth_type
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, 'none'
                )
            """
            await db.execute(
                query_insert,
                display_name,
                server_name,
                url,
                connection_type,
                timeout_seconds,
                is_enabled,
                json.dumps(extra_config),
                priority,
                description
            )
            
        print("✅ Tavily Search registered successfully!")
        
    except Exception as e:
        print(f"❌ Registration failed: {e}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(register_tavily())

