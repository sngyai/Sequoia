"""飞书通知模块：将选股结果通过 Webhook 推送至飞书群。"""

import json
import sqlite3
from datetime import date
from pathlib import Path

import requests

from sequoia_x.core.config import Settings
from sequoia_x.core.logger import get_logger

logger = get_logger(__name__)

# 股票名称本地缓存路径:sequoia_x/notify/feishu.py -> 根目录/data/sequoia_v2.db
_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "sequoia_v2.db"


class FeishuNotifier:
    """飞书 Webhook 推送器。

    根据策略的 webhook_key 路由到对应的飞书机器人。
    若 webhook_key 未在 Settings.strategy_webhooks 中配置，
    则 fallback 到 Settings.feishu_webhook_url。
    """

    def __init__(self, settings: Settings) -> None:
        """
        初始化 FeishuNotifier。

        Args:
            settings: Settings 实例，提供 Webhook URL 配置。
        """
        self.settings = settings

    @staticmethod
    def _to_xueqiu_code(code: str) -> str:
        """将纯数字代码转为雪球格式：6开头→SH，4/8开头→BJ，其余→SZ。"""
        if code.startswith("6"):
            return f"SH{code}"
        elif code.startswith(("4", "8")):
            return f"BJ{code}"
        return f"SZ{code}"

    @staticmethod
    def _get_stock_names(symbols: list[str]) -> dict[str, str]:
        """从本地 stock_basic 表批量查股票名称。

        之前用 baostock 逐只 query_stock_basic,baostock 被风控后 socket 抛 WinError 10057,
        导致 _build_card 失败、推送连环崩。改为本地 sqlite 一次性查,失败时优雅降级到代码。
        """
        if not symbols:
            return {}
        mapping: dict[str, str] = {}
        try:
            conn = sqlite3.connect(_DB_PATH)
            placeholders = ",".join("?" * len(symbols))
            rows = conn.execute(
                f"SELECT code, name FROM stock_basic WHERE code IN ({placeholders})",
                symbols,
            ).fetchall()
            mapping = {code: name for code, name in rows}
            conn.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"本地查股票名称失败({type(exc).__name__}: {exc});将使用代码占位"
            )
        return mapping

    def _build_card(self, symbols: list[str], strategy_name: str) -> dict:
        today = date.today().strftime("%Y-%m-%d")
        names = self._get_stock_names(symbols)

        links: list[str] = []
        for code in symbols:
            xq_code = self._to_xueqiu_code(code)
            name = names.get(code, xq_code)
            links.append(f"[{name}](https://xueqiu.com/S/{xq_code})")

        symbol_text = " ".join(links) if links else "（无选股结果）"

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📈 Sequoia-X 选股播报 | {strategy_name}",
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**日期：** {today}\n**策略：** {strategy_name}\n**选股数量：** {len(symbols)}",
                        },
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**选股列表：**\n{symbol_text}",
                        },
                    },
                ],
            },
        }

    def send(
        self,
        symbols: list[str],
        strategy_name: str,
        webhook_key: str = "default",
    ) -> None:
        """
        将选股结果格式化为飞书卡片消息并 POST 至对应 Webhook。

        根据 webhook_key 从 Settings 中查找专属 URL；
        若未配置，则 fallback 到 feishu_webhook_url。

        Args:
            symbols: 选股结果代码列表。
            strategy_name: 策略名称，用于卡片标题。
            webhook_key: 策略标识，用于路由到对应飞书机器人。

        Raises:
            不抛出异常，HTTP 失败时记录 ERROR 日志。
        """
        url = self.settings.get_webhook_url(webhook_key)
        payload = self._build_card(symbols, strategy_name)

        try:
            resp = requests.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            # 解析飞书真正的返回体
            resp_json = resp.json()

            # 飞书真正的成功标志是内部的 code == 0
            if resp.status_code != 200 or resp_json.get("code") != 0:
                logger.error(
                    f"飞书推送失败 [{webhook_key}] "
                    f"HTTP状态={resp.status_code} 飞书响应={resp.text}"
                )
            else:
                logger.info(f"飞书推送成功 [{webhook_key}]，共 {len(symbols)} 只股票")

        except requests.RequestException as exc:
            logger.error(f"飞书推送请求异常 [{webhook_key}]：{exc}")

    def _build_composite_card(
        self,
        symbols: list[str],
        score_map: dict[str, float],
        vote_map: dict[str, int],
        contrib: dict[str, list[str]],
    ) -> dict:
        today = date.today().strftime("%Y-%m-%d")
        names = self._get_stock_names(symbols)

        lines: list[str] = []
        for code in symbols:
            xq_code = self._to_xueqiu_code(code)
            name = names.get(code, xq_code)
            lines.append(
                f"[{name}](https://xueqiu.com/S/{xq_code}) "
                f"｜ 分{score_map[code]} ｜ {','.join(contrib[code])}"
            )
        body = "\n".join(lines) if lines else "（无选股结果）"

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"📈 Sequoia-X 综合选股 | Top{len(symbols)}",
                    },
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**日期：** {today}\n"
                                f"**模式：** 跨策略综合打分（权重合并）\n"
                                f"**选股数量：** {len(symbols)}"
                            ),
                        },
                    },
                    {"tag": "hr"},
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**选股列表（分=综合得分，命中策略见右）：**\n{body}",
                        },
                    },
                ],
            },
        }

    def send_composite(
        self,
        symbols: list[str],
        score_map: dict[str, float],
        vote_map: dict[str, int],
        contrib: dict[str, list[str]],
        webhook_key: str = "default",
    ) -> None:
        """推送一张「综合选股」卡片（跨策略打分 Top-N），路由到主机器人。

        与按策略分推的 send() 不同，这里把每日候选压缩成一张清单，
        每只附综合得分与命中策略，便于快速浏览。
        """
        url = self.settings.get_webhook_url(webhook_key)
        payload = self._build_composite_card(symbols, score_map, vote_map, contrib)

        try:
            resp = requests.post(
                url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            resp_json = resp.json()
            if resp.status_code != 200 or resp_json.get("code") != 0:
                logger.error(
                    f"飞书综合推送失败 [{webhook_key}] "
                    f"HTTP状态={resp.status_code} 飞书响应={resp.text}"
                )
            else:
                logger.info(
                    f"飞书综合推送成功 [{webhook_key}]，共 {len(symbols)} 只股票"
                )
        except requests.RequestException as exc:
            logger.error(f"飞书综合推送请求异常 [{webhook_key}]：{exc}")
