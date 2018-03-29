# -*- coding: UTF-8 -*-

import talib as tl
import pandas as pd


# TODO 真实波动幅度（ATR）放大
# 最后一个交易日收市价为指定区间内最高价
def check_max_price(stock, data, end_date=None, threshold=60):
    max_price = 0
    data = data.loc[:end_date]
    data = data.tail(n=threshold)
    if data.size < threshold:
        print("{0}:样本小于{1}天...\n".format(stock, threshold))
        return False
    for index, row in data.iterrows():
        if row['close'] > max_price:
            max_price = float(row['close'])

    last_close = data.iloc[-1]['close']

    if last_close >= max_price:
        return True

    return False


# 最后一个交易日收市价突破指定区间内最高价
def check_breakthrough(stock, data, end_date=None, threshold=60):
    max_price = 0
    data = data.loc[:end_date]
    data = data.tail(n=threshold+1)
    if data.size < threshold + 1:
        print("{0}:样本小于{1}天...\n".format(stock, threshold))
        return False

    # 最后一天收市价
    last_close = data.iloc[-1]['close']

    data = data.head(n=threshold)
    for index, row in data.iterrows():
        if row['close'] > max_price:
            max_price = float(row['close'])

    if last_close > max_price > data.iloc[-1]['close']:
        return True
    else:
        return False


# 均线突破
def check_ma(stock, data, end_date=None, ma_days=250):
    begin_date = data.iloc[0].name
    if end_date is not None:
        if end_date < begin_date:  # 该股票在end_date时还未上市
            print("{}在{}时还未上市".format(stock, end_date))
            return False
    data = data.loc[:end_date]
    if data.size < ma_days:
        print("{0}:样本小于{1}天...\n".format(stock, ma_days))
        return False

    data['ma'] = pd.Series(tl.MA(data['close'].values, ma_days), index=data.index.values)

    last_close = data.iloc[-1]['close']
    last_ma = data.iloc[-1]['ma']
    if last_close > last_ma:
        return True
    else:
        return False


# 量比大于3.0
def check_volume(stock, data, end_date=None, threshold=60):
    total_vol = 0
    data = data.loc[:end_date]
    data = data.tail(n=threshold+1)
    if data.size < threshold + 1:
        print("{0}:样本小于{1}天...\n".format(stock, threshold))
        return False

    # 最后一天成交量
    last_vol = data.iloc[-1]['volume']

    data = data.head(n=threshold)

    for index, row in data.iterrows():
        total_vol += float(row['volume'])

    mean_vol = total_vol / threshold
    vol_ratio = last_vol / mean_vol
    if vol_ratio >= 3:
        print("{0}：量比：{1}\n".format(stock, vol_ratio))
        return True
    else:
        return False
