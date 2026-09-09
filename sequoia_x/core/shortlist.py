"""精选漏斗模块：多策略候选池 -> 每日 Top N 短名单。

漏斗规则（依次过滤）：
1. 剔除风险警示股（名称含 ST/退）
2. 流动性过滤：最近交易日成交额 >= 5 亿
3. 共振排序：命中策略数降序，其次成交额降序
4. 取前 N 只
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sequoia_x.core.logger import get_logger

if TYPE_CHECKING:
    from sequoia_x.data.engine import DataEngine

logger = get_logger(__name__)

# 流动性门槛：最近交易日成交额（元）
MIN_TURNOVER: float = 5e8

# 策略类名 -> 推送展示名
STRATEGY_LABELS: dict[str, str] = {
    "MaVolumeStrategy": "均线",
    "TurtleTradeStrategy": "海龟",
    "HighTightFlagStrategy": "旗形",
    "LimitUpShakeoutStrategy": "洗盘",
    "UptrendLimitDownStrategy": "反包",
    "RpsBreakoutStrategy": "RPS",
    "PrivatePlacementStrategy": "定增",
}


@dataclass
class ShortlistItem:
    """精选名单条目。"""

    code: str
    name: str
    hits: list[str] = field(default_factory=list)  # 命中的策略类名
    turnover: float = 0.0  # 最近交易日成交额（元）

    @property
    def labels(self) -> str:
        """命中策略的展示名，如 '海龟+RPS'。"""
        return "+".join(STRATEGY_LABELS.get(h, h) for h in self.hits)


def fetch_all_stock_names() -> dict[str, str]:
    """拉取全市场 {code: name}：优先 akshare（单次 HTTP，盘中更稳），失败回退 baostock。

    两者都失败时返回空 dict，调用方应跳过 ST 过滤（宁可放过不可误杀）。
    """
    try:
        import akshare as ak

        df = ak.stock_info_a_code_name()
        mapping = {
            str(code): str(name)
            for code, name in zip(df["code"], df["name"])
        }
        if mapping:
            return mapping
        logger.warning("akshare 返回空名称表，回退 baostock")
    except Exception as exc:
        logger.warning(f"akshare 拉取名称失败，回退 baostock: {exc}")

    import baostock as bs

    lg = bs.login()
    if lg.error_code != "0":
        logger.warning(f"baostock 登录失败，本次跳过 ST 过滤: {lg.error_msg}")
        return {}
    try:
        rs = bs.query_stock_basic(code_name="", code="")
        mapping: dict[str, str] = {}
        while rs.next():
            row = rs.get_row_data()
            mapping[row[0].split(".")[-1]] = row[1]
        return mapping
    except Exception as exc:
        logger.warning(f"baostock 拉取名称失败，本次跳过 ST 过滤: {exc}")
        return {}
    finally:
        bs.logout()


def _is_risk_warning(name: str) -> bool:
    """风险警示股：名称含 ST（不区分大小写）或 退。"""
    return "ST" in name.upper() or "退" in name


def build_shortlist(
    strategy_results: dict[str, list[str]],
    engine: DataEngine,
    top_n: int = 5,
) -> list[ShortlistItem]:
    """从各策略选股结果构建每日精选短名单。

    Args:
        strategy_results: {策略类名: 选中的股票代码列表}。
        engine: DataEngine，用于查询最近交易日成交额。
        top_n: 精选名单数量上限。

    Returns:
        按共振数、成交额降序排列的 ShortlistItem 列表，最多 top_n 个。
    """
    all_codes: set[str] = set()
    for codes in strategy_results.values():
        all_codes.update(codes)
    if not all_codes:
        logger.info("精选漏斗：无候选股票")
        return []

    # 1) 剔除风险警示股（名称拉取失败时自动跳过该层）
    names = fetch_all_stock_names()
    if names:
        before = len(all_codes)
        all_codes = {
            c for c in all_codes if not _is_risk_warning(names.get(c, ""))
        }
        logger.info(f"精选漏斗：剔除风险警示股 {before - len(all_codes)} 只，剩 {len(all_codes)} 只")

    # 2) 流动性过滤
    turnover = engine.get_latest_turnover()
    all_codes = {c for c in all_codes if turnover.get(c, 0.0) >= MIN_TURNOVER}
    logger.info(f"精选漏斗：成交额>={MIN_TURNOVER / 1e8:.0f}亿过滤后剩 {len(all_codes)} 只")
    if not all_codes:
        return []

    # 3) 共振数 + 成交额降序
    items = [
        ShortlistItem(
            code=c,
            name=names.get(c, c),
            hits=[s for s, codes in strategy_results.items() if c in codes],
            turnover=turnover[c],
        )
        for c in all_codes
    ]
    items.sort(key=lambda it: (len(it.hits), it.turnover), reverse=True)

    shortlist = items[:top_n]
    logger.info(
        "精选漏斗完成：" + "、".join(f"{it.code} {it.name}({it.labels})" for it in shortlist)
    )
    return shortlist
