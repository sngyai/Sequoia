# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging
from strategy import enter


# 平台突破策略
def check(code_name, data, end_date=None, threshold=60):
    origin_data = data
    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return
    data['ma60'] = pd.Series(tl.MA(data['收盘'].values, 60), index=data.index.values)

    if end_date is not None:
        mask = (data['日期'] <= end_date)
        data = data.loc[mask]

    data = data.tail(n=threshold)

    breakthrough_row = None

    for index, row in data.iterrows():
        if row['开盘'] < row['ma60'] <= row['收盘']:
            if enter.check_volume(code_name, origin_data, row['日期'], threshold):
                breakthrough_row = row

    if breakthrough_row is None:
        return False

    data_front = data.loc[(data['日期'] < breakthrough_row['日期'])]
    data_end = data.loc[(data['日期'] >= breakthrough_row['日期'])]

    for index, row in data_front.iterrows():
        if not (-0.05 < (row['ma60'] - row['收盘']) / row['ma60'] < 0.2):
            return False

    return True







