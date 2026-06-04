"""Backfill future performance fields in signal_tracking.csv.

The script intentionally leaves fields blank when future trading days or
unadjusted baostock quotes are unavailable. Blank future fields are valid.
"""

from __future__ import annotations

import csv
import socket
import sqlite3
import sys
from pathlib import Path
from typing import Any


socket.setdefaulttimeout(10.0)

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_mvp_screen import (
    SIGNAL_COLUMNS,
    SIGNAL_TRACKING_PATH,
    format_number,
    make_settings,
    quiet_call,
    to_float,
)
from review_summary import REVIEW_SUMMARY_PATH, build_summary_rows, write_summary_rows
from sequoia_x.data.engine import DataEngine


FUTURE_CLOSE_FIELDS = {
    1: "close_t1",
    3: "close_t3",
    5: "close_t5",
}
FUTURE_RETURN_FIELDS = {
    1: "return_t1",
    3: "return_t3",
    5: "return_t5",
}


def read_signal_rows() -> list[dict[str, str]]:
    if not SIGNAL_TRACKING_PATH.exists():
        return []
    with SIGNAL_TRACKING_PATH.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_signal_rows(rows: list[dict[str, str]]) -> None:
    with SIGNAL_TRACKING_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SIGNAL_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in SIGNAL_COLUMNS})


def trading_dates_by_symbol(db_path: str) -> dict[str, list[str]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT symbol, date FROM stock_daily ORDER BY symbol, date"
        ).fetchall()

    result: dict[str, list[str]] = {}
    for symbol, trade_date in rows:
        result.setdefault(symbol, []).append(trade_date)
    return result


def fetch_unadjusted_history(engine: DataEngine, symbol: str, start_date: str, end_date: str) -> dict[str, dict[str, float]]:
    import baostock as bs

    quotes: dict[str, dict[str, float]] = {}
    login_result = quiet_call(bs.login)
    if login_result.error_code != "0":
        return quotes

    try:
        result = quiet_call(
            bs.query_history_k_data_plus,
            engine._to_baostock_code(symbol),
            "date,close,low",
            start_date=start_date,
            end_date=end_date,
            frequency="d",
            adjustflag="3",
        )
        if result.error_code != "0":
            return quotes
        while result.next():
            row = result.get_row_data()
            if len(row) < 3:
                continue
            close = to_float(row[1])
            low = to_float(row[2])
            if close is None:
                continue
            quotes[row[0]] = {
                "close": close,
                "low": low if low is not None else close,
            }
    finally:
        quiet_call(bs.logout)

    return quotes


def target_dates_for_row(row: dict[str, str], calendars: dict[str, list[str]]) -> dict[int, str]:
    symbol = row.get("code", "")
    selected_date = row.get("selected_date", "")
    dates = calendars.get(symbol, [])
    if selected_date not in dates:
        return {}

    selected_index = dates.index(selected_date)
    targets: dict[int, str] = {}
    for offset in FUTURE_CLOSE_FIELDS:
        target_index = selected_index + offset
        if target_index < len(dates):
            targets[offset] = dates[target_index]
    return targets


def backfill_rows(rows: list[dict[str, str]], engine: DataEngine) -> tuple[list[dict[str, str]], int]:
    calendars = trading_dates_by_symbol(engine.db_path)
    updated = 0

    for row in rows:
        for column in SIGNAL_COLUMNS:
            row.setdefault(column, "")

        selected_close = to_float(row.get("selected_close"))
        if selected_close is None:
            continue

        targets = target_dates_for_row(row, calendars)
        if not targets or 1 not in targets:
            continue

        symbol = row.get("code", "")
        selected_date = row.get("selected_date", "")
        end_date = targets.get(5) or targets.get(3) or targets.get(1)
        if not symbol or not selected_date or not end_date:
            continue

        history = fetch_unadjusted_history(engine, symbol, selected_date, end_date)
        if not history:
            continue

        row_changed = False
        for offset, target_date in targets.items():
            quote = history.get(target_date)
            if not quote:
                continue

            close_field = FUTURE_CLOSE_FIELDS[offset]
            return_field = FUTURE_RETURN_FIELDS[offset]
            close = quote["close"]
            if not row.get(close_field):
                row[close_field] = format_number(close)
                row_changed = True
            if not row.get(return_field):
                row[return_field] = format_number((close - selected_close) / selected_close, digits=6)
                row_changed = True

        if 5 in targets and not row.get("max_drawdown_5d"):
            dates = calendars.get(symbol, [])
            start_index = dates.index(selected_date)
            future_dates = dates[start_index + 1 : start_index + 6]
            lows = [
                history[trade_date]["low"]
                for trade_date in future_dates
                if trade_date in history
            ]
            if lows:
                row["max_drawdown_5d"] = format_number(
                    (min(lows) - selected_close) / selected_close,
                    digits=6,
                )
                row_changed = True

        if row_changed:
            updated += 1

    return rows, updated


def main() -> int:
    settings = make_settings()
    engine = DataEngine(settings)
    rows = read_signal_rows()
    if not rows:
        print("signal_tracking.csv is missing or empty")
        return 0

    rows, updated = backfill_rows(rows, engine)
    write_signal_rows(rows)
    write_summary_rows(build_summary_rows(rows))
    print(f"signal_tracking rows: {len(rows)}")
    print(f"updated rows: {updated}")
    print(f"Output: {SIGNAL_TRACKING_PATH}")
    print(f"Output: {REVIEW_SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
