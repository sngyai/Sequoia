"""Server酱³ 通知属性测试。"""

import logging
from unittest.mock import MagicMock, patch

from hypothesis import given, settings as h_settings
from hypothesis import strategies as st

from sequoia_x.core.config import Settings
from sequoia_x.notify.serverchan3 import ServerChan3Notifier


def make_settings(sendkey: str = "SCTtestkey") -> Settings:
    return Settings(
        db_path="data/test.db",
        start_date="2024-01-01",
        serverchan3_sendkey=sendkey,
        _env_file=None,
    )


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
    """send() 发出的 Markdown 正文包含全部选股代码。"""
    notifier = ServerChan3Notifier(make_settings())

    with (
        patch.object(notifier, "_get_stock_names", return_value={}),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 0}',
            json=MagicMock(return_value={"code": 0}),
        )
        assert notifier.send(symbols=symbols, strategy_name="TestStrategy") is True

    payload = mock_post.call_args.kwargs["json"]
    for symbol in symbols:
        assert symbol in payload["desp"]


@given(sendkey=st.from_regex(r"SCT[a-zA-Z0-9]{8,36}", fullmatch=True))
@h_settings(max_examples=50)
def test_notification_uses_standard_sendkey_url(sendkey: str) -> None:
    """普通 SendKey 应使用 sctapi.ftqq.com。"""
    notifier = ServerChan3Notifier(make_settings(sendkey))

    with (
        patch.object(notifier, "_get_stock_names", return_value={}),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 0}',
            json=MagicMock(return_value={"code": 0}),
        )
        notifier.send(symbols=["000001"], strategy_name="Test")

    assert mock_post.call_args.args[0] == f"https://sctapi.ftqq.com/{sendkey}.send"


def test_notification_uses_sctp_node_url() -> None:
    """sctp SendKey 应从键中提取节点号构造 Server酱³ 地址。"""
    sendkey = "sctp123tTestKey"
    notifier = ServerChan3Notifier(make_settings(sendkey))

    with (
        patch.object(notifier, "_get_stock_names", return_value={}),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 0}',
            json=MagicMock(return_value={"code": 0}),
        )
        notifier.send(symbols=["000001"], strategy_name="Test")

    assert mock_post.call_args.args[0] == (
        f"https://123.push.ft07.com/send/{sendkey}.send"
    )


def test_notification_uses_strategy_sendkey(monkeypatch) -> None:
    """策略专属 SendKey 优先于默认 SendKey。"""
    monkeypatch.setenv("STRATEGY_SENDKEY_TURTLE", "SCTturtle")
    notifier = ServerChan3Notifier(make_settings("SCTdefault"))

    with (
        patch.object(notifier, "_get_stock_names", return_value={}),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 0}',
            json=MagicMock(return_value={"code": 0}),
        )
        notifier.send(["000001"], "TurtleTrade", notification_key="turtle")

    assert mock_post.call_args.args[0] == "https://sctapi.ftqq.com/SCTturtle.send"


def test_missing_sendkey_skips_request() -> None:
    """未配置 Server酱³ 时应跳过，且不影响其他通知通道。"""
    notifier = ServerChan3Notifier(Settings(_env_file=None))
    with patch("requests.post") as mock_post:
        assert notifier.send(["000001"], "Test") is False
    mock_post.assert_not_called()


@given(status_code=st.integers(min_value=400, max_value=599))
@h_settings(max_examples=50)
def test_http_failure_logs_error(status_code: int) -> None:
    """非 200 响应应记录 ERROR 且返回 False。"""
    import sequoia_x.notify.serverchan3 as serverchan3_module

    notifier = ServerChan3Notifier(make_settings())
    notifier_logger = logging.getLogger(serverchan3_module.__name__)
    log_records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(record)

    handler = _ListHandler(logging.ERROR)
    notifier_logger.addHandler(handler)
    try:
        with (
            patch.object(notifier, "_get_stock_names", return_value={}),
            patch("requests.post") as mock_post,
        ):
            mock_post.return_value = MagicMock(
                status_code=status_code,
                text="error",
                json=MagicMock(return_value={"code": 1}),
            )
            assert notifier.send(["000001"], "Test") is False
    finally:
        notifier_logger.removeHandler(handler)

    assert any(record.levelno == logging.ERROR for record in log_records)


def test_api_failure_with_http_200_returns_false() -> None:
    """HTTP 200 但 Server酱返回错误码时仍应视为失败。"""
    notifier = ServerChan3Notifier(make_settings())
    with (
        patch.object(notifier, "_get_stock_names", return_value={}),
        patch("requests.post") as mock_post,
    ):
        mock_post.return_value = MagicMock(
            status_code=200,
            text='{"code": 1}',
            json=MagicMock(return_value={"code": 1}),
        )
        assert notifier.send(["000001"], "Test") is False
