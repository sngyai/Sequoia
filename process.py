# -*- encoding: UTF-8 -*-

import tushare as ts
import threadpool
import datetime


import utils

DATA_DIR = 'data'

CONFIG_MAIN = 'config/沪深A股200亿.xlsx'
CONFIG_CYB = 'config/创业板100亿.xlsx'


def append(code_name):
    stock = code_name[0]
    name = code_name[1]
    old_data = utils.read_data(stock, name)
    if not old_data.empty:
        start_date = old_data.iloc[-1].name
        today = datetime.date.today().strftime('%Y-%m-%d')
        if start_date >= today:
            return
        appender = ts.get_hist_data(stock, start=start_date)
        if appender.empty:
            print("股票：{} 没有新的数据，略过。。。".format(stock))
        else:
            # print("股票：{} 追加数据".format(stock))
            appender = appender.drop(start_date).sort_index()
            file_name = stock + '-' + name + '.h5'
            appender.to_hdf(DATA_DIR + "/" + file_name, 'data', append=True, format='table')


def fetch(code_name):
    stock = code_name[0]
    name = code_name[1]
    data = ts.get_hist_data(stock)
    if data is None or data.empty:
        print("股票："+stock+" 数据下载失败，重试...")
        return
    if len(data) < 60:
        print("股票："+stock+" 上市时间小于60日，略过...")
        return
    data = data.sort_index()
    file_name = stock + '-' + name + '.h5'
    data.to_hdf(DATA_DIR + "/" + file_name, 'data', format='table')


def run():
    code_names = utils.get_stocks()
    if code_names:
        # stocks = list(zip(*code_names))
        [append(ss) for ss in code_names]
        # pool = threadpool.ThreadPool(10)
        # requests = threadpool.makeRequests(append, stocks)
        # [pool.putRequest(req) for req in requests]
        # pool.wait()
    else:   # 第一次下载数据
        stocks_main = utils.get_stocks(CONFIG_MAIN)
        stocks_cyb = utils.get_stocks(CONFIG_CYB)

        all_stocks = stocks_main + stocks_cyb

        [fetch(ss) for ss in all_stocks]
        # pool = threadpool.ThreadPool(10)
        # requests = threadpool.makeRequests(fetch, all_stocks)
        # [pool.putRequest(req) for req in requests]
        # pool.wait()

