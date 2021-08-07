import unittest

import settings
from push import push
from push import strategy
from push import statistics
import logging


def test_push():
    settings.init()
    push("测试")


def test_strategy():
    settings.init()
    strategy("")
    strategy("1")


logging.basicConfig(format='%(asctime)s %(message)s', filename='../sequoia.log')
logging.getLogger().setLevel(logging.INFO)
