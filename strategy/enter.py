# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging


# TODO 真实波动幅度（ATR）放大
# 最后一个交易日收市价从下向上突破指定区间内最高价
def check_breakthrough(code_name, data, end_date=None, threshold=30):
    max_price = 0
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold+1)
    if data.size < threshold + 1:
        logging.info("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False

    # 最后一天收市价
    last_close = float(data.iloc[-1]['close'])
    last_open = float(data.iloc[-1]['open'])

    data = data.head(n=threshold)
    second_last_close = data.iloc[-1]['close']

    for index, row in data.iterrows():
        if row['close'] > max_price:
            max_price = float(row['close'])

    if last_close > max_price > second_last_close and max_price > last_open \
            and last_close / last_open > 1.06:
        return True
    else:
        return False


# 收盘价高于N日均线
def check_ma(code_name, data, end_date=None, ma_days=250):
    if data.size < ma_days:
        logging.info("{0}:样本小于{1}天...\n".format(code_name, ma_days))
        return False

    ma_tag = 'ma' + str(ma_days)
    data[ma_tag] = pd.Series(tl.MA(data['close'].values, ma_days), index=data.index.values)

    begin_date = data.iloc[0].date
    if end_date is not None:
        if end_date < begin_date:  # 该股票在end_date时还未上市
            logging.info("{}在{}时还未上市".format(code_name, end_date))
            return False
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]

    last_close = data.iloc[-1]['close']
    last_ma = data.iloc[-1][ma_tag]
    if last_close > last_ma:
        return True
    else:
        return False


# 上市日小于60天
def check_new(code_name, data, end_date=None, threshold=60):
    size = len(data.index)
    if size < threshold:
        return True
    else:
        return False


# 量比大于3.0
def check_volume(code_name, data, end_date=None, threshold=60):
    stock = code_name[0]
    name = code_name[1]
    total_vol = 0
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold + 1)
    if data.size < threshold + 1:
        logging.info("{0}:样本小于{1}天...\n".format(code_name, threshold))
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
    if vol_ratio >= 2:
        msg = "*{0} 量比：{1:.2f}\n\t收盘价：{2}\n".format(code_name, vol_ratio, last_close)
        logging.info(msg)
        return True
    else:
        return False


# 量比大于3.0
def check_continuous_volume(code_name, data, end_date=None, threshold=60, window_size=3):
    stock = code_name[0]
    name = code_name[1]
    data['vol_ma5'] = pd.Series(tl.MA(data['volume'].values, 5), index=data.index.values)
    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold + window_size)
    if data.size < threshold + window_size:
        logging.info("{0}:样本小于{1}天...\n".format(code_name, threshold+window_size))
        return False

    # 最后一天收盘价
    last_close = data.iloc[-1]['close']
    # 最后一天成交量
    last_vol = data.iloc[-1]['volume']

    data_front = data.head(n=threshold)
    data_end = data.tail(n=window_size)

    mean_vol = data_front.iloc[-1]['vol_ma5']

    for index, row in data_end.iterrows():
        if float(row['volume']) / mean_vol < 3.0:
            return False

    msg = "*{0} 量比：{1:.2f}\n\t收盘价：{2}\n".format(code_name, last_vol/mean_vol, last_close)
    logging.info(msg)
    return True
