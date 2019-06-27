# -*- encoding: UTF-8 -*-

import tushare as ts
import pandas as pd
import datetime
import logging
import settings

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
#         mask = (df['date'] >= start_time.strftime('%Y-%m-%d'))
#         appender = df.loc[mask]
#         if appender.empty:
#             return
#         else:
#             return appender


def init_data(code_name):
    stock = code_name[0]
    data = ts.get_k_data(stock, autype='qfq')
    data_ext = ts.get_hist_data(stock)

    if data is None or data.empty:
        logging.info("股票："+stock+" 没有数据，略过...")
        return
    # for i in range(1, len(data)):
    #     data.loc[i, 'p_change'] = round((data.loc[i, 'close'] - data.loc[i - 1, 'close']) / data.loc[i - 1, 'close'] * 100, 2)
    if len(data) < 60:
        logging.info("股票："+stock+" 上市时间小于60日，略过...")
        return
    if data_ext is None or data_ext.empty:
        return
    data_ext = data_ext.iloc[::-1]
    data_ext['date'] = data_ext.index
    data = pd.merge(data, data_ext[['p_change']], on='date', how='left')
    return data


def run():
    code_names = utils.get_stocks(settings.CONFIG)
    append_mode = False
    update_fun = init_data

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {executor.submit(update_fun, stock): stock for stock in code_names}
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                data = future.result()
                data['code'] = data['code'].apply(lambda x: str(x))
                if data is not None:
                    file_name = stock[0] + '-' + stock[1] + '.h5'
                    data.to_hdf(settings.DATA_DIR + "/" + file_name, 'data', append=append_mode, format='table')
            except Exception as exc:
                print('%s(%r) generated an exception: %s' % (stock[1], stock[0], exc))
