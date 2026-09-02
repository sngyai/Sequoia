"""飞书通知属性测试。"""

import json
import logging
from unittest.mock import MagicMock, patch

from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from sequoia_x.core.config import Settings
from sequoia_x.notify.feishu import FeishuNotifier


def make_settings(webhook_url: str = "https://example.com/default") -> Settings:
    return Settings(feishu_webhook_url=webhook_url, _env_file=None)


@given(
    symbols=st.lists(
        st.text(min_size=6, max_size=6, alphabet="0123456789"),
        min_size=1,
        max_size=10,
        unique=True,
    )
)
@h_settings(max_examples=50)
def test_notification_contains_all_symbols(symbols: list[str]) -> None:
    """飞书请求体应包含全部选股代码。"""
    notifier = FeishuNotifier(make_settings())
    with (
        patch(
            "sequoia_x.notify.feishu.FeishuNotifier._get_stock_names",
            return_value={},
        ),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 0}',
            json=MagicMock(return_value={"code": 0}),
        )
        notifier.send(symbols, "TestStrategy")

    body = json.loads(mock_post.call_args.kwargs["data"])
    card_text = json.dumps(body)
    for symbol in symbols:
        assert symbol in card_text


@given(
    webhook_url=st.from_regex(
        r"https://open\.feishu\.cn/open-apis/bot/v2/hook/[a-z0-9\-]{8,36}",
        fullmatch=True,
    )
)
@h_settings(max_examples=50)
def test_notification_uses_config_url(webhook_url: str) -> None:
    """飞书请求目标应使用配置的 Webhook URL。"""
    notifier = FeishuNotifier(make_settings(webhook_url))
    with (
        patch(
            "sequoia_x.notify.feishu.FeishuNotifier._get_stock_names",
            return_value={},
        ),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 0}',
            json=MagicMock(return_value={"code": 0}),
        )
        notifier.send(["000001"], "Test")

    assert mock_post.call_args.args[0] == webhook_url


def test_http_failure_logs_error() -> None:
    """飞书非 200 响应应记录 ERROR。"""
    import sequoia_x.notify.feishu as feishu_module

    notifier = FeishuNotifier(make_settings())
    notifier_logger = logging.getLogger(feishu_module.__name__)
    records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _ListHandler(logging.ERROR)
    notifier_logger.addHandler(handler)
    try:
        with (
            patch(
                "sequoia_x.notify.feishu.FeishuNotifier._get_stock_names",
                return_value={},
            ),
            patch("requests.post") as mock_post,
        ):
            mock_post.return_value = MagicMock(
                status_code=500,
                text="error",
                json=MagicMock(return_value={"code": 1}),
            )
            notifier.send(["000001"], "Test")
    finally:
        notifier_logger.removeHandler(handler)

    assert any(record.levelno == logging.ERROR for record in records)
