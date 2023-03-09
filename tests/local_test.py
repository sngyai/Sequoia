# !/usr/bin/env python
# -*-coding:utf-8 -*-

"""
# File       : local_test
# Time       ：2023/3/3 20:40
# Author     ：qunzhong
# version    ：python 3.8
# Description：
"""
import datetime

if __name__ == '__main__':
    # just for local test
    current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_filename = 'sequoia-{}.log'.format(current_time)
    print(log_filename)
