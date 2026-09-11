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
    strategy_name: str = "防诱多海龟"
    strategy_descript: str = "\n1. 20日新高突破 + 成交额过亿  \n2. 今日实体阳线且必须真涨"
    _MIN_BARS: int = 21  # 至少需要 21 根 K 线（20日窗口 + 当日）

    def _get_market_caps(self, symbols: list[str]) -> dict[str, float]:
        """通过 baostock 查询候选股票的流通市值（不复权收盘价 × 流通股本）。

        流通股本 = 成交量 / (换手率% / 100)
        流通市值 = 流通股本 × 不复权收盘价
        """
        from datetime import date
        import baostock as bs
        today_str = date.today().strftime("%Y-%m-%d")
        market_caps: dict[str, float] = {}
        
        # 先尝试登录
        lg = bs.login()
        if lg.error_code != "0":
            logger.error(f"baostock 登录失败: {lg.error_msg}")
            return market_caps

        try:
            for symbol in symbols:
                try:
                    bs_code = self.engine._to_baostock_code(symbol)
                    rs = bs.query_history_k_data_plus(
                        bs_code,
                        "close,volume,turn",
                        start_date=today_str,
                        end_date=today_str,
                        frequency="d",
                        adjustflag="3",  # 不复权，真实价格
                    )

                    # 检查查询结果
                    if rs.error_code != "0":
                        logger.warning(f"[{symbol}] 查询失败: {rs.error_msg}")
                        continue

                    # 检查是否有数据
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())

                    if not data_list:
                        logger.debug(f"[{symbol}] 无数据（可能非交易日）")
                        continue

                    # 处理数据
                    for row in data_list:
                        try:
                            # 检查空值
                            if not row[0] or not row[1] or not row[2]:
                                logger.warning(f"[{symbol}] 数据包含空值，close='{row[0]}', volume='{row[1]}', turn='{row[2]}'，跳过")
                                continue
                                
                            close = float(row[0])
                            volume = float(row[1])
                            turn = float(row[2])
                            
                            if turn > 0:
                                circulating_shares = volume / (turn / 100)
                                market_caps[symbol] = circulating_shares * close
                        except (ValueError, ZeroDivisionError, IndexError) as e:
                            logger.warning(f"[{symbol}] 数据处理失败: {e}")
                            continue

                except Exception as e:
                    logger.warning(f"[{symbol}] 查询异常: {e}")
                    continue

        finally:
            bs.logout()

        return market_caps

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
