"""通知 Facade：按配置选择具体推送通道。"""

from sequoia_x.core.config import Settings
from sequoia_x.notify.feishu import FeishuNotifier
from sequoia_x.notify.serverchan3 import ServerChan3Notifier

_CHANNELS = {
    "feishu": FeishuNotifier,
    "serverchan3": ServerChan3Notifier,
}


class NotifyFacade:
    """对调用方隐藏具体通知通道。"""

    def __init__(self, settings: Settings) -> None:
        channel_class = _CHANNELS[settings.notify_channel]
        self._channel: FeishuNotifier | ServerChan3Notifier = channel_class(settings)

    def send(
        self,
        symbols: list[str],
        strategy_name: str,
        webhook_key: str = "default",
    ) -> None:
        """通过配置选中的通道发送消息。"""
        self._channel.send(symbols, strategy_name, webhook_key)
