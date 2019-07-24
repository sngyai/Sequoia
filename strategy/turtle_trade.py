# -*- coding: UTF-8 -*-

# 有关DataFrame的操作详见https://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing

import logging
import math

import talib as tl
import db
import utils

# 总市值
BALANCE = 200000


# 最后一个交易日收市价为指定区间内最高价
def check_enter(code_name, data, end_date=None, threshold=60):
    max_price = 0
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    if data is None:
        return False
    data = data.tail(n=threshold)
    if len(data) < threshold:
        return False
    for index, row in data.iterrows():
        if row['close'] > max_price:
            max_price = float(row['close'])

    last_close = data.iloc[-1]['close']

    if last_close >= max_price:
        return True

    return False


# 最后一个交易日收市价为指定区间内最低价
def check_exit(code_name, data, end_date=None, threshold=10):
    if data is None:
        return True
    min_price = 9999
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold)
    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False
    for index, row in data.iterrows():
        if row['close'] < min_price:
            min_price = float(row['close'])

    last_close = data.iloc[-1]['close']

    if last_close <= min_price:
        return True

    return False


# 止损 todo 亏损达到账户总额的2%
def check_stop(code_name, data, position_data, end_date=None):
    if data is None:
        return True
    last_close = data.iloc[-1]['close']
    positions = position_data['positions']
    cost = position_data['cost']
    current_cap = 0
    for (position_price, position_size) in positions:
        current_cap += position_size * last_close * 100

    if cost - BALANCE / 50 > current_cap:
        return True
    return False


# 绝对波动幅度
def real_atr(n, amount):
    return n * amount


def calculate(code_name, data, end_date=None, threshold=20):
    begin_date = data.iloc[0].date
    if end_date is not None:
        if end_date < begin_date:  # 该股票在end_date时还未上市
            logging.debug("{}在{}时还未上市".format(code_name, end_date))
            return False

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]

    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False

    atr_list = tl.ATR(data['high'], data['low'], data['close'], timeperiod=threshold)
    atr = atr_list.iloc[-1]
    last_close = data.iloc[-1]['close']
    # 头寸规模
    position_size = math.floor(BALANCE / 100 / real_atr(atr, 100))
    t_shelve = db.ShelvePersistence()
    t_shelve.save(code_name, last_close, position_size)

 # last_close, position_size, atr
    result = (
        "N：{0}\n"
        "头寸规模：{1}手\n"
        "买入价格：{2:0.2f}，{3:0.2f}，{4:0.2f}，{5:0.2f}\n"
        "退出价格：{6:0.2f}\n\n"
            .format(atr, math.floor(BALANCE / 100 / real_atr(atr, 100)),
                    last_close,
                    last_close + atr,
                    last_close + atr * 2,
                    last_close + atr * 3,
                    last_close - atr * 2))
    return result

