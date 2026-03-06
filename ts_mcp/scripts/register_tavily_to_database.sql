-- ================================================================
-- Tavily MCP 服务器配置注册脚本
-- 用途：将 Tavily Search 服务器注册到 global_mcp_servers 表
-- 连接方式：stdio (本地安装)
-- ================================================================

INSERT INTO global_mcp_servers (
    display_name,
    server_name,
    url,
    connection_type,
    timeout_seconds,
    is_enabled,
    extra_config,
    priority,
    description,
    created_by,
    auth_token,
    auth_type
) VALUES (
    'Tavily Search',                                    -- display_name
    'tavily-search',                                    -- server_name
    'stdio://tavily-mcp',                              -- url (占位符)
    'stdio',                                            -- connection_type
    60,                                                 -- timeout_seconds (搜索可能较慢)
    true,                                               -- is_enabled
    jsonb_build_object(
        'command', 'tavily-mcp',                       -- 全局安装后的命令
        'args', ARRAY[]::text[],                       -- 无需额外参数
        'env', jsonb_build_object(
            'TAVILY_API_KEY', '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'
        )
    ),
    60,                                                 -- priority (中等优先级)
    'Tavily实时搜索服务。提供4个工具：search（通用搜索）、extract（页面提取）、map（网站地图）、crawl（爬虫）。支持实时互联网信息检索，适用于市场研究、新闻追踪、竞品分析、数据收集等场景。', -- description
    'system',                                           -- created_by
    NULL,                                               -- auth_token (stdio不需要)
    'none'                                              -- auth_type
)
ON CONFLICT (server_name) 
DO UPDATE SET
    display_name = EXCLUDED.display_name,
    url = EXCLUDED.url,
    connection_type = EXCLUDED.connection_type,
    timeout_seconds = EXCLUDED.timeout_seconds,
    is_enabled = EXCLUDED.is_enabled,
    extra_config = EXCLUDED.extra_config,
    priority = EXCLUDED.priority,
    description = EXCLUDED.description,
    updated_at = now()
RETURNING 
    id, 
    server_name, 
    display_name, 
    url,
    connection_type,
    is_enabled,
    priority,
    created_at;

-- 显示注册结果
SELECT 
    server_name,
    display_name,
    connection_type,
    is_enabled,
    priority,
    description
FROM global_mcp_servers
WHERE server_name = 'tavily-search';

