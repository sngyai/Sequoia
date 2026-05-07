"""Web 服务层：桥接现有 engine/settings/strategies 到 Web API。"""

import collections
import logging
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

import pandas as pd

from sequoia_x.core.config import Settings
from sequoia_x.data.engine import DataEngine
from sequoia_x.strategy.base import BaseStrategy
from sequoia_x.strategy.high_tight_flag import HighTightFlagStrategy
from sequoia_x.strategy.limit_up_shakeout import LimitUpShakeoutStrategy
from sequoia_x.strategy.ma_volume import MaVolumeStrategy
from sequoia_x.strategy.rps_breakout import RpsBreakoutStrategy
from sequoia_x.strategy.turtle_trade import TurtleTradeStrategy
from sequoia_x.strategy.uptrend_limit_down import UptrendLimitDownStrategy


# ---------------------------------------------------------------------------
# Strategy registry & metadata
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    cls.webhook_key: cls
    for cls in [
        MaVolumeStrategy,
        TurtleTradeStrategy,
        HighTightFlagStrategy,
        LimitUpShakeoutStrategy,
        UptrendLimitDownStrategy,
        RpsBreakoutStrategy,
    ]
}

STRATEGY_META: dict[str, dict] = {
    "ma_volume": {
        "name": "MaVolume",
        "name_cn": "均线放量",
        "description": "5日均线上穿20日均线（金叉）且成交量放大1.5倍",
        "min_bars": 20,
    },
    "turtle": {
        "name": "TurtleTrade",
        "name_cn": "海龟突破",
        "description": "20日新高突破 + 成交额过亿 + 阳线防诱多",
        "min_bars": 21,
    },
    "flag": {
        "name": "HighTightFlag",
        "name_cn": "高位旗形",
        "description": "40日涨幅>60% + 10日窄幅震荡 + 缩量整理",
        "min_bars": 40,
    },
    "shakeout": {
        "name": "LimitUpShakeout",
        "name_cn": "涨停洗盘",
        "description": "昨日涨停 + 今日阴线放量 + 不破涨停支撑",
        "min_bars": 5,
    },
    "limit_down": {
        "name": "UptrendLimitDown",
        "name_cn": "上升趋势跌停",
        "description": "MA20>MA60上升趋势 + 今日跌停 + 放量",
        "min_bars": 60,
    },
    "rps": {
        "name": "RpsBreakout",
        "name_cn": "RPS相对强度",
        "description": "120日涨幅排名前10% + 接近120日新高",
        "min_bars": 120,
    },
}


# ---------------------------------------------------------------------------
# Background task tracking
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class TaskRecord:
    task_id: str
    strategy_key: str
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    results: list[str] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Log ring buffer handler
# ---------------------------------------------------------------------------

class RingBufferHandler(logging.Handler):
    """自定义 logging handler，将日志存入环形缓冲区。"""

    def __init__(self, maxlen: int = 500):
        super().__init__()
        self.buffer: collections.deque[str] = collections.deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append(self.format(record))


# ---------------------------------------------------------------------------
# Xueqiu code helper (reused from feishu.py)
# ---------------------------------------------------------------------------

def _to_xueqiu_code(code: str) -> str:
    if code.startswith("6"):
        return f"SH{code}"
    elif code.startswith(("4", "8")):
        return f"BJ{code}"
    return f"SZ{code}"


# ---------------------------------------------------------------------------
# WebServices
# ---------------------------------------------------------------------------

class WebServices:
    """桥接 Web 层到现有 DataEngine / Settings / strategies。"""

    def __init__(self, settings: Settings, engine: DataEngine) -> None:
        self.settings = settings
        self.engine = engine
        self._task_store: dict[str, TaskRecord] = {}
        self._result_cache: dict[str, list[str]] = {}
        self._executor = ThreadPoolExecutor(max_workers=2)

    # -- Strategy methods --

    def list_strategies(self) -> list[dict]:
        result = []
        for key, meta in STRATEGY_META.items():
            webhook_url = self.settings.get_webhook_url(key)
            result.append({
                "key": key,
                "name": meta["name"],
                "name_cn": meta["name_cn"],
                "description": meta["description"],
                "min_bars": meta["min_bars"],
                "webhook_key": key,
                "webhook_url": webhook_url,
                "latest_result_count": len(self._result_cache.get(key, [])),
                "last_run_at": None,
            })
        return result

    def get_strategy_class(self, key: str) -> type[BaseStrategy] | None:
        return STRATEGY_REGISTRY.get(key)

    def run_strategy_async(self, key: str) -> str:
        task_id = uuid.uuid4().hex[:8]
        record = TaskRecord(task_id=task_id, strategy_key=key)
        self._task_store[task_id] = record
        self._executor.submit(self._run_strategy_task, task_id, key)
        return task_id

    def _run_strategy_task(self, task_id: str, key: str) -> None:
        record = self._task_store[task_id]
        record.status = TaskStatus.RUNNING
        record.started_at = datetime.now()
        try:
            cls = STRATEGY_REGISTRY[key]
            strategy = cls(engine=self.engine, settings=self.settings)
            results = strategy.run()
            record.results = results
            record.status = TaskStatus.DONE
            self._result_cache[key] = results
        except Exception as e:
            record.status = TaskStatus.ERROR
            record.error = str(e)
        finally:
            record.finished_at = datetime.now()

    def get_task_status(self, task_id: str) -> TaskRecord | None:
        return self._task_store.get(task_id)

    def get_cached_results(self, key: str) -> list[str]:
        return self._result_cache.get(key, [])

    # -- Data sync methods --

    def sync_data_async(self) -> str:
        task_id = uuid.uuid4().hex[:8]
        record = TaskRecord(task_id=task_id, strategy_key="__sync__")
        self._task_store[task_id] = record
        self._executor.submit(self._sync_data_task, task_id)
        return task_id

    def _sync_data_task(self, task_id: str) -> None:
        record = self._task_store[task_id]
        record.status = TaskStatus.RUNNING
        record.started_at = datetime.now()
        try:
            count = self.engine.sync_today_bulk()
            record.results = [f"synced:{count}"]
            record.status = TaskStatus.DONE
        except Exception as e:
            record.status = TaskStatus.ERROR
            record.error = str(e)
        finally:
            record.finished_at = datetime.now()

    def backfill_async(self) -> str:
        task_id = uuid.uuid4().hex[:8]
        record = TaskRecord(task_id=task_id, strategy_key="__backfill__")
        self._task_store[task_id] = record
        self._executor.submit(self._backfill_task, task_id)
        return task_id

    def _backfill_task(self, task_id: str) -> None:
        record = self._task_store[task_id]
        record.status = TaskStatus.RUNNING
        record.started_at = datetime.now()
        try:
            all_symbols = self.engine.get_all_symbols()
            self.engine.backfill(all_symbols)
            record.status = TaskStatus.DONE
        except Exception as e:
            record.status = TaskStatus.ERROR
            record.error = str(e)
        finally:
            record.finished_at = datetime.now()

    # -- Stock data methods --

    def search_symbols(self, query: str, limit: int = 20) -> list[str]:
        with sqlite3.connect(self.engine.db_path, timeout=5) as conn:
            rows = conn.execute(
                "SELECT DISTINCT symbol FROM stock_daily WHERE symbol LIKE ? ORDER BY symbol LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
        return [r[0] for r in rows]

    def get_stock_data(self, symbol: str, days: int = 120) -> list[dict]:
        df = self.engine.get_ohlcv(symbol)
        if df.empty:
            return []
        df = df.sort_values("date").tail(days)
        return df[["date", "open", "high", "low", "close", "volume", "turnover"]].to_dict("records")

    def get_stock_summary(self, symbol: str) -> dict | None:
        df = self.engine.get_ohlcv(symbol)
        if df.empty:
            return None
        df = df.sort_values("date")
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        change_pct = round((latest["close"] - prev["close"]) / prev["close"] * 100, 2) if prev["close"] else 0
        return {
            "symbol": symbol,
            "latest_close": round(latest["close"], 2),
            "latest_date": latest["date"],
            "change_pct": change_pct,
            "total_rows": len(df),
            "date_range": [df.iloc[0]["date"], df.iloc[-1]["date"]],
            "xueqiu_code": _to_xueqiu_code(symbol),
        }

    # -- System methods --

    def get_system_info(self) -> dict:
        db_path = self.engine.db_path
        db_size_mb = round(Path(db_path).stat().st_size / 1024 / 1024, 2) if Path(db_path).exists() else 0
        with sqlite3.connect(db_path, timeout=5) as conn:
            total_rows = conn.execute("SELECT COUNT(*) FROM stock_daily").fetchone()[0]
            distinct_symbols = conn.execute("SELECT COUNT(DISTINCT symbol) FROM stock_daily").fetchone()[0]
            last_date = conn.execute("SELECT MAX(date) FROM stock_daily").fetchone()[0]
        return {
            "db_path": db_path,
            "db_size_mb": db_size_mb,
            "total_rows": total_rows,
            "distinct_symbols": distinct_symbols,
            "last_sync_date": last_date or "N/A",
        }

    def get_recent_logs(self, handler: RingBufferHandler, limit: int = 100) -> list[str]:
        items = list(handler.buffer)
        return items[-limit:]
