"""海龟交易策略：20日新高突破 + 成交额过亿 + 动量阳线过滤。"""

import pandas as pd

from sequoia_x.core.logger import get_logger
from sequoia_x.strategy.base import BaseStrategy

logger = get_logger(__name__)


class TurtleTradeStrategy(BaseStrategy):
    """海龟交易策略（A股防诱多改良版）。

    选股条件（向量化，严禁 iterrows）：
    1. 突破新高：今日 close > 前20个交易日 high 的最大值
    2. 流动性：今日 turnover > 100,000,000
    3. 防诱多过滤：今日必须是实体阳线（今日 close > 今日 open），且必须真涨（今日 close > 昨日 close）

    Attributes:
        webhook_key: 路由到 'turtle' 专属飞书机器人。
    """

    webhook_key: str = "turtle"
    _MIN_BARS: int = 21  # 至少需要 21 根 K 线（20日窗口 + 当日）

    def _get_market_caps(self, symbols: list[str]) -> dict[str, float]:
        """估算候选股票的流通市值，用于排序（完全本地化，不依赖 baostock）。

        1) 从本地库取每只候选最新一行的「流通股本」(outstanding_share, 真实股数)
        2) 取一次新浪快照(stock_zh_a_spot)的「最新价」(不复权)做市值估算：
           cap = 流通股本 × 最新价
        任何一步失败都优雅降级（退化为按流通股本排序），不会让选股崩溃。
        """
        import sqlite3

        db_path = self.settings.db_path
        caps: dict[str, float] = {}

        # 1) 取各候选最新流通股本
        try:
            with sqlite3.connect(db_path) as conn:
                for sym in symbols:
                    row = conn.execute(
                        "SELECT outstanding_share FROM stock_daily "
                        "WHERE symbol=? ORDER BY date DESC LIMIT 1",
                        (sym,),
                    ).fetchone()
                    if row and row[0] is not None:
                        caps[sym] = float(row[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"读取流通股本失败：{exc}")
            return {}

        if not caps:
            return {}

        # 2) 取新浪最新价，算市值
        try:
            import akshare as ak

            spot = ak.stock_zh_a_spot()
            price_map: dict[str, float] = {}
            for _, r in spot.iterrows():
                code = str(r.get("代码", "")).zfill(6)
                price = r.get("最新价")
                try:
                    price_map[code] = float(price)
                except (TypeError, ValueError):
                    continue
            for sym in list(caps):
                p = price_map.get(sym)
                if p:
                    caps[sym] = caps[sym] * p
                # 拿不到最新价则保留流通股本原值（按股数排序，仍是合理的市值代理）
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"新浪最新价获取失败，TurtleTrade 市值排序退化为按流通股本：{exc}"
            )

        return caps

    def run(self) -> list[str]:
        """
        遍历全市场，返回满足海龟突破条件的股票代码列表。
        """
        symbols = self.engine.get_local_symbols()
        candidates: list[str] = []

        for symbol in symbols:
            try:
                df = self.engine.get_ohlcv(symbol)
                if len(df) < self._MIN_BARS:
                    continue

                # 向量化：前20日 high 的滚动最大值（不含当日，shift(1) 后取 rolling(20)）
                df["high_20"] = df["high"].shift(1).rolling(20).max()

                last = df.iloc[-1]
                prev = df.iloc[-2]  # 获取昨日数据，用于对比

                if pd.isna(last["high_20"]):
                    continue

                # 核心条件 1：突破前 20 天最高点
                breakout = last["close"] > last["high_20"]
                # 核心条件 2：流动性过亿
                liquid = last["turnover"] > 100_000_000

                # 【新增防守条件】拒绝郑州煤电式的高开低走大阴线！
                is_yang = last["close"] > last["open"]   # 实体必须是阳线（红柱）
                is_up = last["close"] > prev["close"]    # 必须是真涨，不能是假阳线

                if breakout and liquid and is_yang and is_up:
                    candidates.append(symbol)

            except Exception as exc:
                logger.warning(f"[{symbol}] TurtleTradeStrategy 计算失败：{exc}")
                continue

        # 按流通市值从大到小排序
        if candidates:
            market_caps = self._get_market_caps(candidates)
            candidates.sort(key=lambda s: market_caps.get(s, 0), reverse=True)

        logger.info(f"TurtleTradeStrategy 选出 {len(candidates)} 只股票")
        return candidates