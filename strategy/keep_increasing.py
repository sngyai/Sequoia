# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging


# 持续上涨（MA30向上）
def check(code_name, data, end_date=None, threshold=30):
    if len(data) < threshold:
        logging.debug("{0}:样本小于{1}天...\n".format(code_name, threshold))
        return
    data['ma30'] = pd.Series(tl.MA(data['收盘'].values, 30), index=data.index.values)

    if end_date is not None:
        mask = (data['日期'] <= end_date)
        data = data.loc[mask]

    data = data.tail(n=threshold)

    step1 = round(threshold/3)
    step2 = round(threshold*2/3)

    if data.iloc[0]['ma30'] < data.iloc[step1]['ma30'] < \
        data.iloc[step2]['ma30'] < data.iloc[-1]['ma30'] and data.iloc[-1]['ma30'] > 1.2*data.iloc[0]['ma30']:
        return True
    else:
        return False

