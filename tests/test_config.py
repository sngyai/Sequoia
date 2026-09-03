"""配置管理属性测试。"""

from hypothesis import HealthCheck, given, settings as h_settings
from hypothesis import strategies as st


# Feature: sequoia-x-v2, Property 1: 环境变量覆盖配置默认值
@given(db_path=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/_.-")))
@h_settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_env_overrides_default(db_path: str, monkeypatch) -> None:
    """属性 1：任意合法 db_path 通过环境变量设置后，Settings 实例应反映该值。"""
    import sequoia_x.core.config as cfg_module
    monkeypatch.setenv("DB_PATH", db_path)
    monkeypatch.setattr(cfg_module, "_settings", None)
    from sequoia_x.core.config import Settings
    s = Settings()
    assert s.db_path == db_path


def test_notification_channels_are_optional(monkeypatch) -> None:
    """未配置通知通道时仍可初始化，用于回填等无需推送的流程。"""
    from sequoia_x.core.config import Settings

    monkeypatch.delenv("FEISHU_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SERVERCHAN3_SENDKEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.feishu_webhook_url is None
    assert settings.serverchan3_sendkey is None
    assert settings.notify_channel == "feishu"


def test_notify_channel_from_environment(monkeypatch) -> None:
    """NOTIFY_CHANNEL 环境变量应控制 Facade 使用的通知通道。"""
    from sequoia_x.core.config import Settings

    monkeypatch.setenv("NOTIFY_CHANNEL", "serverchan3")
    settings = Settings(_env_file=None)

    assert settings.notify_channel == "serverchan3"


def test_strategy_sendkey_overrides_default(monkeypatch) -> None:
    """策略专属环境变量优先，其他策略回落到默认 SendKey。"""
    from sequoia_x.core.config import Settings

    monkeypatch.setenv("STRATEGY_SENDKEY_TURTLE", "SCTturtle")
    settings = Settings(serverchan3_sendkey="SCTdefault", _env_file=None)

    assert settings.get_serverchan3_sendkey("turtle") == "SCTturtle"
    assert settings.get_serverchan3_sendkey("ma_volume") == "SCTdefault"


def test_strategy_webhook_overrides_default(monkeypatch) -> None:
    """飞书策略专属环境变量优先，其他策略回落到默认 Webhook。"""
    from sequoia_x.core.config import Settings

    monkeypatch.setenv("STRATEGY_WEBHOOK_TURTLE", "https://example.com/turtle")
    settings = Settings(feishu_webhook_url="https://example.com/default", _env_file=None)

    assert settings.get_webhook_url("turtle") == "https://example.com/turtle"
    assert settings.get_webhook_url("ma_volume") == "https://example.com/default"
