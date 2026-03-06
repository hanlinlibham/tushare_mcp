"""大数据文件存储管理器

当工具返回数据超过阈值时，将数据存为文件并返回下载 URL。
支持 CSV (utf-8-sig) 和 JSON 双格式。
"""

import os
import json
import asyncio
import logging
from uuid import uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 存储目录
DATA_DIR = Path("/tmp/tushare_mcp_data")
# 文件过期时间
FILE_TTL_HOURS = 24
# 服务器基础 URL
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://39.96.218.64:8111")


@dataclass
class DataFileMeta:
    """数据文件元信息"""
    data_id: str
    tool_name: str
    query_params: Dict[str, Any]
    total_rows: int
    columns: List[str]
    csv_path: str
    json_path: str
    created_at: str
    expires_at: str


class DataFileStore:
    """数据文件存储单例"""

    _instance: Optional["DataFileStore"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._index: Dict[str, DataFileMeta] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        # 确保存储目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"DataFileStore initialized, dir={DATA_DIR}")

    def store(
        self,
        rows: List[Dict[str, Any]],
        tool_name: str,
        query_params: Dict[str, Any],
    ) -> DataFileMeta:
        """将数据写入 CSV + JSON 文件，返回元信息"""
        data_id = uuid4().hex[:12]
        now = datetime.now()
        expires = now + timedelta(hours=FILE_TTL_HOURS)

        csv_path = str(DATA_DIR / f"{data_id}.csv")
        json_path = str(DATA_DIR / f"{data_id}.json")

        columns = list(rows[0].keys()) if rows else []

        # 写 CSV (utf-8-sig for Excel)
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

        # 写 JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, default=str)

        meta = DataFileMeta(
            data_id=data_id,
            tool_name=tool_name,
            query_params=query_params,
            total_rows=len(rows),
            columns=columns,
            csv_path=csv_path,
            json_path=json_path,
            created_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )
        self._index[data_id] = meta
        logger.info(f"Stored {len(rows)} rows as {data_id} ({tool_name})")
        return meta

    def get(self, data_id: str) -> Optional[DataFileMeta]:
        """获取文件元信息，过期则返回 None"""
        meta = self._index.get(data_id)
        if meta is None:
            return None
        if datetime.now() > datetime.fromisoformat(meta.expires_at):
            self._remove(data_id)
            return None
        return meta

    def _remove(self, data_id: str):
        """删除文件和索引"""
        meta = self._index.pop(data_id, None)
        if meta:
            for p in (meta.csv_path, meta.json_path):
                try:
                    os.remove(p)
                except OSError:
                    pass

    def cleanup_expired(self):
        """清理所有过期文件"""
        now = datetime.now()
        expired = [
            did for did, m in self._index.items()
            if now > datetime.fromisoformat(m.expires_at)
        ]
        for did in expired:
            self._remove(did)
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired data files")

    async def start_cleanup_loop(self):
        """启动后台清理循环（每小时一次）"""
        if self._cleanup_task is not None:
            return
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("DataFileStore cleanup loop started")

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(3600)
            self.cleanup_expired()

    def get_download_urls(self, data_id: str) -> Dict[str, str]:
        """生成下载 URL"""
        base = SERVER_BASE_URL.rstrip("/")
        return {
            "csv": f"{base}/data/{data_id}.csv",
            "json": f"{base}/data/{data_id}.json",
        }


# 全局单例
data_file_store = DataFileStore()
