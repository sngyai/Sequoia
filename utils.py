# -*- coding: UTF-8 -*-
import datetime
from pandas.tseries.offsets import *

import xlrd
import pandas as pd
import os
import settings


# 是否是工作日
def is_weekday():
    return datetime.datetime.today().weekday() < 5