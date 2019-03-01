# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging


# TODO 真实波动幅度（ATR）放大
# 最后一个交易日收市价从下向上突破指定区间内最高价
def check_breakthrough(stock, data, end_date=None, threshold=60):
    max_price = 0
    data = data.loc[:end_date]
    data = data.tail(n=threshold+1)
    if data.size < threshold + 1:
        logging.info("{0}:样本小于{1}天...\n".format(stock, threshold))
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


# 收盘价高于N日均线
def check_ma(stock, data, end_date=None, ma_days=250):
    if data.size < ma_days:
        logging.info("{0}:样本小于{1}天...\n".format(stock, ma_days))
        return False

    ma_tag = 'ma' + str(ma_days)
    data[ma_tag] = pd.Series(tl.MA(data['close'].values, ma_days), index=data.index.values)

    begin_date = data.iloc[0].date
    if end_date is not None:
        if end_date < begin_date:  # 该股票在end_date时还未上市
            logging.info("{}在{}时还未上市".format(stock, end_date))
            return False
    data = data.loc[:end_date]

    last_close = data.iloc[-1]['close']
    last_ma = data.iloc[-1][ma_tag]
    if last_close > last_ma:
        return True
    else:
        return False


# 量比大于3.0
def check_volume(code_name, data, end_date=None, threshold=60):
    stock = code_name[0]
    name = code_name[1]
    total_vol = 0
    data = data.loc[:end_date]
    data = data.tail(n=threshold + 1)
    if data.size < threshold + 1:
        logging.info("{0}:样本小于{1}天...\n".format(stock, threshold))
        return False

    # 最后一天收盘价
    last_close = data.iloc[-1]['close']
    # 最后一天成交量
    last_vol = data.iloc[-1]['volume']

    data = data.head(n=threshold)

    for index, row in data.iterrows():
        total_vol += float(row['volume'])

    mean_vol = total_vol / threshold
    vol_ratio = last_vol / mean_vol
    if vol_ratio >= 3:

        msg = "*{0}({1}) 量比：{2:.2f}\n\t收盘价：{3}\n".format(name, stock, vol_ratio, last_close)
        logging.info(msg)
        return True
    else:
        return False
