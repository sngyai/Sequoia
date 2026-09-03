"""日常选股（绕开 baostock）。

官方 `main.py` 的日常模式第一步会调 `DataEngine.sync_today_bulk()`，
该函数依赖 baostock；一旦 IP 被风控拉黑，整条流程会直接异常退出。
本脚本跳过同步步骤，只做「跑策略 + 推飞书」，数据更新交给
`scripts/backfill_sina.py`（新浪源，可增量跑）。

完整日常流程（baostock 被封时）：

    1) .venv\\Scripts\\python.exe scripts/backfill_sina.py     # 增量补数据
    2) .venv\\Scripts\\python.exe scripts/run_daily.py         # 跑策略 + 推送

参数
----
--no-push    只打印选股结果，不推飞书（本地调试/查看用）
--only       只跑指定策略，逗号分隔，如 --only turtle,ma_volume
             可选标识：ma_volume / turtle / flag / shakeout / limit_down / rps / private
--composite  跨策略综合打分，取 Top-N（默认 20）推送一张卡片；
             与「每策略各推一条」的默认模式互斥，用于每日精简播报。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from sequoia_x.core.config import get_settings  # noqa: E402
from sequoia_x.core.logger import get_logger  # noqa: E402
from sequoia_x.data.engine import DataEngine  # noqa: E402
from sequoia_x.notify.feishu import FeishuNotifier  # noqa: E402
from sequoia_x.strategy.base import BaseStrategy  # noqa: E402
from sequoia_x.strategy.high_tight_flag import HighTightFlagStrategy  # noqa: E402
from sequoia_x.strategy.limit_up_shakeout import LimitUpShakeoutStrategy  # noqa: E402
from sequoia_x.strategy.ma_volume import MaVolumeStrategy  # noqa: E402
from sequoia_x.strategy.private_placement import PrivatePlacementStrategy  # noqa: E402
from sequoia_x.strategy.rps_breakout import RpsBreakoutStrategy  # noqa: E402
from sequoia_x.strategy.turtle_trade import TurtleTradeStrategy  # noqa: E402
from sequoia_x.strategy.uptrend_limit_down import UptrendLimitDownStrategy  # noqa: E402

# 与 main.py 保持一致的策略装配顺序
STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "ma_volume": MaVolumeStrategy,
    "turtle": TurtleTradeStrategy,
    "flag": HighTightFlagStrategy,
    "shakeout": LimitUpShakeoutStrategy,
    "limit_down": UptrendLimitDownStrategy,
    "rps": RpsBreakoutStrategy,
    "private": PrivatePlacementStrategy,
}

# 综合打分权重：数值越大代表该策略信号的优先级/可靠性越高
STRATEGY_WEIGHTS: dict[str, int] = {
    "turtle": 3,
    "rps": 3,
    "ma_volume": 2,
    "flag": 2,
    "shakeout": 2,
    "private": 2,
    "limit_down": 1,
}

# 综合选股每日上限（用户要求：每天 ≤ 20 只）
TOP_N: int = 20

# 用户不可交易的板块前缀（科创板 / 创业板 / 北交所），分推与综合模式均过滤
#   科创板: 688 / 689   创业板: 300 / 301   北交所: 4 / 8 开头（含 920 新号段）
EXCLUDED_BOARDS: tuple[str, ...] = ("688", "689", "300", "301", "4", "8", "920")


def _is_buyable(code: str) -> bool:
    """用户可交易板块（沪/深主板）才保留；其余一律过滤。"""
    return not code.startswith(EXCLUDED_BOARDS)


def _run_composite(
    keys: list[str],
    engine: DataEngine,
    settings,
    logger,
    notifier: FeishuNotifier | None,
) -> None:
    """跨策略综合打分：每策略给选中股票加权，取总分 Top-N 推送一张卡片。

    与默认「每策略各推一条」互斥，用于把每日播报压缩到 ≤ TOP_N 只。
    """
    results: dict[str, list[str]] = {}
    for key in keys:
        cls = STRATEGY_MAP[key]
        strategy = cls(engine=engine, settings=settings)
        name = type(strategy).__name__
        try:
            selected = strategy.run()
        except Exception as exc:  # noqa: BLE001
            print(f"{name} 执行失败：{type(exc).__name__} {exc}", flush=True)
            logger.exception(f"{name} 执行失败")
            results[key] = []
            continue
        results[key] = selected
        print(f"{name}: {len(selected)} 只", flush=True)

    score_map: dict[str, float] = {}
    vote_map: dict[str, int] = {}
    contrib: dict[str, list[str]] = {}
    for key, syms in results.items():
        w = STRATEGY_WEIGHTS.get(key, 1)
        for s in syms:
            if not _is_buyable(s):
                continue
            score_map[s] = score_map.get(s, 0) + w
            vote_map[s] = vote_map.get(s, 0) + 1
            contrib.setdefault(s, []).append(key)

    # 先按总分，再按命中策略数，最后按代码保证确定性
    ranked = sorted(
        score_map.keys(),
        key=lambda s: (score_map[s], vote_map[s], s),
        reverse=True,
    )
    top = ranked[:TOP_N]

    print(
        f"\n=== 综合打分 Top {len(top)}（共 {len(score_map)} 只候选）===",
        flush=True,
    )
    for s in top:
        print(
            f"  {s}  分={score_map[s]} 票数={vote_map[s]} 策略={contrib[s]}",
            flush=True,
        )

    if top and notifier:
        notifier.send_composite(top, score_map, vote_map, contrib)
    elif top:
        print("  （--no-push，未推送）", flush=True)
    else:
        print("  综合选股为空", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sequoia-X 日常选股（跳过 baostock 同步）")
    parser.add_argument("--no-push", action="store_true", help="只打印结果，不推飞书")
    parser.add_argument("--only", default="", help="只跑指定策略，逗号分隔标识")
    parser.add_argument(
        "--composite",
        action="store_true",
        help="跨策略综合打分，取 Top-N 推送一张卡片（每日精简播报）",
    )
    args = parser.parse_args()

    settings = get_settings()
    logger = get_logger(__name__)
    engine = DataEngine(settings)

    keys = [k.strip() for k in args.only.split(",") if k.strip()] or list(STRATEGY_MAP)
    unknown = [k for k in keys if k not in STRATEGY_MAP]
    if unknown:
        print(f"未知策略标识：{unknown}；可选：{list(STRATEGY_MAP)}")
        return

    notifier = None if args.no_push else FeishuNotifier(settings)

    if args.composite:
        _run_composite(keys, engine, settings, logger, notifier)
        return

    print(f"库内股票 {len(engine.get_local_symbols())} 只", flush=True)

    for key in keys:
        cls = STRATEGY_MAP[key]
        strategy = cls(engine=engine, settings=settings)
        name = type(strategy).__name__
        try:
            selected = strategy.run()
        except Exception as exc:  # noqa: BLE001
            print(f"{name} 执行失败：{type(exc).__name__} {exc}", flush=True)
            logger.exception(f"{name} 执行失败")
            continue

        # 过滤掉用户不可交易的板块（科创板/创业板/北交所）
        selected = [s for s in selected if _is_buyable(s)]

        print(f"{name}: {len(selected)} 只 -> {selected}", flush=True)

        if selected and notifier:
            notifier.send(
                symbols=selected,
                strategy_name=name,
                webhook_key=strategy.webhook_key,
            )
        elif selected:
            print(f"  （--no-push，未推送）", flush=True)


if __name__ == "__main__":
    main()
