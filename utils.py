# -*- coding: UTF-8 -*-
import datetime


# 是否是工作日
def is_weekday():
    return datetime.datetime.today().weekday() < 5