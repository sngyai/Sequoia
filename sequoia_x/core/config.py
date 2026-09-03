"""配置管理模块：通过 pydantic-settings 从环境变量或 .env 文件加载系统配置。"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str = "data/sequoia_v2.db"
    start_date: str = "2024-01-01"
    notify_channel: Literal["feishu", "serverchan3"] = "feishu"
    feishu_webhook_url: str | None = None
    serverchan3_sendkey: str | None = None
    strategy_webhooks: dict[str, str] = {}
    strategy_sendkeys: dict[str, str] = {}

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # <--- 加上这一行！让 Pydantic 放行未定义的变量
    )

    def model_post_init(self, __context: object) -> None:
        """合并飞书 Webhook 与 Server酱³ SendKey 的策略专属环境变量。"""
        import os

        webhooks: dict[str, str] = dict(self.strategy_webhooks)
        sendkeys: dict[str, str] = dict(self.strategy_sendkeys)
        for key, value in os.environ.items():
            upper_key = key.upper()
            if upper_key.startswith("STRATEGY_WEBHOOK_"):
                strategy_key = key[len("STRATEGY_WEBHOOK_") :].lower()
                webhooks[strategy_key] = value
            if upper_key.startswith("STRATEGY_SENDKEY_"):
                strategy_key = key[len("STRATEGY_SENDKEY_") :].lower()
                sendkeys[strategy_key] = value

        object.__setattr__(self, "strategy_webhooks", webhooks)
        object.__setattr__(self, "strategy_sendkeys", sendkeys)

    def get_webhook_url(self, webhook_key: str) -> str | None:
        """返回策略对应的飞书 Webhook URL。"""
        return self.strategy_webhooks.get(webhook_key.lower(), self.feishu_webhook_url)

    def get_serverchan3_sendkey(self, webhook_key: str) -> str | None:
        """返回策略对应的 Server酱³ SendKey。"""
        return self.strategy_sendkeys.get(webhook_key.lower(), self.serverchan3_sendkey)


_settings: Settings | None = None


def get_settings() -> Settings:
    """返回全局 Settings 单例。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
