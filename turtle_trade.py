# -*- coding: UTF-8 -*-

# 有关DataFrame的操作详见https://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing

import pandas as pd
import numpy
import math
import datetime
import dateutil
import tushare as ts
import pandas as pd
import utils
import threadpool

# 第一个N值样本天数
DAYS_MEASURE = 20


# 总市值
BALANCE = 200000


# 真实波动幅度
def atr(high, low, last_close):
    return max(high - low, high - last_close, last_close - low)


# N值
def n(pdn, atr):
    return (19 * pdn + atr) / 20


# 绝对波动幅度
def real_atr(n, price):
    return n * price


def calculate(stock, end_date=None):
    data_history = pd.read_hdf("data/" + stock + '.h5', 'data')

    # 截取制定日期(end_date) 前60个交易日日线， 默认为最近60个交易日日线
    data_history = data_history.loc[:end_date]
    data_history = data_history.tail(n=60)

    print(data_history)

    last_close = data_history.iloc[-1]['close']
    current_n = data_history.iloc[-1]['n']
    print(last_close)
    print("代码：{0}\n"
          "N：{1}\n"
          "头寸规模：{2}手\n"
          "买入价格：{3:0.2f}，{4:0.2f}，{5:0.2f}，{6:0.2f}\n"
          "退出价格：{7:0.2f}\n\n"
          .format(stock, current_n, math.floor(BALANCE/100/real_atr(current_n, 100)), last_close,
                  last_close + current_n,
                  last_close + current_n * 2,
                  last_close + current_n * 3,
                  last_close - current_n * 2))
    # TODO 最近6日N值比5日前N值高出50%并且成交量放大的股票纳入选股范围， 参考2017-09-26京东方A，2017-07-24鲁西化工
    return


calculate("000977")

