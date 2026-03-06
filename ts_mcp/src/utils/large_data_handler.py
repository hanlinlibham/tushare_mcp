"""大数据分流处理

当工具返回行数 > THRESHOLD 时，自动存文件并返回摘要 + 下载 URL。
"""

import logging
from typing import Dict, List, Any, Optional, Callable

from ..cache.data_file_store import data_file_store

logger = logging.getLogger(__name__)

THRESHOLD = 100  # 行数阈值


def _build_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """自动生成数值列统计 + 日期范围"""
    summary: Dict[str, Any] = {}

    if not rows:
        return summary

    keys = rows[0].keys()

    # 检测日期列
    date_cols = [k for k in keys if "date" in k.lower()]
    for col in date_cols:
        vals = [r[col] for r in rows if r.get(col)]
        if vals:
            summary["date_range"] = f"{min(vals)} ~ {max(vals)}"
            break

    # 数值列统计
    for col in keys:
        if col in date_cols or col in ("ts_code", "index_code", "con_code", "con_name", "trade_date"):
            continue
        # 尝试提取数值
        nums = []
        for r in rows:
            v = r.get(col)
            if v is not None:
                try:
                    nums.append(float(v))
                except (ValueError, TypeError):
                    break
        if len(nums) > len(rows) * 0.5:  # 至少一半行有数值
            summary[col] = {
                "latest": round(nums[-1], 4),
                "min": round(min(nums), 4),
                "max": round(max(nums), 4),
                "mean": round(sum(nums) / len(nums), 4),
            }

    return summary


def handle_large_data(
    rows: List[Dict[str, Any]],
    tool_name: str,
    query_params: Dict[str, Any],
    summary_builder: Optional[Callable] = None,
    preview_rows: int = 5,
) -> Dict[str, Any]:
    """大数据分流：小数据 inline，大数据存文件返回摘要。

    Args:
        rows: 数据行列表 (list of dicts)
        tool_name: 工具名称
        query_params: 查询参数 (用于元信息)
        summary_builder: 自定义摘要生成函数，签名 (rows) -> dict
        preview_rows: 预览行数

    Returns:
        适合直接作为工具返回值的 dict
    """
    total = len(rows)

    if total <= THRESHOLD:
        # 小数据，直接返回
        return {"data": rows, "total_rows": total}

    # 大数据：存文件
    meta = data_file_store.store(rows, tool_name, query_params)
    urls = data_file_store.get_download_urls(meta.data_id)

    # 摘要
    if summary_builder:
        summary = summary_builder(rows)
    else:
        summary = _build_summary(rows)

    return {
        "total_rows": total,
        "is_truncated": True,
        "message": f"数据量较大({total}行)，已存为文件。请通过以下链接下载完整数据。",
        "download_urls": urls,
        "preview": rows[:preview_rows],
        "summary": summary,
        "expires_in": "24小时",
    }
