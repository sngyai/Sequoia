"""Create review_summary.csv from signal_tracking.csv."""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_mvp_screen import OUTPUT_DIR, SIGNAL_TRACKING_PATH, format_number, to_float


REVIEW_SUMMARY_PATH = OUTPUT_DIR / "review_summary.csv"

SUMMARY_COLUMNS = [
    "group_type",
    "group_name",
    "sample_count",
    "actual_trade_count",
    "return_t1_count",
    "return_t1_mean",
    "return_t1_win_rate",
    "return_t3_count",
    "return_t3_mean",
    "return_t3_win_rate",
    "return_t5_count",
    "return_t5_mean",
    "return_t5_win_rate",
    "max_drawdown_5d_count",
    "max_drawdown_5d_mean",
]

TAG_GROUPS = [
    "main_trade_candidate",
    "strength_watch",
    "breakout_watch",
    "volume_watch",
    "consolidation_watch",
    "not_affordable",
    "low_price_high_risk",
]

STRATEGY_GROUPS = [
    "RpsBreakout",
    "TurtleTrade",
    "MaVolume",
    "HighTightFlag",
]


def read_signal_rows() -> list[dict[str, str]]:
    if not SIGNAL_TRACKING_PATH.exists():
        return []
    with SIGNAL_TRACKING_PATH.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def values(rows: Iterable[dict[str, str]], column: str) -> list[float]:
    result: list[float] = []
    for row in rows:
        value = to_float(row.get(column))
        if value is not None:
            result.append(value)
    return result


def mean_text(items: list[float]) -> str:
    if not items:
        return ""
    return format_number(statistics.fmean(items), digits=6)


def win_rate_text(items: list[float]) -> str:
    if not items:
        return ""
    return format_number(sum(value > 0 for value in items) / len(items), digits=6)


def summarize(group_type: str, group_name: str, rows: list[dict[str, str]]) -> dict[str, str]:
    return_t1 = values(rows, "return_t1")
    return_t3 = values(rows, "return_t3")
    return_t5 = values(rows, "return_t5")
    max_drawdown = values(rows, "max_drawdown_5d")

    return {
        "group_type": group_type,
        "group_name": group_name,
        "sample_count": str(len(rows)),
        "actual_trade_count": str(sum(row.get("actual_trade_flag") == "true" for row in rows)),
        "return_t1_count": str(len(return_t1)),
        "return_t1_mean": mean_text(return_t1),
        "return_t1_win_rate": win_rate_text(return_t1),
        "return_t3_count": str(len(return_t3)),
        "return_t3_mean": mean_text(return_t3),
        "return_t3_win_rate": win_rate_text(return_t3),
        "return_t5_count": str(len(return_t5)),
        "return_t5_mean": mean_text(return_t5),
        "return_t5_win_rate": win_rate_text(return_t5),
        "max_drawdown_5d_count": str(len(max_drawdown)),
        "max_drawdown_5d_mean": mean_text(max_drawdown),
    }


def build_summary_rows(signal_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [summarize("all", "all", signal_rows)]

    for tag in TAG_GROUPS:
        tag_rows = [
            row for row in signal_rows
            if tag in row.get("priority_tag", "").split(";")
        ]
        rows.append(summarize("priority_tag", tag, tag_rows))

    for strategy in STRATEGY_GROUPS:
        strategy_rows = [
            row for row in signal_rows
            if strategy in row.get("strategy_hit", "").split(";")
        ]
        rows.append(summarize("strategy_hit", strategy, strategy_rows))

    for value in ["true", "false"]:
        hard_filter_rows = [
            row for row in signal_rows
            if row.get("passed_hard_filter") == value
        ]
        rows.append(summarize("passed_hard_filter", value, hard_filter_rows))

    return rows


def write_summary_rows(rows: list[dict[str, str]]) -> None:
    REVIEW_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    signal_rows = read_signal_rows()
    summary_rows = build_summary_rows(signal_rows)
    write_summary_rows(summary_rows)
    print(f"signal_tracking rows: {len(signal_rows)}")
    print(f"review_summary rows: {len(summary_rows)}")
    print(f"Output: {REVIEW_SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
