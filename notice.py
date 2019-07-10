# -*- encoding: UTF-8 -*-
import settings


# 可以实现自己的推送逻辑（例如发送到手机上）


def strategy(msg=None):
    if msg is None or not msg:
        msg = "今日没有符合条件的股票"
    if settings.NOTIFY:
        print(msg)


def statistics(msg=None):
    if settings.NOTIFY:
        print(msg)
