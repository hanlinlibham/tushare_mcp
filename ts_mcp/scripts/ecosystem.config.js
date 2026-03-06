/**
 * PM2 配置文件 - MCP 服务器管理
 *
 * 使用方式：
 *   启动: pm2 start ecosystem.config.js
 *   停止: pm2 stop ecosystem.config.js
 *   重启: pm2 restart ecosystem.config.js
 *   查看: pm2 list
 *   日志: pm2 logs tushare-mcp
 */

module.exports = {
  apps: [
    {
      name: 'tushare-mcp',
      script: 'tushare_server.py',
      interpreter: '/opt/miniforge/envs/able_bff/bin/python',
      cwd: '/home/abmind_v01/mcp',
      args: '--host 0.0.0.0 --port 8006',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        // ✅ Tushare token 从环境变量读取
        // Python代码会自动从 /home/abmind_v01/mcp/.env 加载 TUSHARE_TOKEN
        BACKEND_API_URL: 'http://localhost:8004'
      },
      error_file: '/home/abmind_v01/logs/mcp/tushare-mcp-error.log',
      out_file: '/home/abmind_v01/logs/mcp/tushare-mcp-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000,
    },
    {
      name: 'tushare-mcp-modular',
      script: 'src/server.py',
      interpreter: '/opt/miniforge/envs/able_bff/bin/python',
      cwd: '/home/abmind_v01/mcp',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        PYTHONUNBUFFERED: '1',
        // ✅ Tushare token 从环境变量读取
        // Python代码会自动从 /home/abmind_v01/mcp/.env 加载 TUSHARE_TOKEN
        BACKEND_API_URL: 'http://localhost:8004',
        MCP_SERVER_HOST: '0.0.0.0',
        MCP_SERVER_PORT: '8007'
      },
      error_file: '/home/abmind_v01/logs/mcp/tushare-mcp-modular-error.log',
      out_file: '/home/abmind_v01/logs/mcp/tushare-mcp-modular-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      min_uptime: '10s',
      max_restarts: 10,
      restart_delay: 4000,
    }
  ]
};

