# -*- encoding: UTF-8 -*-

import talib as tl
import pandas as pd
import logging
from datetime import datetime, timedelta
from strategy import enter


# “停机坪”策略
def check(code_name, data, end_date=None, threshold=60, window=10):
    if data.size < 250:
        logging.info("{0}:样本小于250天...\n".format(code_name))
        return
    data['ma250'] = pd.Series(tl.MA(data['close'].values, 250), index=data.index.values)

    begin_date = data.iloc[0].date
    if end_date is not None:
        if end_date < begin_date:  # 该股票在end_date时还未上市
            logging.info("{}在{}时还未上市".format(code_name, end_date))
            return False

    if end_date is not None:
        mask = (data['date'] <= end_date)
        data = data.loc[mask]

    data = data.tail(n=window)
    data_rev = data.iloc[::-1]

    # 涨停日
    limitup_row = None

    # 计算区间最高、最低价格
    for index, row in data_rev.iterrows():
        try:
            if float(row['p_change']) > 9.5:
                if enter.check_volume(code_name, data, row['date'], threshold):
                    limitup_row = row
                    break
        except KeyError as error:
            logging.info("{}处理异常：{}".format(code_name, error))

    if limitup_row is None:
        return False

    return True

