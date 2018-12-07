# -*- encoding: UTF-8 -*-

import tushare as ts
import pandas as pd
import datetime
import logging

import utils

import concurrent.futures

from pandas.tseries.offsets import *

DATA_DIR = 'data'

CONFIG_MAIN = 'config/沪深A股200亿.xlsx'
CONFIG_CYB = 'config/创业板100亿.xlsx'


def update_data(code_name):
    stock = code_name[0]
    old_data = utils.read_data(code_name)
    if not old_data.empty:
        start_time = utils.next_weekday(old_data.iloc[-1].date)
        current_time = datetime.datetime.now()
        if start_time > current_time:
            return
        appender = ts.get_k_data(stock, start=start_time.strftime('%Y-%m-%d'), autype='hfq')
        if appender.empty:
            return
        else:
            return appender


def init_data(code_name):
    stock = code_name[0]
    data = ts.get_k_data(stock, autype='hfq')
    if data is None or data.empty:
        logging.info("股票："+stock+" 数据下载失败，重试...")
        return
    if len(data) < 60:
        logging.info("股票："+stock+" 上市时间小于60日，略过...")
        return
    return data


def run():
    code_names = utils.get_stocks()
    append_mode = True
    update_fun = update_data
    if code_names == []:   # 第一次下载数据
        stocks_main = utils.get_stocks(CONFIG_MAIN)
        stocks_cyb = utils.get_stocks(CONFIG_CYB)
        code_names = stocks_main + stocks_cyb
        append_mode = False
        update_fun = init_data

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {executor.submit(update_fun, stock): stock for stock in code_names}
        for future in concurrent.futures.as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                data = future.result()
                if data is not None:
                    file_name = stock[0] + '-' + stock[1] + '.h5'
                    data.to_hdf(DATA_DIR + "/" + file_name, 'data', append=append_mode, format='table')
            except Exception as exc:
                print('%s(%r) generated an exception: %s' % (stock[1], stock[0], exc))