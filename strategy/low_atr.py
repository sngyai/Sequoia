# -*- encoding: UTF-8 -*-
import pandas as pd
import talib as tl
import logging


# 低ATR成长策略
def check_low_increase(stock, name, data, end_date=None, ma_short=30, ma_long=250, threshold=140):
    if data.size < ma_long:
        logging.info("{0}:样本小于{1}天...\n".format(stock, ma_long))
        return False

    # data['ma_short'] = pd.Series(tl.MA(data['close'].values, ma_short), index=data.index.values)
    # data['ma_long'] = pd.Series(tl.MA(data['close'].values, ma_long), index=data.index.values)

    data = data.loc[:end_date]
    data = data.tail(n=threshold)
    inc_days = 0
    dec_days = 0
    if data.size < threshold:
        logging.info("{0}:样本小于{1}天...\n".format(stock, threshold))
        return False

    for index, row in data.iterrows():
        p_change = float((row['close'] - row['open']) / row['open'])

        # if p_change < -7.5:
        #     return False
        # if row['ma_short'] < row['ma_long']:
        #     return False

        if p_change > 0:
            inc_days = inc_days + 1
        if p_change < 0:
            dec_days = dec_days + 1

    begin = data.iloc[0]['close']
    end = data.iloc[-1]['close']
    ratio = (end - begin) / begin

    if ratio > 0.2:
        logging.info("股票：{0}（{1}）  初始价:{2}, 当前价:{3}, 涨跌比率:{4}       上涨天数:{5}， 下跌天数:{6}".format(name, stock, begin, end, ratio, inc_days, dec_days))

    return True
