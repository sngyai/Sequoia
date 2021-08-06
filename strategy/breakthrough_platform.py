# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging
import push
from strategy import enter


# 平台突破策略
def check(code_name, data, end_date=None, threshold=60):
    origin_data = data
    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return
    data['ma60'] = pd.Series(tl.MA(data['close'].values, 60), index=data.index.values)

    begin_date = data.iloc[0].date
    if end_date is not None:
        if end_date < begin_date:  # 该股票在end_date时还未上市
            logging.debug("{}在{}时还未上市".format(code_name, end_date))
            return False

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]

    data = data.tail(n=threshold)

    breakthrough_row = None

    for index, row in data.iterrows():
        if row['open'] < row['ma60'] <= row['close']:
            if enter.check_volume(code_name, origin_data, row['date'], threshold):
                breakthrough_row = row

    if breakthrough_row is None:
        return False

    data_front = data.loc[(data['date'] < breakthrough_row['date'])]
    data_end = data.loc[(data['date'] >= breakthrough_row['date'])]

    for index, row in data_front.iterrows():
        if not (-0.05 < (row['ma60'] - row['close']) / row['ma60'] < 0.2):
            return False

    push.strategy("股票{0} 突破日期：{1}".format(code_name, breakthrough_row['date']))
    return True







