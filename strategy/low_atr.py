# -*- encoding: UTF-8 -*-
import pandas as pd
import talib as tl
import logging


# 低ATR成长策略
def check_low_increase(code_name, data, end_date=None, ma_short=30, ma_long=250, threshold=30):
    stock = code_name[0]
    name = code_name[1]
    if data.size < ma_long:
        logging.info("{0}:样本小于{1}天...\n".format(code_name, ma_long))
        return False

    # data['ma_short'] = pd.Series(tl.MA(data['close'].values, ma_short), index=data.index.values)
    # data['ma_long'] = pd.Series(tl.MA(data['close'].values, ma_long), index=data.index.values)

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]
    data = data.tail(n=threshold)
    inc_days = 0
    dec_days = 0
    if data.size < threshold:
        logging.info("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False

    # 区间最低点
    lowest_row = data.iloc[-1]
    # 区间最高点
    highest_row = data.iloc[-1]

    for index, row in data.iterrows():
        p_change = float(row['p_change'])

        # if p_change < -7:
        #     return False
        # if row['ma_short'] < row['ma_long']:
        #     return False

        if p_change > 0:
            inc_days = inc_days + 1
        if p_change < 0:
            dec_days = dec_days + 1

        if row['close'] > highest_row['close']:
            highest_row = row
        if row['close'] < lowest_row['close']:
            lowest_row = row

    ratio = (highest_row['close'] - lowest_row['close']) / lowest_row['close']

    if ratio > 2:
        logging.info("股票：{0}（{1}）  最低:{2}, 最高:{3}, 涨跌比率:{4}       上涨天数:{5}， 下跌天数:{6}".format(name, stock, lowest_row['date'], highest_row['date'], ratio, inc_days, dec_days))
        return True

    return False
