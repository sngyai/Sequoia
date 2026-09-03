"""Server酱³ 通知通道。"""

import re
from datetime import date
from typing import Any

import requests

from sequoia_x.core.config import Settings
from sequoia_x.core.logger import get_logger

logger = get_logger(__name__)


class ServerChan3Notifier:
    """通过 Server酱³ 推送选股结果。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @staticmethod
    def _to_xueqiu_code(code: str) -> str:
        if code.startswith("6"):
            return f"SH{code}"
        if code.startswith(("4", "8")):
            return f"BJ{code}"
        return f"SZ{code}"

    @staticmethod
    def _get_stock_names(symbols: list[str]) -> dict[str, str]:
        import baostock as bs

        bs.login()
        mapping: dict[str, str] = {}
        try:
            for code in symbols:
                prefix = "sh" if code.startswith(("6", "9")) else "sz"
                result = bs.query_stock_basic(code=f"{prefix}.{code}")
                while result.next():
                    row = result.get_row_data()
                    mapping[code] = row[1]
        finally:
            bs.logout()
        return mapping

    @staticmethod
    def _build_url(sendkey: str) -> str | None:
        if sendkey.startswith("sctp"):
            match = re.match(r"^sctp(\d+)t", sendkey)
            if not match:
                return None
            node_number = match.group(1)
            return f"https://{node_number}.push.ft07.com/send/{sendkey}.send"
        return f"https://sctapi.ftqq.com/{sendkey}.send"

    def _build_message(self, symbols: list[str], strategy_name: str) -> tuple[str, str]:
        names = self._get_stock_names(symbols)
        stocks: list[str] = []
        for code in symbols:
            xueqiu_code = self._to_xueqiu_code(code)
            name = names.get(code, xueqiu_code)
            stocks.append(
                f"- [{name}（{code}）](https://xueqiu.com/S/{xueqiu_code})"
            )

        stock_text = "\n".join(stocks) if stocks else "- （无选股结果）"
        title = f"📈 Sequoia-X 选股播报 | {strategy_name}"
        content = (
            f"**日期：** {date.today():%Y-%m-%d}\n\n"
            f"**策略：** {strategy_name}\n\n"
            f"**选股数量：** {len(symbols)}\n\n"
            "---\n\n"
            f"### 选股列表\n\n{stock_text}"
        )
        return title, content

    @staticmethod
    def _is_success(response_data: Any) -> bool:
        if not isinstance(response_data, dict):
            return False
        return response_data.get("code") in (None, 0, "0")

    def send(
        self,
        symbols: list[str],
        strategy_name: str,
        notification_key: str = "default",
    ) -> bool:
        sendkey = self.settings.get_serverchan3_sendkey(notification_key)
        if not sendkey:
            logger.warning(f"Server酱³ SendKey 未配置，跳过推送 [{notification_key}]")
            return False

        url = self._build_url(sendkey)
        if url is None:
            logger.error(f"Server酱³ SendKey 格式无效 [{notification_key}]")
            return False

        try:
            title, content = self._build_message(symbols, strategy_name)
            response = requests.post(
                url,
                json={"title": title, "desp": content, "options": {}},
                headers={"Content-Type": "application/json;charset=utf-8"},
                timeout=10,
            )
            response_data = response.json()
            if response.status_code != 200 or not self._is_success(response_data):
                logger.error(
                    f"Server酱³ 推送失败 [{notification_key}] "
                    f"HTTP状态={response.status_code} 响应={response.text}"
                )
                return False
        except Exception as exc:
            logger.error(f"Server酱³ 推送异常 [{notification_key}]：{exc}")
            return False

        logger.info(f"Server酱³ 推送成功 [{notification_key}]，共 {len(symbols)} 只股票")
        return True
