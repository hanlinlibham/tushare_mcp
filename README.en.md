# findatamcp

> English · [中文](README.md)

**One call. Data for the model. UI for the human.**

**findatamcp** lets LLM agents pull both *structured data for the model* and *an interactive chart for the user* in a single tool call. It ships 42 financial-data tools (A-share quotes, financial statements, funds, macro) and renders results as live UI — zoomable K-lines, market breadth dashboards, money-flow lines — via the MCP Apps spec. One fetch, no re-invocations, users interact directly in the artifact panel. Backed by Tushare Pro.

Formerly `tushare_mcp`; renamed to `findatamcp` after a modular refactor.

## Preview

Structured tool results are shipped through MCP Apps (SEP-1865, protocol `2025-06-18`). The host renders a registered `ui://` resource inside a sandboxed iframe, while the LLM sees a concise markdown-table summary in `content[0].text` — so the same data reaches both the user and the model without duplication or re-invocation.

<p align="center">
  <img src="docs/pic/overview.png" alt="A-share market overview" width="720"><br>
  <sub><code>get_market_overview</code> — one-page market stats: gainers/losers, averages, PE/PB medians, donut breakdown</sub>
</p>

<p align="center">
  <img src="docs/pic/k-line-ui.png" alt="CSI 300 daily K-line" width="720"><br>
  <sub><code>get_historical_data(ts_code="000300.SH", include_ui=True)</code> — daily candles with dual MA + volume, zoom & pan enabled</sub>
</p>

## Quick start

```bash
# Python 3.10+
conda create -n findatamcp python=3.12
conda activate findatamcp

pip install -r requirements.txt
cp .env.example .env
# edit .env, set TUSHARE_TOKEN

# run (pick one)
python -m findatamcp.server              # Streamable HTTP (recommended)
python -m findatamcp.server_sse          # SSE, for Claude Desktop et al.
./start.sh                               # PM2 daemon
```

### PM2 environment variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `FINDATA_PYTHON` | `~/miniforge3/envs/mcp_server/bin/python` | Python interpreter path |
| `FINDATA_MCP_DIR` | `pm2.config.js` parent dir | Repo root |
| `FINDATA_LOG_DIR` | `~/.mcp-logs` | Log directory |
| `FINDATA_DATA_DIR` | `/tmp/findatamcp_data` | Large artifact dump directory |
| `MCP_SERVER_HOST` | `127.0.0.1` | Bind address |
| `MCP_SERVER_PORT` | `8006` | Port |
| `SERVER_BASE_URL` | `http://127.0.0.1:8006` | External base URL for artifacts |

## Layout

```
findatamcp/
├── findatamcp/             # main package
│   ├── server.py           # Streamable HTTP entry, assembles the DI container
│   ├── server_sse.py       # SSE entry
│   ├── config.py           # configuration
│   ├── database.py         # SQLite query helpers
│   ├── entity_store.py     # in-memory entity index (pypinyin)
│   ├── cache/              # tushare responses / computed results / file artifacts
│   │   ├── tushare_cache.py
│   │   ├── calc_cache.py
│   │   └── data_file_store.py
│   ├── tools/              # MCP tools (12 modules × 42 @mcp.tool)
│   ├── resources/          # MCP resources
│   │   ├── ui_apps.py      # ui:// interactive components (HTML + inline ECharts)
│   │   ├── large_data.py   # data:// JSONL artifact reader
│   │   ├── stock_data.py
│   │   └── entity_stats.py
│   ├── prompts/            # MCP prompts (e.g., stock_analysis)
│   ├── routes/             # extra HTTP routes (downloads)
│   └── utils/
│       ├── artifact_payload.py    # unified envelope builder
│       ├── ui_hint.py             # LLM guidance text
│       ├── tushare_api.py
│       ├── data_processing.py     # alignment / halted-trading handling
│       ├── technical_indicators.py
│       ├── large_data_handler.py
│       ├── response.py
│       └── errors.py
├── tests/                  # pytest suite
├── docs/                   # docs (including screenshots)
├── static/                 # frontend assets (AG Charts / ECharts, bundled locally)
├── pm2.config.js           # PM2 deployment config
├── start.sh / stop.sh      # PM2 lifecycle
├── start_sse.sh            # SSE foreground launcher
└── requirements.txt
```

## Tool catalogue

**42 MCP tools** across **12 modules**:

| Module | Scope |
| :--- | :--- |
| `market_data` | Realtime quotes, historical candles, daily bars |
| `market_flow` | Money flow, tick detail |
| `market_statistics` | Breadth, sector stats |
| `financial_data` | Three statements, ratios, dividends |
| `performance_data` | Earnings previews / flash reports |
| `index_data` | Index quotes & constituents |
| `fund_data` | Mutual-fund NAV & holdings |
| `sector` | Industry / thematic sectors |
| `macro_data` | Macro indicators (GDP / CPI / PMI / M2 / LPR …) |
| `analysis` | Technical indicators, correlation, alignment |
| `search` | Code / name / pinyin / alias lookup |
| `meta` | Metadata & capability discovery |

Also exposed: resources (`entity_stats`, `large_data`, `stock_data`, `ui_apps`) and prompts (`stock_analysis`).

---

## Implementation path

At the heart of findatamcp is a three-layer contract: **tools produce data, the UI consumes it immersively, the LLM sees a terse summary**. The rest of this section walks the data flow end-to-end.

### 1. Envelope contract: content + structuredContent + meta

Every tool exits through `finalize_artifact_result` in `findatamcp/utils/artifact_payload.py`, producing a `ToolResult` with three carefully separated layers:

| Layer | Consumer | Contents |
| :--- | :--- | :--- |
| `content[0].text` | LLM | header + first 10 rows as markdown table + trailer ("UI rendered"/"N rows total"/"pass `as_file=True` for full data") |
| `structuredContent` | UI iframe / `execute` tool | The single source of truth: `row_count` / `columns=[{name,type}]` / `rows=[…]` / optional `date_range` / optional `path` / optional `download_urls` |
| `meta` | MCP host | `{ui: None}` to explicitly suppress UI rendering when `include_ui=False`; otherwise inherits the `ui://` registered via `app=AppConfig(...)` |

The LLM always sees concise text + guidance — never drowned in rows. The UI and downstream scripts consume `structuredContent.rows`. Both sides read from the same `rows` list, so no drift between preview and full data.

### 2. MCP UI: `ui://` resources + iframe postMessage

`findatamcp/resources/ui_apps.py` registers several `ui://findata/*` resources (`market-dashboard`, `kline-chart`, `moneyflow-chart`, `macro-panel`, `data-table`). Each returns a complete HTML document:

- **Zero CDN dependency** — `static/echarts.min.js` is read into memory at startup and inlined as a `<script>` tag. This satisfies the sandboxed iframe's CSP and works in air-gapped deployments.
- **Theme forwarding** — the HTML uses `light-dark()` CSS variables; when the host emits `ui/notifications/host-context-changed`, the iframe applies the new palette.
- **Four handshake messages** (protocol `2025-06-18`):
  - `ui/initialize` (host → iframe; iframe replies with `result.protocolVersion + appCapabilities`)
  - `ui/notifications/initialized` (iframe → host, signalling readiness)
  - `ui/notifications/tool-input` (host → iframe, carrying the tool arguments)
  - `ui/notifications/tool-result` (host → iframe, carrying `structuredContent` or `content`; the iframe parses and renders)

A tool only needs to declare the binding via `@mcp.tool(app=AppConfig(ui_uri="ui://findata/kline-chart"))` and the host forwards `structuredContent` to the matching iframe.

### 3. Large-data artifacts: JSONL + column-schema sidecar

By default (`as_file=False`) rows are embedded directly in `structuredContent.rows`. When the user asks to "export / save" or the LLM plans to call `execute` for further analysis, pass `as_file=True`:

1. `data_file_store.store(rows, tool_name, query_params)` (`findatamcp/cache/data_file_store.py`) writes rows to `.jsonl` — date and code columns forced to strings, `NaN → null`.
2. A column-schema sidecar (`{col: {"type": date|string|number|bool}}`) is dumped alongside, so downstream AG Grid can infer column types without scanning.
3. Returns a semantic filename (`get_historical_data_000300.SH_20260306_20260402.jsonl`) + `/workspace/<name>` path + `download_urls`.
4. With `include_ui=False` an extra `meta.ui = None` tells the host to skip rendering — typical when the LLM plans to plot itself with matplotlib and wants to avoid two competing charts.

### 4. LLM behaviour: preventing redundant calls

UI-rendering tools have a known failure mode: the LLM only reads `content.text` and doesn't realise the iframe has already drawn the chart, so it re-invokes "to check". `findatamcp/utils/ui_hint.py` and `artifact_payload.build_content_trailer` cooperate to pin four guidance lines at the tail of the text:

```
UI rendered (ui://findata/kline-chart).
Full 245 rows written to /workspace/xxx.jsonl.
The user can open it in the artifact panel; you may read it with execute for further analysis.
```

Tool docstrings also embed `AS_FILE_INCLUDE_UI_DECISION_GUIDE`, exposing the `as_file` / `include_ui` decision table directly to the model. In practice this materially cuts duplicate calls.

### 5. Dependency injection + tool registration

`server.py` wires a one-shot DI container at startup:

```python
api = TushareAPI(token, cache=tushare_cache)
db  = EntityStore.from_sqlite(db_path)
mcp = FastMCP("findatamcp")

register_market_tools(mcp, api)
register_financial_tools(mcp, api)
register_search_tools(mcp, api, db)
# … 12 register_*_tools calls
```

Each module's `register_*_tools(mcp, api, [db])` hangs its `@mcp.tool` / `@mcp.resource` / `@mcp.prompt` decorators on the FastMCP instance. Tests can swap `api` for a mock and `db` for an in-memory fixture.

### 6. Cache layering

| Layer | Location | Invalidation |
| :--- | :--- | :--- |
| Raw Tushare responses | `cache/tushare_cache.py` | Keyed by endpoint + param hash; TTL tuned per frequency |
| Computed results (alignment, indicators) | `cache/calc_cache.py` | Per-process LRU; cleared on restart |
| File artifacts (`.jsonl` + schema) | `cache/data_file_store.py` | 24h TTL, background sweep |

On the async front, Tushare's Python SDK is synchronous, so `TushareAPI` wraps every call in `asyncio.to_thread` — the FastMCP event loop never blocks on network I/O.

### 7. Entity search: EntityStore + pypinyin

Search tools regularly need to map "baijiu sector", "招商银行", or "平安" to concrete `ts_code` lists. `entity_store.py` loads the full security universe from SQLite into memory at startup:

- Primary index: `ts_code → entity`
- Inverted index: `name / pinyin-full / pinyin-initials / alias → set[ts_code]`
- Chinese names are pre-encoded with `pypinyin`, so "zsyh / 招行 / 招商银行" all resolve to the same code

Searches hit the in-memory index with a TF ranking, responses are sub-millisecond, and Tushare never gets called for lookups.

---

## Configuration

Common `.env` variables:

```bash
TUSHARE_TOKEN=your_token_here       # required
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8006
MCP_TRANSPORT=streamable-http        # or sse
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

## Testing

```bash
pytest tests/
```

Covers cache, data processing, market statistics, tool registration, SSE client, and end-to-end flows.

## Docs

- [docs/SSE_GUIDE.md](docs/SSE_GUIDE.md) — SSE deployment and client integration

## License

Tushare Pro data usage is subject to the [Tushare user agreement](https://tushare.pro/document/1). Code in this repo is released under MIT.
