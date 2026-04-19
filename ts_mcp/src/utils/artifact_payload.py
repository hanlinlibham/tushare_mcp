"""带 UI resource 的 MCP 工具统一 payload 构造器

支持 as_file / include_ui 两个语义开关，四种组合行为：
  as_file=False, include_ui=True  → 原默认：UI iframe + structuredContent preview
  as_file=True,  include_ui=True  → UI + .jsonl 文件 path
  as_file=True,  include_ui=False → 只 .jsonl 文件，无 UI
  as_file=False, include_ui=False → 只 preview，无 UI 无文件
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..cache.data_file_store import data_file_store, infer_schema


def _safe_name(s: str) -> str:
    """文件名安全化：非字母数字/./-/_ 替为下划线。"""
    return re.sub(r"[^0-9A-Za-z_.-]", "_", s).strip("_.") or "data"


_FILENAME_PRIORITY_KEYS = (
    "ts_code", "stock_code", "index_code", "fund_code", "symbol", "code",
    "start_date", "end_date", "trade_date", "period", "indicator",
)


def build_semantic_filename(tool_name: str, query_params: Dict[str, Any]) -> str:
    """语义化文件名：tool_name + 关键参数 + 日期范围。带 .jsonl 扩展。

    例：get_historical_data_600519.SH_20240101_20240331.jsonl
    """
    parts: List[str] = [_safe_name(tool_name)]
    for k in _FILENAME_PRIORITY_KEYS:
        v = query_params.get(k)
        if v is None or v == "":
            continue
        parts.append(_safe_name(str(v)))
    return "_".join(parts) + ".jsonl"


def build_preview(rows: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    """前 limit 行预览，永远返回 list of dict（不转 CSV 字符串）。"""
    if not rows:
        return []
    if len(rows) <= limit:
        return list(rows)
    return list(rows[:limit])


def build_llm_hint(
    *,
    ui_uri: Optional[str],
    row_count: int,
    path: Optional[str],
) -> str:
    """按 as_file / include_ui 四种组合给 agent 不同的下一步引导。"""
    if ui_uri and not path:
        return (
            f"📊 已渲染到前端: {ui_uri}\n"
            f"📦 数据预览: structuredContent.rows_preview（共 {row_count} 行，前 20 行）\n"
            f"💡 如需完整数据文件做后续分析/导出，重新调用并设 as_file=True"
        )
    if ui_uri and path:
        return (
            f"📊 已渲染到前端: {ui_uri}\n"
            f"📁 完整数据文件: {path}（共 {row_count} 行）\n"
            f"💡 用户可在 artifact 面板打开此文件交互查看；你也可以用 execute 工具读此文件做进一步分析"
        )
    if (ui_uri is None) and path:
        return (
            f"📁 数据文件已写入: {path}（共 {row_count} 行）\n"
            f"💡 无内嵌 UI。你可以用 execute + matplotlib/plotly 绘图，或直接返回文件让用户在 artifact 面板查看"
        )
    return (
        f"📦 数据预览: structuredContent.rows_preview（共 {row_count} 行）\n"
        f"💡 无 UI 也无文件。如需完整数据，重新调用并设 as_file=True"
    )


def build_artifact_fields(
    rows: List[Dict[str, Any]],
    *,
    tool_name: str,
    query_params: Dict[str, Any],
    ui_uri: str,
    as_file: bool,
    include_ui: bool,
    preview_limit: int = 20,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """返回要合并进 structuredContent 的字段 + hint + meta override。

    返回 dict 的 keys（消费方自行拼装 ToolResult / dict 返回）：
        row_count       : int
        columns         : list[str]
        rows_preview    : list[dict]  ≤ preview_limit 行
        schema          : {col: {type: date|string|number|bool}}
        path            : str         仅 as_file=True；形如 /workspace/xxx.jsonl
        download_urls   : dict        仅 as_file=True；{jsonl, json} HTTP URL
        _llm_hint       : str         下一步引导文案
        _meta_override  : dict | None include_ui=False 时 {'ui': None}（供调用方给 ToolResult(meta=...)）
    """
    columns = list(rows[0].keys()) if rows else []
    schema = infer_schema(rows, columns)
    preview = build_preview(rows, preview_limit)
    row_count = len(rows)

    fields: Dict[str, Any] = {
        "row_count": row_count,
        "columns": columns,
        "rows_preview": preview,
        "schema": schema,
    }

    path: Optional[str] = None
    if as_file and rows:
        meta = data_file_store.store(rows, tool_name, query_params)
        urls = data_file_store.get_download_urls(meta.data_id)
        semantic = filename or build_semantic_filename(tool_name, query_params)
        path = f"/workspace/{semantic}"
        fields["path"] = path
        fields["download_urls"] = urls

    fields["_llm_hint"] = build_llm_hint(
        ui_uri=ui_uri if include_ui else None,
        row_count=row_count,
        path=path,
    )
    # 给调用方的 meta override：include_ui=False 时让 ToolResult 显式塞 {'ui': None}
    fields["_meta_override"] = {"ui": None} if not include_ui else None
    return fields


AS_FILE_INCLUDE_UI_DECISION_GUIDE = """

【as_file / include_ui 决策指南】
默认（as_file=False, include_ui=True）：用户只是"看看走势"，UI iframe 足以回答问题。
何时设 as_file=True（把数据写成 .jsonl 文件）：
  - 用户明确要求"保存 / 导出 / 下载"数据
  - 你计划用 execute 工具对数据做自定义分析（聚合成月线、多标的对比、计算指标）
  - 用户目标超出内嵌 UI 范围（5 年以上月线、多资产对比）
  - 用户要求以表格形式查看并交互（排序、筛选）
何时设 include_ui=False（跳过内嵌 UI）：
  - 你已决定 as_file=True 并打算自己绘图——避免两张图混淆
  - 用户只需要数据做逻辑判断，不需要可视化
"""
