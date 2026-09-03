"""数据引擎属性测试。"""

import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from hypothesis import given
from hypothesis import settings as h_settings
from hypothesis import strategies as st

from sequoia_x.core.config import Settings
from sequoia_x.data.engine import DataEngine


def make_engine_in(tmp_dir: str) -> tuple[DataEngine, Settings]:
    """创建使用临时数据库的 DataEngine 实例。"""
    settings = Settings(
        db_path=str(Path(tmp_dir) / "test.db"),
        start_date="2024-01-01",
        feishu_webhook_url="https://example.com/hook",
    )
    engine = DataEngine(settings)
    return engine, settings


# Property 4: (symbol, date) 唯一约束防止重复写入
@given(
    symbol=st.text(min_size=6, max_size=6, alphabet="0123456789"),
    trade_date=st.dates(min_value=date(2024, 1, 1), max_value=date(2025, 12, 31)),
)
@h_settings(max_examples=50, deadline=None)
def test_unique_symbol_date_constraint(symbol: str, trade_date: date) -> None:
    """相同 (symbol, date) 插入两次，数据库中该组合记录数应保持为 1。"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine, _ = make_engine_in(tmp_dir)
        row = {
            "symbol": symbol, "date": str(trade_date),
            "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5,
            "volume": 1000.0, "turnover": 10500.0,
        }
        df = pd.DataFrame([row])
        with sqlite3.connect(engine.db_path) as conn:
            df.to_sql("stock_daily", conn, if_exists="append", index=False, method="multi")
            try:
                df.to_sql("stock_daily", conn, if_exists="append", index=False, method="multi")
            except sqlite3.IntegrityError:
                pass
            count = conn.execute(
                "SELECT COUNT(*) FROM stock_daily WHERE symbol=? AND date=?",
                (symbol, str(trade_date)),
            ).fetchone()[0]
        assert count == 1


def test_sync_today_bulk_preserves_other_symbols_on_same_date(tmp_path: Path) -> None:
    """增量同步部分股票时，不应删除其他股票当天已有的数据。"""
    engine, _ = make_engine_in(str(tmp_path))
    today = date.today()
    yesterday = today - timedelta(days=1)

    conn = sqlite3.connect(engine.db_path)
    try:
        conn.executemany(
            """INSERT INTO stock_daily
            (symbol, date, open, high, low, close, volume, turnover)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                ("000001", str(today), 10, 11, 9, 10.5, 1000, 10500),
                ("000002", str(yesterday), 20, 21, 19, 20.5, 2000, 41000),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    fetched_rows = [
        ["000002", str(today), "21", "22", "20", "21.5", "2100", "45150"]
    ]

    with patch("multiprocessing.Pool") as pool_class:
        pool_class.return_value.__enter__.return_value.map.return_value = [fetched_rows]
        assert engine.sync_today_bulk() == 1

    conn = sqlite3.connect(engine.db_path)
    try:
        current_symbols = conn.execute(
            "SELECT symbol FROM stock_daily WHERE date = ? ORDER BY symbol",
            (str(today),),
        ).fetchall()
    finally:
        conn.close()

    assert current_symbols == [("000001",), ("000002",)]
