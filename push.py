# -*- encoding: UTF-8 -*-

import logging
import settings
from wxpusher import WxPusher


def push(msg):
    if settings.config['push']['enable']:
        response = WxPusher.send_message(msg, uids=[settings.config['push']['wxpusher_uid']],
                                         token=settings.config['push']['wxpusher_token'])
        print(response)
    logging.info(msg)


def statistics(msg=None):
    push(msg)


def strategy(msg=None):
    if msg is None or not msg:
        msg = '今日没有符合条件的股票'
    push(msg)
