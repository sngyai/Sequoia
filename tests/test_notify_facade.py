"""通知 Facade 测试。"""

from unittest.mock import MagicMock, patch

from sequoia_x.core.config import Settings
from sequoia_x.notify.facade import NotifyFacade


def test_facade_selects_feishu() -> None:
    settings = Settings(notify_channel="feishu", _env_file=None)
    channel = MagicMock()
    channel.send.return_value = True
    with patch.dict(
        "sequoia_x.notify.facade._CHANNELS",
        {"feishu": lambda _: channel},
    ):
        result = NotifyFacade(settings).send(["000001"], "Test", "turtle")

    assert result is None
    channel.send.assert_called_once_with(["000001"], "Test", "turtle")


def test_facade_selects_serverchan3() -> None:
    settings = Settings(notify_channel="serverchan3", _env_file=None)
    channel = MagicMock()
    channel.send.return_value = True
    with patch.dict(
        "sequoia_x.notify.facade._CHANNELS",
        {"serverchan3": lambda _: channel},
    ):
        result = NotifyFacade(settings).send(["000001"], "Test", "turtle")

    assert result is None
    channel.send.assert_called_once_with(["000001"], "Test", "turtle")
