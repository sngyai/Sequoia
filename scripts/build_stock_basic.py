"""从 akshare 新浪 spot 一次性拉全市场股票名称,写入本地 stock_basic 表。

用途:替代 feishu.py 中通过 baostock 查询股票名称的逻辑(baostock 已被风控)。
用法:venv\Scripts\python scripts/build_stock_basic.py
     --refresh  强制全量刷新(默认只 UPSERT,会覆盖名称)
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "sequoia_v2.db"


def _strip_prefix(code: str) -> str:
    """akshare 新浪 spot 返回的代码含 sh/sz/bj 前缀,统一去掉。"""
    s = str(code).strip()
    for p in ("sh", "sz", "bj", "SH", "SZ", "BJ"):
        if s.startswith(p):
            return s[len(p):]
    return s


def fetch_all_names(retries: int = 3) -> list[tuple[str, str]]:
    """拉全市场 (code, name) 列表,带重试。"""
    import akshare as ak
    last_err = None
    for i in range(retries):
        try:
            df = ak.stock_zh_a_spot()
            pairs = [
                (_strip_prefix(c), n)
                for c, n in zip(df["代码"], df["名称"])
            ]
            # 去重 + 过滤空名
            seen: set[str] = set()
            out: list[tuple[str, str]] = []
            for code, name in pairs:
                if not code or not name or code in seen:
                    continue
                seen.add(code)
                out.append((code, str(name).strip()))
            return out
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = 5 * (i + 1)
            print(f"  第 {i+1} 次失败: {type(e).__name__}: {str(e)[:60]}; 等 {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"拉取股票名称失败(重试 {retries} 次): {last_err}")


def upsert(db_path: Path, pairs: list[tuple[str, str]]) -> int:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_basic (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            updated_at TEXT
        )"""
    )
    now = datetime.now().isoformat(timespec="seconds")
    conn.executemany(
        "INSERT INTO stock_basic(code, name, updated_at) VALUES (?,?,?) "
        "ON CONFLICT(code) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at",
        [(c, n, now) for c, n in pairs],
    )
    n = conn.total_changes
    conn.commit()
    conn.close()
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="建/更新 stock_basic 股票名称表")
    ap.add_argument("--refresh", action="store_true", help="保留表结构,覆盖名称")
    args = ap.parse_args()

    if not DB_PATH.parent.exists():
        print(f"❌ 数据库目录不存在: {DB_PATH.parent}", file=sys.stderr)
        return 1

    print(f"DB: {DB_PATH}", flush=True)
    print("拉取全市场股票名称(akshare 新浪 spot)...", flush=True)
    t0 = time.time()
    pairs = fetch_all_names()
    print(f"  拿到 {len(pairs)} 条,耗时 {time.time()-t0:.1f}s", flush=True)

    n = upsert(DB_PATH, pairs)
    print(f"✅ 写入 stock_basic: {n} 行(INSERT or UPDATE)", flush=True)

    # 抽样校验
    conn = sqlite3.connect(DB_PATH)
    for r in conn.execute("SELECT code, name FROM stock_basic WHERE code IN ('600000','000001','300750','688981') ORDER BY code"):
        print(f"  {r[0]} -> {r[1]}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())