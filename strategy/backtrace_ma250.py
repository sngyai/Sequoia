# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging


# 回踩年线策略
def check(stock, data, end_date=None, threshold=60):
    if data.size < 250:
        logging.info("{0}:样本小于250天...\n".format(stock))
        return
    data['ma250'] = pd.Series(tl.MA(data['close'].values, 250), index=data.index.values)

    begin_date = data.iloc[0].date
    if end_date is not None:
        if pd.to_datetime(end_date) < begin_date:  # 该股票在end_date时还未上市
            logging.info("{}在{}时还未上市".format(stock, end_date))
            return False

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]

    data = data.tail(n=threshold)

    last_close = data.iloc[-1]['close']

    lowest_row = data.iloc[-1]
    highest_row = data.iloc[-1]

    # 计算区间最高价格
    for index, row in data.iterrows():
        if row['close'] > highest_row['close']:
            highest_row = row
        elif row['close'] < lowest_row['close']:
            lowest_row = row

    if lowest_row['volume'] == 0 or highest_row['volume'] == 0:
        return False

    data_front = data.loc[(data['date'] < highest_row['date'])]
    data_end = data.loc[(data['date'] >= highest_row['date'])]

    if data_front.empty:
        return False
    # 前半段由年线以下向上突破
    if not (data_front.iloc[0]['close'] < data_front.iloc[0]['ma250'] and
            data_front.iloc[-1]['close'] > data_front.iloc[-1]['ma250']):
        return False

    if data_end.empty:
        # 后半段必须在年线以上运行（回踩年线）
        for index, row in data_end.iterrows():
            if row['close'] < row['ma250']:
                return False

    if not ((highest_row['volume']/lowest_row['volume'] > 2) and (highest_row['close'] / lowest_row['close'] > 1.3)) :
        return False

    return True

