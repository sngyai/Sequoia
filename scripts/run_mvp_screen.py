"""MVP screen wrapper for Sequoia-X.

This script keeps the original strategy logic untouched. It only updates local
data, runs the four Phase 1 strategies, merges their symbol outputs, applies
pass/fail labels, and writes the required CSV/Markdown outputs.
"""

from __future__ import annotations

import argparse
import csv
import os
import socket
import sqlite3
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


socket.setdefaulttimeout(10.0)

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sequoia_x.core.config import Settings
from sequoia_x.data.engine import DataEngine
from sequoia_x.strategy.high_tight_flag import HighTightFlagStrategy
from sequoia_x.strategy.ma_volume import MaVolumeStrategy
from sequoia_x.strategy.rps_breakout import RpsBreakoutStrategy
from sequoia_x.strategy.turtle_trade import TurtleTradeStrategy


OUTPUT_DIR = ROOT_DIR / "outputs"
DAILY_CANDIDATES_PATH = OUTPUT_DIR / "daily_candidates.csv"
SIGNAL_TRACKING_PATH = OUTPUT_DIR / "signal_tracking.csv"
EXIT_LOG_PATH = OUTPUT_DIR / "exit_log.csv"
DATA_HEALTH_PATH = OUTPUT_DIR / "data_health.csv"
EXIT_ALERTS_PATH = OUTPUT_DIR / "exit_alerts.csv"
DAILY_REPORT_PATH = OUTPUT_DIR / "daily_report.md"
REVIEW_SUMMARY_PATH = OUTPUT_DIR / "review_summary.csv"

STRATEGIES = [
    ("RpsBreakout", RpsBreakoutStrategy),
    ("TurtleTrade", TurtleTradeStrategy),
    ("MaVolume", MaVolumeStrategy),
    ("HighTightFlag", HighTightFlagStrategy),
]

STRATEGY_ORDER = [name for name, _ in STRATEGIES]

DAILY_COLUMNS = [
    "trade_date",
    "code",
    "name",
    "close",
    "strategy_hit",
    "priority_tag",
    "turnover",
    "volume",
    "one_lot_cost",
    "affordable_flag",
    "price_bucket",
    "passed_price_filter",
    "market_board",
    "account_accessible_flag",
    "market_access_fail_reason",
    "fundamental_passed",
    "fundamental_fail_reason",
    "fundamental_data_status",
    "pe_ttm",
    "pb",
    "roe",
    "debt_ratio",
    "filter_fail_reason",
]

SIGNAL_COLUMNS = [
    "selected_date",
    "code",
    "name",
    "selected_close",
    "strategy_hit",
    "priority_tag",
    "price_bucket",
    "one_lot_cost",
    "market_board",
    "account_accessible_flag",
    "market_access_fail_reason",
    "fundamental_passed",
    "fundamental_fail_reason",
    "fundamental_data_status",
    "pe_ttm",
    "pb",
    "roe",
    "debt_ratio",
    "market_gate_status",
    "passed_hard_filter",
    "filter_fail_reason",
    "actual_trade_flag",
    "actual_buy_price",
    "actual_sell_price",
    "close_t1",
    "close_t3",
    "close_t5",
    "return_t1",
    "return_t3",
    "return_t5",
    "max_drawdown_5d",
    "notes",
]

EXIT_COLUMNS = [
    "buy_date",
    "code",
    "name",
    "buy_price",
    "buy_reason",
    "initial_stop_price",
    "exit_date",
    "exit_price",
    "exit_reason",
    "exit_attempted_flag",
    "holding_days",
    "return_pct",
    "notes",
]

DATA_HEALTH_COLUMNS = [
    "generated_at",
    "code",
    "name",
    "row_count",
    "first_date",
    "latest_date",
    "market_latest_date",
    "is_latest",
    "data_health_status",
    "notes",
]

EXIT_ALERT_COLUMNS = [
    "alert_date",
    "code",
    "name",
    "buy_date",
    "buy_price",
    "initial_stop_price",
    "latest_date",
    "latest_close",
    "adjusted_close",
    "ma20",
    "hard_stop_triggered",
    "trend_stop_triggered",
    "exit_priority",
    "exit_attempted_flag",
    "notes",
]

MANUAL_SIGNAL_COLUMNS = [
    "actual_trade_flag",
    "actual_buy_price",
    "actual_sell_price",
    "close_t1",
    "close_t3",
    "close_t5",
    "return_t1",
    "return_t3",
    "return_t5",
    "max_drawdown_5d",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sequoia-X Phase 1 MVP screen")
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Force a historical backfill before running strategies.",
    )
    parser.add_argument(
        "--backfill-only",
        action="store_true",
        help="Only backfill missing K-line data and refresh data_health.csv.",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip baostock data sync and run strategies on the local SQLite data.",
    )
    parser.add_argument(
        "--skip-fundamentals",
        action="store_true",
        help="Skip AKShare fundamentals and mark fundamental fields as pending.",
    )
    return parser.parse_args()


def make_settings() -> Settings:
    return Settings(
        db_path=str(ROOT_DIR / "data" / "sequoia_v2.db"),
        feishu_webhook_url="mvp-local-only",
    )


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def format_number(value: Any, digits: int = 4) -> str:
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    text = f"{number:.{digits}f}"
    return text.rstrip("0").rstrip(".")


def to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def quiet_call(func: Any, *args: Any, **kwargs: Any) -> Any:
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return func(*args, **kwargs)


def update_data(engine: DataEngine, *, force_backfill: bool, skip_sync: bool) -> str:
    if skip_sync:
        return "skipped"

    local_symbols = engine.get_local_symbols()
    if force_backfill or not local_symbols:
        return parallel_backfill(engine)

    count = engine.sync_today_bulk()
    return f"incremental_sync_rows={count}"


def get_all_symbols_with_retry(engine: DataEngine, attempts: int = 3) -> list[str]:
    import time

    for attempt in range(1, attempts + 1):
        symbols = engine.get_all_symbols()
        if symbols:
            return symbols
        if attempt < attempts:
            print(f"Stock list fetch returned empty, retrying {attempt}/{attempts}")
            time.sleep(3)
    return []


def fetch_history_task(task: tuple[str, str, str, str], attempts: int = 3) -> list[list[Any]]:
    import time

    import baostock as bs

    symbol, bs_code, start, end = task
    last_error = ""
    for attempt in range(1, attempts + 1):
        socket.setdefaulttimeout(10.0)
        rows: list[list[Any]] = []
        try:
            login_result = quiet_call(bs.login)
            if login_result.error_code != "0":
                last_error = login_result.error_msg
                continue

            result = quiet_call(
                bs.query_history_k_data_plus,
                bs_code,
                "date,open,high,low,close,volume,amount",
                start_date=start,
                end_date=end,
                frequency="d",
                adjustflag="1",
            )
            if result.error_code != "0":
                last_error = result.error_msg
                continue

            while result.next():
                row = result.get_row_data()
                if len(row) == 7:
                    rows.append([symbol] + row)
            return rows
        except Exception as exc:
            last_error = repr(exc)
            time.sleep(min(attempt * 2, 6))
        finally:
            try:
                quiet_call(bs.logout)
            except Exception:
                pass

    print(f"Backfill skipped {symbol}: {last_error}")
    return []


def fetch_batch_worker(batch_id: int, tasks: list[tuple[str, str, str, str]], queue: Any) -> None:
    socket.setdefaulttimeout(10.0)
    try:
        rows: list[list[Any]] = []
        for task in tasks:
            rows.extend(fetch_history_task(task))
        queue.put((batch_id, "ok", rows))
    except Exception as exc:
        queue.put((batch_id, "error", repr(exc)))


def parallel_backfill(
    engine: DataEngine,
    workers: int = 3,
    batch_size: int = 3,
    batch_timeout_seconds: int = 120,
) -> str:
    from datetime import date, timedelta
    from multiprocessing import Process, Queue
    from queue import Empty
    import time

    symbols = get_all_symbols_with_retry(engine)
    if not symbols:
        return "backfill_failed_no_symbols"

    today = date.today().strftime("%Y-%m-%d")
    tasks = []
    for symbol in symbols:
        last_date = engine._get_last_date(symbol)
        if last_date and last_date >= today:
            continue
        start = engine.start_date
        if last_date:
            start = (date.fromisoformat(last_date) + timedelta(days=1)).strftime("%Y-%m-%d")
        tasks.append((symbol, engine._to_baostock_code(symbol), start, today))

    if not tasks:
        return f"parallel_backfill_noop_symbols={len(symbols)}"

    worker_count = min(workers, len(tasks))
    chunks = [tasks[index : index + batch_size] for index in range(0, len(tasks), batch_size)]
    print(
        "Parallel backfill tasks: "
        f"{len(tasks)} symbols, workers: {worker_count}, batches: {len(chunks)}"
    )

    result_queue: Any = Queue()
    active: dict[int, tuple[Any, float]] = {}
    finished_batches: set[int] = set()
    inserted_rows = 0
    processed_batches = 0
    skipped_batches = 0
    next_batch_id = 0

    def launch_next() -> None:
        nonlocal next_batch_id
        if next_batch_id >= len(chunks):
            return
        batch_id = next_batch_id
        process = Process(
            target=fetch_batch_worker,
            args=(batch_id, chunks[batch_id], result_queue),
        )
        process.start()
        active[batch_id] = (process, time.monotonic())
        next_batch_id += 1

    for _ in range(worker_count):
        launch_next()

    while len(finished_batches) < len(chunks):
        message_received = False
        while True:
            try:
                batch_id, status, payload = result_queue.get_nowait()
            except Empty:
                break

            if batch_id in finished_batches:
                continue

            message_received = True
            process_info = active.pop(batch_id, None)
            if process_info:
                process_info[0].join(timeout=1)

            if status == "ok":
                inserted_rows += insert_raw_rows(engine.db_path, payload)
                processed_batches += 1
            else:
                skipped_batches += 1
                finished_batches.add(batch_id)
                print(f"Parallel backfill batch {batch_id} failed: {payload}")
                launch_next()
                continue

            finished_batches.add(batch_id)
            if len(finished_batches) % 10 == 0 or len(finished_batches) == len(chunks):
                print(
                    "Parallel backfill progress: "
                    f"{len(finished_batches)}/{len(chunks)} batches, "
                    f"inserted_rows={inserted_rows}, skipped_batches={skipped_batches}"
                )
            launch_next()

        now = time.monotonic()
        for batch_id, (process, started_at) in list(active.items()):
            if not process.is_alive():
                process.join(timeout=1)
                active.pop(batch_id, None)
                skipped_batches += 1
                finished_batches.add(batch_id)
                print(
                    "Parallel backfill batch exited without result: "
                    f"{batch_id}, exitcode={process.exitcode}"
                )
                launch_next()
                continue

            if now - started_at > batch_timeout_seconds:
                process.terminate()
                process.join(timeout=2)
                active.pop(batch_id, None)
                skipped_batches += 1
                finished_batches.add(batch_id)
                print(f"Parallel backfill batch timed out and skipped: {batch_id}")
                launch_next()

        if not message_received:
            time.sleep(0.2)

    if inserted_rows == 0:
        return f"parallel_backfill_no_rows_tasks={len(tasks)}"

    return (
        f"parallel_backfill_inserted_rows={inserted_rows} "
        f"tasks={len(tasks)} skipped_batches={skipped_batches}"
    )


def insert_raw_rows(db_path: str, raw_rows: list[list[Any]]) -> int:
    import pandas as pd

    if not raw_rows:
        return 0

    df = pd.DataFrame(
        raw_rows,
        columns=["symbol", "date", "open", "high", "low", "close", "volume", "turnover"],
    )
    for column in ["open", "high", "low", "close", "volume", "turnover"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["close"])
    df = df[df["volume"] > 0]

    if df.empty:
        return 0

    records = list(df[
        ["symbol", "date", "open", "high", "low", "close", "volume", "turnover"]
    ].itertuples(index=False, name=None))
    with sqlite3.connect(db_path) as conn:
        before = conn.total_changes
        conn.executemany(
            """
            INSERT OR IGNORE INTO stock_daily
                (symbol, date, open, high, low, close, volume, turnover)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        conn.commit()
        inserted = conn.total_changes - before

    return inserted


def fetch_stock_names(engine: DataEngine) -> dict[str, str]:
    import baostock as bs

    names: dict[str, str] = {}
    login_result = quiet_call(bs.login)
    if login_result.error_code != "0":
        print(f"Stock basic fetch failed: {login_result.error_msg}")
        return names

    try:
        result = quiet_call(bs.query_stock_basic, code_name="", code="")
        while result.next():
            row = result.get_row_data()
            if len(row) < 2:
                continue
            if len(row) >= 6:
                status = row[4]
                stock_type = row[5]
                if status != "1" or stock_type != "1":
                    continue
            code = row[0].split(".")[-1]
            names[code] = row[1]
    finally:
        quiet_call(bs.logout)

    return names


def fetch_unadjusted_quotes(
    engine: DataEngine,
    symbols: set[str],
    fallback_quotes: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    import baostock as bs

    def missing_real_quote(symbol: str) -> dict[str, Any]:
        fallback = fallback_quotes.get(symbol, {})
        return {
            "trade_date": fallback.get("trade_date", ""),
            "close": None,
            "volume": fallback.get("volume"),
            "turnover": fallback.get("turnover"),
        }

    quotes: dict[str, dict[str, Any]] = {}
    if not symbols:
        return quotes

    login_result = quiet_call(bs.login)
    if login_result.error_code != "0":
        print(f"Unadjusted quote fetch failed: {login_result.error_msg}")
        return {symbol: missing_real_quote(symbol) for symbol in symbols}

    try:
        for symbol in sorted(symbols):
            fallback = fallback_quotes.get(symbol, {})
            trade_date = fallback.get("trade_date")
            if not trade_date:
                quotes[symbol] = missing_real_quote(symbol)
                continue

            result = quiet_call(
                bs.query_history_k_data_plus,
                engine._to_baostock_code(symbol),
                "date,close,volume,amount",
                start_date=str(trade_date),
                end_date=str(trade_date),
                frequency="d",
                adjustflag="3",
            )
            if result.error_code != "0":
                quotes[symbol] = missing_real_quote(symbol)
                continue

            quote = missing_real_quote(symbol)
            while result.next():
                row = result.get_row_data()
                if len(row) < 4:
                    continue
                quote = {
                    "trade_date": row[0],
                    "close": row[1],
                    "volume": row[2],
                    "turnover": row[3],
                }
            quotes[symbol] = quote
    finally:
        quiet_call(bs.logout)

    return quotes


def detect_market_board(symbol: str) -> str:
    if symbol.startswith("688"):
        return "star_market"
    if symbol.startswith(("300", "301")):
        return "chinext"
    if symbol.startswith(("8", "4", "920")):
        return "beijing_stock_exchange"
    if symbol.startswith(("600", "601", "603", "605")):
        return "sh_main_board"
    if symbol.startswith(("000", "001", "002", "003")):
        return "sz_main_board"
    return "unknown"


def account_access(symbol: str) -> tuple[bool, str]:
    board = detect_market_board(symbol)
    if board == "star_market":
        return False, "no_star_market_access"
    if board == "chinext":
        return False, "no_chinext_access"
    if board == "beijing_stock_exchange":
        return False, "no_bse_access"
    if board == "unknown":
        return False, "unknown_market_board"
    return True, "none"


def blank_fundamental(status: str = "pending") -> dict[str, str]:
    return {
        "fundamental_passed": "pending",
        "fundamental_fail_reason": "fundamental_data_unavailable",
        "fundamental_data_status": status,
        "pe_ttm": "",
        "pb": "",
        "roe": "",
        "debt_ratio": "",
    }


def pick_column(row: dict[str, Any], candidates: list[str]) -> Any:
    for column in candidates:
        if column in row:
            return row[column]
    return None


def evaluate_fundamental(row: dict[str, Any]) -> dict[str, str]:
    pe = to_float(pick_column(row, ["市盈率-动态", "市盈率(TTM)", "市盈率ttm", "市盈率"]))
    pb = to_float(pick_column(row, ["市净率", "市净率MRQ"]))
    roe = to_float(pick_column(row, ["净资产收益率", "ROE", "roe"]))
    debt_ratio = to_float(pick_column(row, ["资产负债率", "debt_ratio"]))

    fail_reasons: list[str] = []
    if pe is not None and (pe <= 0 or pe > 300):
        fail_reasons.append("pe_extreme")
    if pb is not None and (pb <= 0 or pb > 20):
        fail_reasons.append("pb_extreme")
    if roe is not None and roe < 0:
        fail_reasons.append("roe_negative")
    if debt_ratio is not None and debt_ratio > 80:
        fail_reasons.append("debt_ratio_high")

    return {
        "fundamental_passed": format_bool(not fail_reasons),
        "fundamental_fail_reason": ";".join(fail_reasons) if fail_reasons else "none",
        "fundamental_data_status": "akshare_spot_available",
        "pe_ttm": format_number(pe, digits=4),
        "pb": format_number(pb, digits=4),
        "roe": format_number(roe, digits=4),
        "debt_ratio": format_number(debt_ratio, digits=4),
    }


def recent_report_periods(today: date | None = None) -> list[tuple[int, int]]:
    today = today or date.today()
    periods: list[tuple[int, int]] = []
    if today.month >= 11:
        periods.extend([(today.year, 3), (today.year, 2), (today.year, 1)])
    elif today.month >= 9:
        periods.extend([(today.year, 2), (today.year, 1)])
    elif today.month >= 5:
        periods.append((today.year, 1))

    periods.extend([
        (today.year - 1, 4),
        (today.year - 1, 3),
        (today.year - 1, 2),
        (today.year - 1, 1),
    ])
    return periods


def first_baostock_row(result: Any) -> dict[str, str]:
    if result.error_code != "0":
        return {}
    while result.next():
        values = result.get_row_data()
        return dict(zip(result.fields, values, strict=False))
    return {}


def evaluate_baostock_fundamental(
    profit_row: dict[str, str],
    balance_row: dict[str, str],
    period: tuple[int, int],
    source_status: str,
) -> dict[str, str]:
    roe_raw = to_float(profit_row.get("roeAvg"))
    debt_raw = to_float(balance_row.get("liabilityToAsset"))
    roe = roe_raw * 100 if roe_raw is not None else None
    debt_ratio = debt_raw * 100 if debt_raw is not None else None

    fail_reasons: list[str] = []
    if roe is not None and roe < 0:
        fail_reasons.append("roe_negative")
    if debt_ratio is not None and debt_ratio > 80:
        fail_reasons.append("debt_ratio_high")

    year, quarter = period
    return {
        "fundamental_passed": format_bool(not fail_reasons),
        "fundamental_fail_reason": ";".join(fail_reasons) if fail_reasons else "none",
        "fundamental_data_status": f"baostock_fallback_after_{source_status}:{year}Q{quarter}",
        "pe_ttm": "",
        "pb": "",
        "roe": format_number(roe, digits=4),
        "debt_ratio": format_number(debt_ratio, digits=4),
    }


def fetch_baostock_fundamentals(symbols: set[str], source_status: str) -> dict[str, dict[str, str]]:
    import baostock as bs

    fundamentals: dict[str, dict[str, str]] = {}
    if not symbols:
        return fundamentals

    login_result = quiet_call(bs.login)
    if login_result.error_code != "0":
        status = f"baostock_unavailable:{login_result.error_msg}"
        return {symbol: blank_fundamental(status) for symbol in symbols}

    periods = recent_report_periods()
    try:
        for symbol in sorted(symbols):
            bs_code = DataEngine._to_baostock_code(symbol)
            selected: dict[str, str] | None = None
            for period in periods:
                year, quarter = period
                try:
                    profit_row = first_baostock_row(
                        quiet_call(bs.query_profit_data, code=bs_code, year=year, quarter=quarter)
                    )
                    balance_row = first_baostock_row(
                        quiet_call(bs.query_balance_data, code=bs_code, year=year, quarter=quarter)
                    )
                except Exception:
                    continue

                if profit_row or balance_row:
                    selected = evaluate_baostock_fundamental(
                        profit_row,
                        balance_row,
                        period,
                        source_status,
                    )
                    break

            fundamentals[symbol] = selected or blank_fundamental(
                f"baostock_no_report_after_{source_status}"
            )
    finally:
        quiet_call(bs.logout)

    return fundamentals


def fetch_fundamentals(symbols: set[str], *, skip: bool) -> dict[str, dict[str, str]]:
    if skip or not symbols:
        return {symbol: blank_fundamental("skipped") for symbol in symbols}

    old_no_proxy = os.environ.get("NO_PROXY")
    old_no_proxy_lower = os.environ.get("no_proxy")
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
    try:
        import akshare as ak

        df = ak.stock_zh_a_spot_em()
    except Exception as exc:
        status = f"akshare_unavailable:{type(exc).__name__}"
        print(f"Fundamental fetch unavailable: {status}")
        return fetch_baostock_fundamentals(symbols, status)
    finally:
        if old_no_proxy is None:
            os.environ.pop("NO_PROXY", None)
        else:
            os.environ["NO_PROXY"] = old_no_proxy
        if old_no_proxy_lower is None:
            os.environ.pop("no_proxy", None)
        else:
            os.environ["no_proxy"] = old_no_proxy_lower

    if df.empty or "代码" not in df.columns:
        return fetch_baostock_fundamentals(symbols, "akshare_empty")

    df = df.copy()
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    rows_by_symbol = {
        str(row["代码"]).zfill(6): row.to_dict()
        for _, row in df.iterrows()
    }

    fundamentals: dict[str, dict[str, str]] = {}
    for symbol in symbols:
        raw = rows_by_symbol.get(symbol)
        if not raw:
            fundamentals[symbol] = blank_fundamental("akshare_symbol_missing")
        else:
            fundamentals[symbol] = evaluate_fundamental(raw)
    return fundamentals


def run_strategies(engine: DataEngine, settings: Settings) -> dict[str, set[str]]:
    hits: dict[str, set[str]] = {}
    for strategy_name, strategy_cls in STRATEGIES:
        strategy = strategy_cls(engine=engine, settings=settings)
        selected = set(strategy.run())
        hits[strategy_name] = selected
        print(f"{strategy_name}: {len(selected)} hits")
    return hits


def latest_quote_by_symbol(db_path: str) -> dict[str, dict[str, Any]]:
    query = """
        SELECT d.symbol, d.date, d.close, d.volume, d.turnover
        FROM stock_daily AS d
        JOIN (
            SELECT symbol, MAX(date) AS latest_date
            FROM stock_daily
            GROUP BY symbol
        ) AS latest
        ON d.symbol = latest.symbol AND d.date = latest.latest_date
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query).fetchall()

    return {
        symbol: {
            "trade_date": trade_date,
            "close": close,
            "volume": volume,
            "turnover": turnover,
        }
        for symbol, trade_date, close, volume, turnover in rows
    }


def price_bucket(close: float | None) -> str:
    if close is None:
        return ""
    if close < 5:
        return "low_price_high_risk"
    if close < 15:
        return "low_price_tradable_need_fundamental_check"
    if close < 30:
        return "preferred_mid_price"
    if close <= 45:
        return "preferred_upper_mid_price"
    if close <= 50:
        return "watch_only"
    return "not_affordable"


def is_st_stock(name: str) -> bool:
    return "ST" in name.upper()


def build_daily_rows(
    hits: dict[str, set[str]],
    quotes: dict[str, dict[str, Any]],
    names: dict[str, str],
    fundamentals: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    by_symbol: dict[str, list[str]] = defaultdict(list)
    for strategy_name in STRATEGY_ORDER:
        for symbol in hits.get(strategy_name, set()):
            by_symbol[symbol].append(strategy_name)

    rows: list[dict[str, str]] = []
    for symbol in sorted(by_symbol):
        strategy_hit = [name for name in STRATEGY_ORDER if name in by_symbol[symbol]]
        quote = quotes.get(symbol, {})
        name = names.get(symbol, "")

        close: float | None = None
        try:
            close = float(quote["close"])
        except (KeyError, TypeError, ValueError):
            close = None

        one_lot_cost = close * 100 if close is not None else None
        affordable = one_lot_cost is not None and one_lot_cost <= 4500
        bucket = price_bucket(close)
        st_stock = is_st_stock(name)
        board = detect_market_board(symbol)
        account_accessible, market_access_fail_reason = account_access(symbol)
        fundamental = fundamentals.get(symbol, blank_fundamental())

        fail_reasons: list[str] = []
        if close is None:
            fail_reasons.append("missing_close")
        if st_stock:
            fail_reasons.append("st_stock")
        if not account_accessible:
            fail_reasons.append(market_access_fail_reason)
        if bucket == "low_price_high_risk":
            fail_reasons.append("low_price_high_risk")
        if bucket == "watch_only":
            fail_reasons.append("watch_only")
        if not affordable:
            fail_reasons.append("not_affordable")
        if fundamental["fundamental_passed"] == "false":
            fail_reasons.extend(fundamental["fundamental_fail_reason"].split(";"))

        hard_passed = not fail_reasons
        rps_hit = "RpsBreakout" in strategy_hit
        turtle_hit = "TurtleTrade" in strategy_hit

        tags: list[str] = []
        if rps_hit and turtle_hit and hard_passed:
            tags.append("main_trade_candidate")
        else:
            if rps_hit:
                tags.append("strength_watch")
            if turtle_hit:
                tags.append("breakout_watch")

        if "MaVolume" in strategy_hit:
            tags.append("volume_watch")
        if "HighTightFlag" in strategy_hit:
            tags.append("consolidation_watch")
        if bucket == "low_price_high_risk":
            tags.append("low_price_high_risk")
        if not affordable:
            tags.append("not_affordable")

        rows.append(
            {
                "trade_date": str(quote.get("trade_date", "")),
                "code": symbol,
                "name": name,
                "close": format_number(close),
                "strategy_hit": ";".join(strategy_hit),
                "priority_tag": ";".join(dict.fromkeys(tags)),
                "turnover": format_number(quote.get("turnover"), digits=2),
                "volume": format_number(quote.get("volume"), digits=2),
                "one_lot_cost": format_number(one_lot_cost, digits=2),
                "affordable_flag": format_bool(affordable),
                "price_bucket": bucket,
                "passed_price_filter": format_bool(affordable),
                "market_board": board,
                "account_accessible_flag": format_bool(account_accessible),
                "market_access_fail_reason": market_access_fail_reason,
                "fundamental_passed": fundamental["fundamental_passed"],
                "fundamental_fail_reason": fundamental["fundamental_fail_reason"],
                "fundamental_data_status": fundamental["fundamental_data_status"],
                "pe_ttm": fundamental["pe_ttm"],
                "pb": fundamental["pb"],
                "roe": fundamental["roe"],
                "debt_ratio": fundamental["debt_ratio"],
                "filter_fail_reason": ";".join(fail_reasons) if fail_reasons else "none",
            }
        )

    rows.sort(
        key=lambda row: (
            "main_trade_candidate" not in row["priority_tag"].split(";"),
            row["code"],
        )
    )
    return rows


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_existing_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def build_signal_rows(daily_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    existing_rows = read_existing_csv(SIGNAL_TRACKING_PATH)
    daily_keys = {(row["trade_date"], row["code"]) for row in daily_rows}
    daily_dates = {row["trade_date"] for row in daily_rows}
    existing_by_key = {
        (row.get("selected_date", ""), row.get("code", "")): row for row in existing_rows
    }

    merged_by_key = {
        (row.get("selected_date", ""), row.get("code", "")): {
            column: row.get(column, "") for column in SIGNAL_COLUMNS
        }
        for row in existing_rows
        if (row.get("selected_date", ""), row.get("code", "")) in daily_keys
        or row.get("selected_date", "") not in daily_dates
    }

    for daily in daily_rows:
        key = (daily["trade_date"], daily["code"])
        existing = existing_by_key.get(key, {})
        signal_row = {
            "selected_date": daily["trade_date"],
            "code": daily["code"],
            "name": daily["name"],
            "selected_close": daily["close"],
            "strategy_hit": daily["strategy_hit"],
            "priority_tag": daily["priority_tag"],
            "price_bucket": daily["price_bucket"],
            "one_lot_cost": daily["one_lot_cost"],
            "market_board": daily["market_board"],
            "account_accessible_flag": daily["account_accessible_flag"],
            "market_access_fail_reason": daily["market_access_fail_reason"],
            "fundamental_passed": daily["fundamental_passed"],
            "fundamental_fail_reason": daily["fundamental_fail_reason"],
            "fundamental_data_status": daily["fundamental_data_status"],
            "pe_ttm": daily["pe_ttm"],
            "pb": daily["pb"],
            "roe": daily["roe"],
            "debt_ratio": daily["debt_ratio"],
            "market_gate_status": existing.get("market_gate_status") or "pending",
            "passed_hard_filter": format_bool(daily["filter_fail_reason"] == "none"),
            "filter_fail_reason": daily["filter_fail_reason"],
            "actual_trade_flag": existing.get("actual_trade_flag") or "false",
            "actual_buy_price": "",
            "actual_sell_price": "",
            "close_t1": "",
            "close_t3": "",
            "close_t5": "",
            "return_t1": "",
            "return_t3": "",
            "return_t5": "",
            "max_drawdown_5d": "",
            "notes": "",
        }
        for column in MANUAL_SIGNAL_COLUMNS:
            if existing.get(column):
                signal_row[column] = existing[column]
        merged_by_key[key] = signal_row

    return sorted(
        merged_by_key.values(),
        key=lambda row: (row.get("selected_date", ""), row.get("code", "")),
    )


def ensure_exit_log() -> None:
    if EXIT_LOG_PATH.exists():
        return
    write_csv(EXIT_LOG_PATH, EXIT_COLUMNS, [])


def build_data_health_rows(engine: DataEngine, names: dict[str, str]) -> list[dict[str, str]]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(engine.db_path) as conn:
        stats = conn.execute(
            """
            SELECT symbol, COUNT(*) AS row_count, MIN(date) AS first_date, MAX(date) AS latest_date
            FROM stock_daily
            GROUP BY symbol
            """
        ).fetchall()

    stats_by_symbol = {
        symbol: {
            "row_count": row_count,
            "first_date": first_date or "",
            "latest_date": latest_date or "",
        }
        for symbol, row_count, first_date, latest_date in stats
    }
    market_latest_date = max(
        (item["latest_date"] for item in stats_by_symbol.values() if item["latest_date"]),
        default="",
    )
    universe = set(names) | set(stats_by_symbol)

    rows: list[dict[str, str]] = []
    for symbol in sorted(universe):
        stat = stats_by_symbol.get(symbol)
        if not stat:
            status = "missing_symbol"
            row_count = 0
            first_date = ""
            latest_date = ""
            is_latest = False
            notes = "no_local_kline"
        else:
            row_count = int(stat["row_count"])
            first_date = stat["first_date"]
            latest_date = stat["latest_date"]
            is_latest = bool(market_latest_date and latest_date == market_latest_date)
            if not is_latest:
                status = "stale"
                notes = "latest_date_before_market_latest"
            elif row_count < 120:
                status = "insufficient_history"
                notes = "less_than_120_bars"
            else:
                status = "ok"
                notes = ""

        rows.append(
            {
                "generated_at": generated_at,
                "code": symbol,
                "name": names.get(symbol, ""),
                "row_count": str(row_count),
                "first_date": first_date,
                "latest_date": latest_date,
                "market_latest_date": market_latest_date,
                "is_latest": format_bool(is_latest),
                "data_health_status": status,
                "notes": notes,
            }
        )

    return rows


def is_open_position(exit_row: dict[str, str]) -> bool:
    if not exit_row.get("code"):
        return False
    exit_price = exit_row.get("exit_price", "").strip()
    exit_reason = exit_row.get("exit_reason", "").strip()
    return not exit_price and exit_reason in {"", "not_exited"}


def build_exit_alert_rows(engine: DataEngine) -> list[dict[str, str]]:
    ensure_exit_log()
    exit_rows = [row for row in read_existing_csv(EXIT_LOG_PATH) if is_open_position(row)]
    if not exit_rows:
        return []

    symbols = {row["code"] for row in exit_rows}
    adjusted_quotes = latest_quote_by_symbol(engine.db_path)
    real_quotes = fetch_unadjusted_quotes(engine, symbols, adjusted_quotes)
    alert_date = date.today().strftime("%Y-%m-%d")

    rows: list[dict[str, str]] = []
    for exit_row in exit_rows:
        symbol = exit_row["code"]
        buy_price = to_float(exit_row.get("buy_price"))
        initial_stop_price = to_float(exit_row.get("initial_stop_price"))
        if initial_stop_price is None and buy_price is not None:
            initial_stop_price = buy_price * 0.94

        latest_quote = real_quotes.get(symbol, {})
        latest_close = to_float(latest_quote.get("close"))
        latest_date = str(latest_quote.get("trade_date", ""))

        adjusted_close: float | None = None
        ma20: float | None = None
        try:
            df = engine.get_ohlcv(symbol)
            if not df.empty:
                adjusted_close = to_float(df.iloc[-1]["close"])
                ma20 = to_float(df["close"].tail(20).mean()) if len(df) >= 20 else None
        except Exception:
            pass

        hard_stop_triggered = (
            buy_price is not None
            and latest_close is not None
            and latest_close <= buy_price * 0.94
        )
        trend_stop_triggered = (
            adjusted_close is not None
            and ma20 is not None
            and adjusted_close < ma20
        )

        if hard_stop_triggered:
            exit_priority = "hard_stop"
        elif trend_stop_triggered:
            exit_priority = "trend_stop"
        else:
            exit_priority = "not_triggered"

        rows.append(
            {
                "alert_date": alert_date,
                "code": symbol,
                "name": exit_row.get("name", ""),
                "buy_date": exit_row.get("buy_date", ""),
                "buy_price": format_number(buy_price),
                "initial_stop_price": format_number(initial_stop_price),
                "latest_date": latest_date,
                "latest_close": format_number(latest_close),
                "adjusted_close": format_number(adjusted_close),
                "ma20": format_number(ma20),
                "hard_stop_triggered": format_bool(hard_stop_triggered),
                "trend_stop_triggered": format_bool(trend_stop_triggered),
                "exit_priority": exit_priority,
                "exit_attempted_flag": exit_row.get("exit_attempted_flag", "") or "false",
                "notes": "",
            }
        )

    return rows


def write_daily_report(
    daily_rows: list[dict[str, str]],
    health_rows: list[dict[str, str]],
    exit_alert_rows: list[dict[str, str]],
    update_status: str,
) -> None:
    main_rows = [
        row for row in daily_rows
        if "main_trade_candidate" in row["priority_tag"].split(";")
    ]
    watch_rows = [row for row in daily_rows if row not in main_rows]
    filtered_rows = [row for row in daily_rows if row["filter_fail_reason"] != "none"]
    health_counts: dict[str, int] = defaultdict(int)
    for row in health_rows:
        health_counts[row["data_health_status"]] += 1
    fundamental_counts: dict[str, int] = defaultdict(int)
    fundamental_fail_counts: dict[str, int] = defaultdict(int)
    filter_counts: dict[str, int] = defaultdict(int)
    tag_counts: dict[str, int] = defaultdict(int)
    for row in daily_rows:
        fundamental_counts[row["fundamental_passed"]] += 1
        if row["fundamental_fail_reason"] != "none":
            for reason in row["fundamental_fail_reason"].split(";"):
                fundamental_fail_counts[reason] += 1
        if row["filter_fail_reason"] != "none":
            for reason in row["filter_fail_reason"].split(";"):
                filter_counts[reason] += 1
        for tag in row["priority_tag"].split(";"):
            if tag:
                tag_counts[tag] += 1

    clean_watch_rows = [
        row for row in watch_rows
        if row["filter_fail_reason"] == "none"
    ][:12]

    lines = [
        "# A股 MVP 日报",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 数据更新：`{update_status}`",
        f"- 候选总数：{len(daily_rows)}",
        f"- 主候选：{len(main_rows)}",
        f"- 观察候选：{len(watch_rows)}",
        f"- 被硬过滤候选：{len(filtered_rows)}",
        f"- 持仓退出提醒：{len(exit_alert_rows)}",
        "",
        "## 主候选",
        "",
    ]

    if main_rows:
        lines.extend([
            "| code | name | close | one_lot_cost | price_bucket | ROE | debt_ratio | strategy_hit |",
            "|---|---|---:|---:|---|---:|---:|---|",
        ])
        for row in main_rows:
            lines.append(
                "| {code} | {name} | {close} | {one_lot_cost} | {price_bucket} | "
                "{roe} | {debt_ratio} | {strategy_hit} |".format(
                    **row
                )
            )
    else:
        lines.append("今日没有主候选。")

    lines.extend([
        "",
        "## 观察池",
        "",
        f"- strength_watch：{tag_counts.get('strength_watch', 0)}",
        f"- breakout_watch：{tag_counts.get('breakout_watch', 0)}",
        f"- volume_watch：{tag_counts.get('volume_watch', 0)}",
        f"- consolidation_watch：{tag_counts.get('consolidation_watch', 0)}",
        "",
    ])

    if clean_watch_rows:
        lines.extend([
            "| code | name | close | tag | strategy_hit |",
            "|---|---|---:|---|---|",
        ])
        for row in clean_watch_rows:
            lines.append(
                "| {code} | {name} | {close} | {priority_tag} | {strategy_hit} |".format(**row)
            )
    else:
        lines.append("没有通过硬过滤的观察候选。")

    lines.extend([
        "",
        "## 数据健康",
        "",
        f"- 股票覆盖数：{len(health_rows)}",
        f"- OK：{health_counts.get('ok', 0)}",
        f"- 缺失：{health_counts.get('missing_symbol', 0)}",
        f"- 滞后：{health_counts.get('stale', 0)}",
        f"- 历史不足：{health_counts.get('insufficient_history', 0)}",
        "",
        "## 基础面状态",
        "",
        f"- 通过：{fundamental_counts.get('true', 0)}",
        f"- 未通过：{fundamental_counts.get('false', 0)}",
        f"- 待定/不可用：{fundamental_counts.get('pending', 0)}",
        "",
        "## 过滤原因",
        "",
    ])

    if filter_counts:
        for reason, count in sorted(filter_counts.items(), key=lambda item: (-item[1], item[0]))[:12]:
            lines.append(f"- {reason}：{count}")
    else:
        lines.append("- 今日没有候选被硬过滤。")

    lines.extend([
        "",
        "## 基础面失败",
        "",
    ])

    if fundamental_fail_counts:
        for reason, count in sorted(
            fundamental_fail_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:8]:
            lines.append(f"- {reason}：{count}")
    else:
        lines.append("- 今日没有基础面硬过滤失败。")

    lines.extend([
        "",
        "## 退出提醒",
        "",
    ])

    if exit_alert_rows:
        lines.extend([
            "| code | name | exit_priority | hard_stop | trend_stop | latest_close | ma20 |",
            "|---|---|---|---|---|---:|---:|",
        ])
        for row in exit_alert_rows:
            lines.append(
                "| {code} | {name} | {exit_priority} | {hard_stop_triggered} | "
                "{trend_stop_triggered} | {latest_close} | {ma20} |".format(**row)
            )
    else:
        lines.append("当前没有未退出持仓记录。")

    lines.extend([
        "",
        "## 输出文件",
        "",
        f"- `{DAILY_CANDIDATES_PATH}`",
        f"- `{SIGNAL_TRACKING_PATH}`",
        f"- `{EXIT_LOG_PATH}`",
        f"- `{DATA_HEALTH_PATH}`",
        f"- `{EXIT_ALERTS_PATH}`",
        f"- `{REVIEW_SUMMARY_PATH}`",
    ])

    DAILY_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def schema_ok(path: Path, expected_columns: list[str]) -> bool:
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            columns = next(reader)
        except StopIteration:
            return False
    return columns == expected_columns


def main() -> int:
    args = parse_args()
    settings = make_settings()
    engine = DataEngine(settings)

    print("MVP screen started")
    update_status = update_data(
        engine,
        force_backfill=args.backfill or args.backfill_only,
        skip_sync=args.skip_sync,
    )
    print(f"Data update: {update_status}")

    if args.backfill_only:
        names = fetch_stock_names(engine)
        health_rows = build_data_health_rows(engine, names)
        write_csv(DATA_HEALTH_PATH, DATA_HEALTH_COLUMNS, health_rows)
        health_issue_count = sum(row["data_health_status"] != "ok" for row in health_rows)
        print(f"data_health rows: {len(health_rows)}")
        print(f"data_health issue rows: {health_issue_count}")
        print(f"Output: {DATA_HEALTH_PATH}")
        print(f"Schema data_health.csv: {schema_ok(DATA_HEALTH_PATH, DATA_HEALTH_COLUMNS)}")
        print("Backfill-only completed")
        return 0

    print("Strategies: RpsBreakout, TurtleTrade, MaVolume, HighTightFlag")
    hits = run_strategies(engine, settings)

    candidates = set().union(*hits.values()) if hits else set()
    adjusted_quotes = latest_quote_by_symbol(engine.db_path)
    quotes = fetch_unadjusted_quotes(engine, candidates, adjusted_quotes)
    names = fetch_stock_names(engine)
    fundamentals = fetch_fundamentals(candidates, skip=args.skip_fundamentals)
    daily_rows = build_daily_rows(hits, quotes, names, fundamentals)
    signal_rows = build_signal_rows(daily_rows)
    health_rows = build_data_health_rows(engine, names)
    exit_alert_rows = build_exit_alert_rows(engine)

    write_csv(DAILY_CANDIDATES_PATH, DAILY_COLUMNS, daily_rows)
    write_csv(SIGNAL_TRACKING_PATH, SIGNAL_COLUMNS, signal_rows)
    ensure_exit_log()
    write_csv(DATA_HEALTH_PATH, DATA_HEALTH_COLUMNS, health_rows)
    write_csv(EXIT_ALERTS_PATH, EXIT_ALERT_COLUMNS, exit_alert_rows)
    write_daily_report(daily_rows, health_rows, exit_alert_rows, update_status)

    main_count = sum(
        "main_trade_candidate" in row["priority_tag"].split(";") for row in daily_rows
    )
    missing_close_count = sum(row["close"] == "" for row in daily_rows)
    health_issue_count = sum(row["data_health_status"] != "ok" for row in health_rows)
    exit_alert_count = sum(row["exit_priority"] != "not_triggered" for row in exit_alert_rows)

    print(f"Merged candidates: {len(candidates)}")
    print(f"daily_candidates rows: {len(daily_rows)}")
    print(f"main_trade_candidate rows: {main_count}")
    print(f"Rows with missing close: {missing_close_count}")
    print(f"data_health rows: {len(health_rows)}")
    print(f"data_health issue rows: {health_issue_count}")
    print(f"exit_alerts rows: {len(exit_alert_rows)}")
    print(f"triggered exit alerts: {exit_alert_count}")
    print(f"Output: {DAILY_CANDIDATES_PATH}")
    print(f"Output: {SIGNAL_TRACKING_PATH}")
    print(f"Output: {EXIT_LOG_PATH}")
    print(f"Output: {DATA_HEALTH_PATH}")
    print(f"Output: {EXIT_ALERTS_PATH}")
    print(f"Output: {DAILY_REPORT_PATH}")
    print(f"Schema daily_candidates.csv: {schema_ok(DAILY_CANDIDATES_PATH, DAILY_COLUMNS)}")
    print(f"Schema signal_tracking.csv: {schema_ok(SIGNAL_TRACKING_PATH, SIGNAL_COLUMNS)}")
    print(f"Schema exit_log.csv: {schema_ok(EXIT_LOG_PATH, EXIT_COLUMNS)}")
    print(f"Schema data_health.csv: {schema_ok(DATA_HEALTH_PATH, DATA_HEALTH_COLUMNS)}")
    print(f"Schema exit_alerts.csv: {schema_ok(EXIT_ALERTS_PATH, EXIT_ALERT_COLUMNS)}")
    print("MVP screen completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
