# findatamcp

> 中文版 · [English](README.en.md)

基于 MCP (Model Context Protocol) 的金融数据服务器，面向 LLM Agent 提供 A 股行情、财务、指数、基金、宏观等结构化数据访问能力，并将工具调用结果自动渲染为可交互的前端 UI。底层数据源为 Tushare Pro。

原名 `tushare_mcp`，重构后更名为 `findatamcp`，采用模块化包结构。

## 预览

工具调用的结构化结果会通过 MCP Apps 规范（SEP-1865，protocol `2025-06-18`）回传 `ui://` 资源，客户端在沙箱 iframe 中渲染为交互组件；LLM 则通过 `content[0].text` 看到同一数据的 markdown 表格摘要，避免重复调用。

<p align="center">
  <img src="docs/pic/overview.png" alt="A 股市场概况卡片" width="720"><br>
  <sub><code>get_market_overview</code> — 全市场一页纸：涨跌家数、均值、PE/PB 中位数、环形占比</sub>
</p>

<p align="center">
  <img src="docs/pic/k-line-ui.png" alt="沪深 300 日 K 线" width="720"><br>
  <sub><code>get_historical_data(ts_code="000300.SH", include_ui=True)</code> — 日 K + 双均线 + 成交量，可缩放拖动</sub>
</p>

## 快速开始

```bash
# Python 3.10+
conda create -n findatamcp python=3.12
conda activate findatamcp

pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 TUSHARE_TOKEN

# 运行（三选一）
python -m findatamcp.server              # Streamable HTTP，推荐
python -m findatamcp.server_sse          # SSE，配合 Claude Desktop 等
./start.sh                               # PM2 守护
```

### PM2 环境变量

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `FINDATA_PYTHON` | `~/miniforge3/envs/mcp_server/bin/python` | Python 解释器路径 |
| `FINDATA_MCP_DIR` | `pm2.config.js` 所在目录 | 仓库根 |
| `FINDATA_LOG_DIR` | `~/.mcp-logs` | 日志目录 |
| `FINDATA_DATA_DIR` | `/tmp/findatamcp_data` | 大数据 artifact 落盘目录 |
| `MCP_SERVER_HOST` | `127.0.0.1` | 绑定地址 |
| `MCP_SERVER_PORT` | `8006` | 端口 |
| `SERVER_BASE_URL` | `http://127.0.0.1:8006` | artifact 外链基址 |

## 目录结构

```
findatamcp/
├── findatamcp/             # 主包
│   ├── server.py           # Streamable HTTP 入口，组装 DI 容器
│   ├── server_sse.py       # SSE 入口
│   ├── config.py           # 配置
│   ├── database.py         # SQLite 查询
│   ├── entity_store.py     # 实体索引（内存 + pypinyin）
│   ├── cache/              # tushare 响应 / 计算 / 文件 artifact
│   │   ├── tushare_cache.py
│   │   ├── calc_cache.py
│   │   └── data_file_store.py
│   ├── tools/              # MCP tools（12 模块 × 42 个 @mcp.tool）
│   ├── resources/          # MCP resources
│   │   ├── ui_apps.py      # ui:// 交互组件（HTML + 内联 ECharts）
│   │   ├── large_data.py   # data:// JSONL artifact 回读
│   │   ├── stock_data.py
│   │   └── entity_stats.py
│   ├── prompts/            # MCP prompts（stock_analysis 等）
│   ├── routes/             # 额外 HTTP 路由（数据下载）
│   └── utils/
│       ├── artifact_payload.py    # 统一 envelope 构造
│       ├── ui_hint.py             # LLM 提示文案
│       ├── tushare_api.py
│       ├── data_processing.py     # 对齐 / 停牌处理
│       ├── technical_indicators.py
│       ├── large_data_handler.py
│       ├── response.py
│       └── errors.py
├── tests/                  # pytest 测试
├── docs/                   # 文档（含截图）
├── static/                 # 前端资源（AG Charts / ECharts，本地打包）
├── pm2.config.js           # PM2 部署配置
├── start.sh / stop.sh      # PM2 生命周期
├── start_sse.sh            # SSE 前台启动
└── requirements.txt
```

## 工具一览

共 **42 个 MCP tool**，分 **12 个模块**：

| 模块 | 内容 |
| :--- | :--- |
| `market_data` | 实时行情、历史 K 线、日线 |
| `market_flow` | 资金流、成交明细 |
| `market_statistics` | 涨跌家数、板块统计 |
| `financial_data` | 财务三表、指标、分红 |
| `performance_data` | 业绩预告 / 快报 |
| `index_data` | 指数行情与成分股 |
| `fund_data` | 公募基金净值、持仓 |
| `sector` | 行业 / 概念板块 |
| `macro_data` | 宏观经济指标（GDP / CPI / PMI / M2 / LPR…）|
| `analysis` | 技术指标、相关性、对齐 |
| `search` | 代码 / 名称 / 拼音 / 别名检索 |
| `meta` | 元数据与能力发现 |

同时暴露 resources（`entity_stats`、`large_data`、`stock_data`、`ui_apps`）和 prompts（`stock_analysis`）。

---

## 实现路径

findatamcp 的核心是一套**"工具侧生产数据、UI 侧沉浸式消费、LLM 侧简短摘要"**的三层契约。下面按数据流向拆解。

### 1. Envelope 契约：content + structuredContent + meta

每个工具最终通过 `finalize_artifact_result`（`findatamcp/utils/artifact_payload.py`）输出一个 `ToolResult`，三层分工：

| 层 | 消费方 | 内容 |
| :--- | :--- | :--- |
| `content[0].text` | LLM | header + 前 10 行 markdown 表 + 尾部引导（"已渲染 UI"/"还有多少行"/"要完整数据请设 as_file=True"）|
| `structuredContent` | UI iframe / execute 工具 | 唯一完整数据源：`row_count` / `columns=[{name,type}]` / `rows=[…]` / 可选 `date_range` / 可选 `path` / 可选 `download_urls` |
| `meta` | MCP host | `{ui: None}` 显式关闭 UI 渲染（`include_ui=False` 时），否则继承 `app=AppConfig(...)` 注册的 `ui://` |

这样 LLM 看到的永远是简短文本 + 引导，不会被大表淹没；UI 和下游脚本通过 `structuredContent.rows` 拿到完整数据；两者出自同一份 `rows`，避免副本漂移。

### 2. MCP UI：ui:// 资源 + iframe postMessage

`findatamcp/resources/ui_apps.py` 注册若干 `ui://findata/*` 资源（`market-dashboard` / `kline-chart` / `moneyflow-chart` / `macro-panel` / `data-table`），返回值是一段完整 HTML：

- **零 CDN 依赖**：`static/echarts.min.js` 在服务端启动时读进内存，直接内联到 `<script>` 标签，满足沙箱 iframe 的 CSP / 离线部署需求
- **主题变量透传**：HTML 用 `light-dark()` CSS 变量，host 发 `ui/notifications/host-context-changed` 时同步切换明暗
- **四个握手消息**（protocol `2025-06-18`）：
  - `ui/initialize`（host → iframe，iframe 回 `result.protocolVersion + appCapabilities`）
  - `ui/notifications/initialized`（iframe → host，报告就绪）
  - `ui/notifications/tool-input`（host → iframe，带入参）
  - `ui/notifications/tool-result`（host → iframe，带 `structuredContent` 或 `content`，iframe 解析并 render）

工具端只需在 `@mcp.tool(app=AppConfig(ui_uri="ui://findata/kline-chart"))` 声明绑定关系，host 就会把 `structuredContent` 推给对应 iframe。

### 3. 大数据 artifact：JSONL + 列 schema sidecar

默认（`as_file=False`）数据直接内嵌 `structuredContent.rows`。当用户要"导出 / 保存"或 LLM 计划调用 `execute` 做二次分析时传 `as_file=True`，流程：

1. `data_file_store.store(rows, tool_name, query_params)`（`findatamcp/cache/data_file_store.py`）把行写成 `.jsonl`（日期 / 代码列强制字符串化、`NaN → null`）
2. 同时 dump 一份列 `schema` sidecar（`{col: {"type": date|string|number|bool}}`），供下游 AG Grid 推断列类型
3. 返回语义化文件名（`get_historical_data_000300.SH_20260306_20260402.jsonl`）+ `/workspace/<name>` 路径 + `download_urls`
4. `include_ui=False` 时额外把 `meta.ui` 置 None，host 不再渲染 UI —— 典型用法：LLM 要自己用 matplotlib 画图，避免双图混淆

### 4. LLM 行为约束：防重复调用

UI 渲染型工具有个老问题：LLM 只能看到 `content.text`，不知道 iframe 已经出图，很容易"再调一次看看"。`findatamcp/utils/ui_hint.py` 和 `artifact_payload.build_content_trailer` 联手在 text 尾部写死 4 行提示：

```
UI 已同步渲染（ui://findata/kline-chart）。
完整 245 行数据已写入 /workspace/xxx.jsonl。
用户可在 artifact 面板打开此文件交互查看；你也可以用 execute 读此文件做进一步分析。
```

同时 tool docstring 里塞入 `AS_FILE_INCLUDE_UI_DECISION_GUIDE`，把 `as_file` / `include_ui` 的决策表直接曝露给 LLM。实测重复调用率显著下降。

### 5. 依赖注入 + 工具注册

`server.py` 在启动时装配一次性 DI 容器：

```python
api       = TushareAPI(token, cache=tushare_cache)
db        = EntityStore.from_sqlite(db_path)
mcp       = FastMCP("findatamcp")

register_market_tools(mcp, api)
register_financial_tools(mcp, api)
register_search_tools(mcp, api, db)
# … 12 个 register_*_tools
```

每个模块的 `register_*_tools(mcp, api, [db])` 负责把 `@mcp.tool` / `@mcp.resource` / `@mcp.prompt` 挂到 FastMCP 实例。测试里可以替换 `api` 为 mock，`db` 为内存 fixture。

### 6. 缓存分层

| 层 | 位置 | 失效策略 |
| :--- | :--- | :--- |
| Tushare 原始响应 | `cache/tushare_cache.py` | 按表命名 + 参数哈希，按请求频率设 TTL |
| 计算结果（对齐 / 技术指标） | `cache/calc_cache.py` | 进程内 LRU，重启清空 |
| 文件 artifact（.jsonl / schema） | `cache/data_file_store.py` | 24h TTL，定时清理过期文件 |

异步层面，Tushare Python SDK 是同步的，`TushareAPI` 统一用 `asyncio.to_thread` 包装，保证 FastMCP 的事件循环不被阻塞。

### 7. 实体检索：EntityStore + pypinyin

搜索类工具常需把 "白酒行业"、"招商银行"、"平安" 映射到代码列表。`entity_store.py` 在启动时把 SQLite 里的全量证券实体装进内存：

- 主索引：`ts_code → entity`
- 倒排索引：name / 拼音全拼 / 拼音首字母 / 别名 → ts_code 集合
- 中文名用 `pypinyin` 预计算拼音，支持"zsyh/招行/招商银行"多形态命中

搜索走内存索引 + TF 排序，响应稳定在毫秒级，不走 Tushare 接口。

---

## 配置

`.env` 常用变量：

```bash
TUSHARE_TOKEN=your_token_here       # 必需
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8006
MCP_TRANSPORT=streamable-http        # 或 sse
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

## 测试

```bash
pytest tests/
```

覆盖缓存、数据处理、市场统计、工具注册、SSE 客户端、端到端流程。

## 文档

- [docs/SSE_GUIDE.md](docs/SSE_GUIDE.md) — SSE 部署与客户端接入

## License

Tushare Pro 数据使用请遵循 [Tushare 用户协议](https://tushare.pro/document/1)。本仓库代码以 MIT 发布。
