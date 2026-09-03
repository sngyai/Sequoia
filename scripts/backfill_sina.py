"""新浪数据源回填脚本 —— 绕开 baostock 风控。

背景
----
并发拉 baostock 会触发风控，返回 `10001011 黑名单用户`，整个 IP 被拉黑，
官方 `main.py --backfill` 和 `sync_today_bulk` 都会失效。
本脚本改用 akshare 的新浪接口（`stock_zh_a_daily`），把数据灌进**同一个库**
`data/sequoia_v2.db` 的 `stock_daily` 表，灌完后 `python main.py` 可直接跑策略。

为什么选新浪而不是东财
----------------------
- 东财域名（push2his / 82.push2.eastmoney.com）在本机代理环境下被掐断，成功率 0。
- 新浪源实测 8/8 稳定成功。
- **成交量单位与 baostock 一致（都是「股」）**：600000 在 2026-09-02
  baostock volume=67036450，新浪 volume=67036450，amount 也一致。无需换算。

⚠️ 唯一差异：后复权基准
------------------------
新浪与 baostock 的后复权价格数值不同（600000 在 2026-09-02：
baostock 后复权收盘 124.05，新浪 161.39）。原因是两家的除权因子基准不同。
**绝对价格不同，但同一只股票内部的形态、均线、突破关系是等比一致的，
策略（新高突破 / 均线 / 涨幅排序）结论不受影响。**

但**不能混用**：如果库里已有 baostock 数据，切到新浪必须加 `--reset` 清空重灌，
否则同一只股票前后两段价格跳变，均线和突破判断会失真。

用法
----
    # 首次切换到新浪：清空旧数据后全量重灌（推荐）
    .venv\\Scripts\\python.exe scripts/backfill_sina.py --reset

    # 日常增量：只补缺失日期，可代替 main.py 的 sync_today_bulk
    .venv\\Scripts\\python.exe scripts/backfill_sina.py

    # 先跑 30 只验证
    .venv\\Scripts\\python.exe scripts/backfill_sina.py --limit 30 --reset

    # 指定代码补漏
    .venv\\Scripts\\python.exe scripts/backfill_sina.py --symbols 600000,000001

参数
----
--reset    清空 stock_daily 后全量重灌
--workers  并发线程数（默认 4；调太高可能被新浪限流）
--limit    只处理前 N 只（调试用）
--retries  单只失败重试次数（默认 5）
--symbols  逗号分隔代码，指定后跳过全市场列表获取
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import sqlite3
import sys
import threading
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sequoia_x.core.config import get_settings  # noqa: E402

_LOCK = threading.Lock()
_COUNTER = {"done": 0, "rows": 0, "fail": 0}


def _to_sina_code(symbol: str) -> str:
    """纯数字代码转新浪格式：6/9 -> sh，4/8 -> bj，其余 -> sz。"""
    if symbol.startswith(("6", "9")):
        return f"sh{symbol}"
    if symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    return f"sz{symbol}"


def _fetch_one(symbol: str, start: str, end: str, retries: int = 5) -> list[tuple]:
    """拉取单只股票日 K（后复权），带重试退避。返回待写入行。"""
    import akshare as ak

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            df = ak.stock_zh_a_daily(
                symbol=_to_sina_code(symbol),
                start_date=start.replace("-", ""),
                end_date=end.replace("-", ""),
                adjust="hfq",
            )
            break
        except Exception as exc:  # noqa: BLE001 - 网络异常类型不可控
            last_err = exc
            if attempt < retries - 1:
                time.sleep(1.5 ** (attempt + 1))
    else:
        raise RuntimeError(f"{symbol} 重试 {retries} 次仍失败：{last_err}")

    if df is None or df.empty:
        return []

    rows: list[tuple] = []

    def f(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    # 注意：日期取自 'date' 列，不是 df.index（index 是整数 RangeIndex）
    for rec in df.to_dict("records"):
        d = rec.get("date")
        d = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        if len(d) != 10:
            continue
        close = f(rec.get("close"))
        volume = f(rec.get("volume"))
        if close is None or volume is None or volume <= 0:
            continue
        rows.append(
            (
                symbol,
                d,
                f(rec.get("open")),
                f(rec.get("high")),
                f(rec.get("low")),
                close,
                volume,
                f(rec.get("amount")),
                f(rec.get("outstanding_share")),  # 流通股本(股)，用于市值估算
            )
        )
    return rows


def _write(db_path: str, rows: list[tuple]) -> int:
    if not rows:
        return 0
    with sqlite3.connect(db_path, timeout=30) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO stock_daily "
            "(symbol, date, open, high, low, close, volume, turnover, outstanding_share) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def _worker(task: tuple[str, str, str, int]) -> list[tuple]:
    """多进程 worker：串行处理一批股票，返回结果行。

    ⚠️ 必须用多进程而非多线程：akshare 的新浪接口内部调用 py_mini_racer
    （内嵌 V8 引擎），该 DLL 非线程安全，多线程并发会直接段错误崩溃。
    """
    symbol, start, end, retries = task
    try:
        return _fetch_one(symbol, start, end, retries)
    except Exception as exc:  # noqa: BLE001
        print(f"[{symbol}] 失败：{exc}", flush=True)
        return []


def _run_chunk(chunk: list[tuple]) -> list[tuple]:
    """模块级函数（multiprocessing spawn 需要可 pickle）：串行跑一批。"""
    out: list[tuple] = []
    for t in chunk:
        out.extend(_worker(t))
    return out


def _get_symbols(retries: int = 4) -> list[str]:
    """全市场 A 股代码，过滤沪深（6/0/3 开头），与 baostock 口径一致。"""
    import akshare as ak

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            df = ak.stock_info_a_code_name()
            codes = [str(c).zfill(6) for c in df["code"].tolist()]
            return [c for c in codes if c.startswith(("6", "0", "3"))]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(1.5 ** (attempt + 1))
    raise RuntimeError(f"获取股票列表失败：{last_err}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sequoia-X 新浪数据源回填")
    parser.add_argument("--reset", action="store_true", help="清空 stock_daily 后全量重灌")
    parser.add_argument("--workers", type=int, default=4, help="并发线程数（默认 4）")
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 只（调试用）")
    parser.add_argument("--retries", type=int, default=5, help="单只失败重试次数（默认 5）")
    parser.add_argument(
        "--symbols",
        default="",
        help="逗号分隔的股票代码，指定后跳过全市场列表获取",
    )
    args = parser.parse_args()

    settings = get_settings()
    db_path = settings.db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL, date TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL,
                volume REAL, turnover REAL, outstanding_share REAL,
                UNIQUE (symbol, date))"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_date ON stock_daily (symbol, date)"
        )
        # 老库兼容：补加流通股本列（已存在的库不会因 IF NOT EXISTS 自动加）
        try:
            conn.execute("ALTER TABLE stock_daily ADD COLUMN outstanding_share REAL")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # 列已存在
        conn.commit()
        if args.reset:
            conn.execute("DELETE FROM stock_daily")
            conn.commit()
            print("已清空 stock_daily")
        done = dict(
            conn.execute("SELECT symbol, MAX(date) FROM stock_daily GROUP BY symbol").fetchall()
        )

    end_date = date.today().strftime("%Y-%m-%d")
    if args.symbols:
        symbols = [s.strip().zfill(6) for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = _get_symbols()
    if args.limit:
        symbols = symbols[: args.limit]
    print(f"候选 {len(symbols)} 只，库内已有 {len(done)} 只", flush=True)

    tasks: list[tuple[str, str]] = []
    for symbol in symbols:
        last = done.get(symbol)
        if last and last >= end_date:
            continue
        start = settings.start_date
        if last:
            start = (date.fromisoformat(last) + timedelta(days=1)).strftime("%Y-%m-%d")
        tasks.append((symbol, start))

    if not tasks:
        print("全部已是最新，无需回填")
        return

    full_tasks = [(s, st, end_date, args.retries) for s, st in tasks]

    print(f"待处理 {len(tasks)} 只，开始拉取...", flush=True)
    t0 = time.time()
    total = len(tasks)

    chunk_size = 25
    chunks = [full_tasks[i : i + chunk_size] for i in range(0, len(full_tasks), chunk_size)]
    workers = min(args.workers, len(chunks))

    with mp.Pool(workers) as pool:
        for rows in pool.imap_unordered(_run_chunk, chunks):
            _write(db_path, rows)
            with _LOCK:
                _COUNTER["done"] = min(_COUNTER["done"] + chunk_size, total)
                _COUNTER["rows"] += len(rows)
                d, r = _COUNTER["done"], _COUNTER["rows"]
            elapsed = time.time() - t0
            speed = d / elapsed if elapsed else 0
            eta = (total - d) / speed if speed else 0
            print(
                f"{d}/{total} ({d / total * 100:.1f}%) | 累计 {r} 行 | "
                f"{speed:.1f} 只/秒 | 剩余 {eta / 60:.1f} 分钟",
                flush=True,
            )

    print(
        f"完成：{_COUNTER['done']} 只，{_COUNTER['rows']} 行，"
        f"失败 {_COUNTER['fail']} 只，耗时 {(time.time() - t0) / 60:.1f} 分钟"
    )
    if _COUNTER["fail"]:
        print("提示：失败多为网络抖动，直接重跑本脚本即可续传")


if __name__ == "__main__":
    main()
