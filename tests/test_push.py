import unittest

import settings
from push import push
from push import strategy
from push import statistics
import logging
import datetime


def test_push():
    settings.init()
    push("测试")


def test_strategy():
    settings.init()
    strategy("")
    strategy("1")


current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
log_filename = 'logs/test-push-{}.log'.format(current_time)
logging.basicConfig(format='%(asctime)s %(message)s', filename=log_filename)
logging.getLogger().setLevel(logging.INFO)
