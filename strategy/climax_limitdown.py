# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging


def check(code_name, data, end_date=None, threshold=60):
    if len(data) < threshold:
        logging.debug("{0}:样本小于250天...\n".format(code_name))
        return False

    data['vol_ma5'] = pd.Series(tl.MA(data['成交量'].values, 5), index=data.index.values)

    if end_date is not None:
        mask = (data['日期'] <= end_date)
        data = data.loc[mask]
    if data.empty:
        return False
    p_change = data.iloc[-1]['p_change']
    if p_change > -9.5:
        return False

    data = data.tail(n=threshold + 1)
    if len(data) < threshold + 1:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return False

    # 最后一天收盘价
    last_close = data.iloc[-1]['收盘']
    # 最后一天成交量
    last_vol = data.iloc[-1]['成交量']

    amount = last_close * last_vol * 100

    # 成交额不低于2亿
    if amount < 200000000:
        return False

    data = data.head(n=threshold)

    mean_vol = data.iloc[-1]['vol_ma5']

    vol_ratio = last_vol / mean_vol
    if vol_ratio >= 4:
        msg = "*{0}\n量比：{1:.2f}\t跌幅：{2}%\n".format(code_name, vol_ratio, p_change)
        logging.debug(msg)
        return True
    else:
        return False

