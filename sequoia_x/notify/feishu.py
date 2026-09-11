"""飞书通知模块：将选股结果通过 Webhook 推送至飞书群。"""

import json
from datetime import date
import threading
from collections import defaultdict
import sqlite3
import baostock as bs
import requests

from sequoia_x.core.config import Settings
from sequoia_x.core.logger import get_logger

logger = get_logger(__name__)


class FeishuNotifier:
    """飞书 Webhook 推送器。

    根据策略的 webhook_key 路由到对应的飞书机器人。
    若 webhook_key 未在 Settings.strategy_webhooks 中配置，
    则 fallback 到 Settings.feishu_webhook_url。
    """
    # 类级别的线程锁
    _lock = threading.Lock()
    # baostock 连接池
    _bs_pool = []
    _bs_pool_lock = threading.Lock()
    _bs_max_pool_size = 4

    def __init__(self, settings: Settings) -> None:
        """
        初始化 FeishuNotifier。

        Args:
            settings: Settings 实例，提供 Webhook URL 配置。
        """
        self.settings = settings
        self.db_path = settings.db_path

    @staticmethod
    def _to_xueqiu_code(code: str) -> str:
        """将纯数字代码转为雪球格式：6开头→SH，4/8开头→BJ，其余→SZ。"""
        if code.startswith("6"):
            return f"SH{code}"
        elif code.startswith(("4", "8")):
            return f"BJ{code}"
        return f"SZ{code}"

    @staticmethod
    def _get_stock_names(symbols: list[str], db_path: str) -> dict[str, str]:
        """优先从本地 SQLite 批量查询股票名称，未命中再通过 baostock 批量查询，返回 {code: name} 映射。"""
        # 使用线程安全的数据结构
        mapping = defaultdict(str)
        missed_codes = []
        to_insert = []

        # 1. 确保表存在，并优先从本地 stock_name 表查询
        with FeishuNotifier._lock:
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS stock_name (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL UNIQUE, name TEXT NOT NULL)"
                )
                conn.execute("BEGIN TRANSACTION")
                try:
                    for code in symbols:
                        row = conn.execute(
                            "SELECT name FROM stock_name WHERE symbol = ?", (code,)
                        ).fetchone()
                        if row:
                            mapping[code] = row[0]
                            logger.debug(f"找到股票 [来源: local_db]: 代码={code}, 名称={row[0]}")
                        else:
                            missed_codes.append(code)
                            logger.debug(f"未找到股票 [来源: local_db]: 代码={code}")
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    logger.error(f"本地数据库查询失败: {e}")
                    raise

        # 2. 本地未命中的部分，走 baostock 查询
        if missed_codes:
            bs_conn = FeishuNotifier._get_bs_connection()
            try:
                for code in missed_codes:
                    # 拼接 prefix 供 baostock 使用
                    prefix = "sh" if code.startswith(("6", "9")) else "sz"
                    bs_code = f"{prefix}.{code}"
                    
                    rs = bs.query_stock_basic(code=bs_code)
                    while rs.next():
                        row = rs.get_row_data()
                        mapping[code] = row[1]  # 第2个字段是股票名称
                        to_insert.append((code, row[1]))
                        logger.debug(f"找到股票 [来源: baostock]: 代码={code}, 名称={row[1]}")
            finally:
                FeishuNotifier._release_bs_connection(bs_conn)

            # 3. 将 baostock 查询到的结果保存到本地 stock_name 表
            if to_insert:
                with FeishuNotifier._lock:
                    with sqlite3.connect(db_path) as conn:
                        conn.execute("BEGIN TRANSACTION")
                        try:
                            conn.executemany(
                                "INSERT OR IGNORE INTO stock_name (symbol, name) VALUES (?, ?)",
                                to_insert,
                            )
                            conn.commit()
                            logger.debug(f"已将 {len(to_insert)} 条股票信息保存至本地 stock_name 表")
                        except Exception as e:
                            conn.rollback()
                            logger.error(f"保存股票信息到本地数据库失败: {e}")
                            raise

        return dict(mapping)

    @classmethod
    def _get_bs_connection(cls):
        """从连接池获取 baostock 连接"""
        with cls._bs_pool_lock:
            if cls._bs_pool:
                return cls._bs_pool.pop()
            lg = bs.login()
            if lg.error_code != '0':
                raise RuntimeError(f"baostock 登录失败: {lg.error_msg}")
            return True

    @classmethod
    def _release_bs_connection(cls, conn):
        """释放 baostock 连接到连接池"""
        with cls._bs_pool_lock:
            if len(cls._bs_pool) < cls._bs_max_pool_size:
                cls._bs_pool.append(conn)
            else:
                bs.logout()

    def _build_card(self, symbols: list[str], strategy_name: str, strategy_descript: str) -> dict:
        today = date.today().strftime("%Y-%m-%d")
        names = self._get_stock_names(symbols, self.db_path)

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
                            "content": f"**日期：** {today}\n**策略：** {strategy_descript}\n**选股数量：** {len(symbols)}",
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
        strategy_descript: str,
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
        payload = self._build_card(symbols, strategy_name, strategy_descript)

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
