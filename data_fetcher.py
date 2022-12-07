# -*- encoding: UTF-8 -*-

import tushare as ts
import akshare as ak
import pandas as pd
import datetime
import logging
import settings
import talib as tl

import utils

import concurrent.futures

from pandas.tseries.offsets import *


# def update_data(code_name):
#     stock = code_name[0]
#     old_data = utils.read_data(code_name)
#     if not old_data.empty:
#         start_time = utils.next_weekday(old_data.iloc[-1].date)
#         current_time = datetime.datetime.now()
#         if start_time > current_time:
#             return
#
#         df = ts.get_k_data(stock, autype='qfq')
#         mask = (df['日期'] >= start_time.strftime('%Y-%m-%d'))
#         appender = df.loc[mask]
#         if appender.empty:
#             return
#         else:
#             return appender


def fetch(code_name):
    stock = code_name[0]
    data = ak.stock_zh_a_hist(symbol=stock, period="daily", start_date="20210101", adjust="qfq")

    if data is None or data.empty:
        logging.debug("股票："+stock+" 没有数据，略过...")
        return

    data['p_change'] = tl.ROC(data['收盘'], 1)

    return data


def run(stocks):
    stocks_data = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
        future_to_stock = {executor.submit(fetch, stock): stock for stock in stocks}
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                data = future.result()
                if data is not None:
                    data = data.astype({'成交量': 'double'})
                    stocks_data[stock[1]] = data
            except Exception as exc:
                print('%s(%r) generated an exception: %s' % (stock[1], stock[0], exc))

    return stocks_data
